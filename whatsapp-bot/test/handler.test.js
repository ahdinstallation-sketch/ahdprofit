import { test, before } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

// Point memory at a throwaway dir and give the bot a fake key before modules load.
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "wa-bot-test-"));
process.env.DATA_DIR = tmp;
process.env.ANTHROPIC_API_KEY = "test-key";
process.env.OWNER_NUMBERS = "923001234567";
process.env.TRIGGER_WORDS = "!ai,claude,hey claude";

const { shouldReplyInGroup, cleanPrompt, isOwner } = await import("../src/handler.js");
const { parseMessage, chunkText, selfJids } = await import("../src/util.js");
const { memory } = await import("../src/memory.js");
const { groups } = await import("../src/groups.js");

const BOT_PN = "923009999999@s.whatsapp.net";
const BOT_LID = "111222333444555@lid";
const fakeSock = { user: { id: "923009999999:12@s.whatsapp.net", lid: "111222333444555:12@lid" } };
const self = selfJids(fakeSock);

const groupMsg = (text, extra = {}) =>
  parseMessage({
    key: { remoteJid: "120363000000000001@g.us", fromMe: false, id: "ABC" + Math.random(), participant: "923001111111@s.whatsapp.net" },
    pushName: "Ali",
    messageTimestamp: 1700000000,
    message: { extendedTextMessage: { text, contextInfo: extra.contextInfo } },
  });

test("selfJids normalises device suffixes and includes both phone and lid forms", () => {
  assert.deepEqual([...self].sort(), [BOT_LID, BOT_PN].sort());
});

test("parseMessage extracts text, sender and group flag", () => {
  const m = groupMsg("hello there");
  assert.equal(m.text, "hello there");
  assert.equal(m.isGroup, true);
  assert.equal(m.senderName, "Ali");
  assert.equal(m.senderJid, "923001111111@s.whatsapp.net");
});

test("parseMessage ignores status broadcasts and protocol messages", () => {
  assert.equal(parseMessage({ key: { remoteJid: "status@broadcast" }, message: { conversation: "x" } }), null);
  assert.equal(
    parseMessage({ key: { remoteJid: "1@s.whatsapp.net" }, message: { protocolMessage: { type: 0 } } }),
    null
  );
});

test("parseMessage handles image captions", () => {
  const m = parseMessage({
    key: { remoteJid: "923001111111@s.whatsapp.net", id: "IMG1" },
    message: { imageMessage: { caption: "what is this?", mimetype: "image/jpeg" } },
  });
  assert.equal(m.mediaType, "image");
  assert.equal(m.text, "what is this?");
  assert.equal(m.mimetype, "image/jpeg");
  assert.equal(m.isGroup, false);
});

test("group mode off never replies, always replies to anything", () => {
  assert.equal(shouldReplyInGroup(groupMsg("claude hi"), self, "off").reply, false);
  assert.equal(shouldReplyInGroup(groupMsg("random chatter"), self, "always").reply, true);
});

test("mention mode: plain chatter is ignored", () => {
  assert.equal(shouldReplyInGroup(groupMsg("what time is dinner?"), self, "mention").reply, false);
});

test("mention mode: @mention by phone jid or lid triggers a reply", () => {
  const byPn = groupMsg("@923009999999 what's up", { contextInfo: { mentionedJid: [BOT_PN] } });
  const byLid = groupMsg("@111222333444555 what's up", { contextInfo: { mentionedJid: [BOT_LID] } });
  assert.equal(shouldReplyInGroup(byPn, self, "mention").reason, "mention");
  assert.equal(shouldReplyInGroup(byLid, self, "mention").reason, "mention");
  assert.equal(cleanPrompt(byPn, self), "what's up");
  assert.equal(cleanPrompt(byLid, self), "what's up");
});

test("mention mode: replying to one of the bot's messages triggers a reply", () => {
  memory.rememberBotMessage("BOTMSG1");
  const m = groupMsg("can you expand on that?", { contextInfo: { stanzaId: "BOTMSG1", participant: "someone@lid" } });
  assert.equal(shouldReplyInGroup(m, self, "mention").reason, "reply");
  const byParticipant = groupMsg("and this?", { contextInfo: { stanzaId: "UNKNOWN", participant: BOT_LID } });
  assert.equal(shouldReplyInGroup(byParticipant, self, "mention").reason, "reply");
});

test("mention mode: trigger words at the start of the message", () => {
  const d = shouldReplyInGroup(groupMsg("Claude, what's 2+2?"), self, "mention");
  assert.equal(d.reason, "trigger");
  assert.equal(cleanPrompt(groupMsg("Claude, what's 2+2?"), self, d.strip), "what's 2+2?");
  assert.equal(cleanPrompt(groupMsg("!ai summarise"), self, shouldReplyInGroup(groupMsg("!ai summarise"), self, "mention").strip), "summarise");
  // trigger word in the middle of a sentence is not a trigger
  assert.equal(shouldReplyInGroup(groupMsg("I asked claude yesterday"), self, "mention").reply, false);
  // "claudette" is not "claude"
  assert.equal(shouldReplyInGroup(groupMsg("claudette is here"), self, "mention").reply, false);
});

test("isOwner: fromMe, listed number, or neither", () => {
  assert.equal(isOwner({ fromMe: true, senderJid: "x@s.whatsapp.net" }), true);
  assert.equal(isOwner({ fromMe: false, senderJid: "923001234567@s.whatsapp.net" }), true);
  assert.equal(isOwner({ fromMe: false, senderJid: "923000000000@s.whatsapp.net" }), false);
  assert.equal(isOwner({ fromMe: false, senderJid: "999@lid" }), false);
});

test("memory: history is capped and group log rolls", () => {
  const jid = "test@s.whatsapp.net";
  for (let i = 0; i < 100; i++) memory.pushTurn(jid, `q${i}`, `a${i}`);
  const h = memory.getHistory(jid);
  assert.equal(h.length, 60); // HISTORY_TURNS default 30 * 2
  assert.equal(h[0].content, "q70");
  assert.equal(h[59].content, "a99");

  const g = "120363000000000002@g.us";
  for (let i = 0; i < 400; i++) memory.logGroupMessage(g, { ts: i, sender: "s", text: `m${i}` });
  assert.equal(memory.getGroupLog(g).length, 300);
  assert.equal(memory.getGroupLog(g, 5).map((e) => e.text).join(","), "m395,m396,m397,m398,m399");
});

test("memory: per-group mode falls back to default", () => {
  const g = "120363000000000003@g.us";
  assert.equal(memory.getGroupMode(g), "mention");
  memory.setGroupMode(g, "always");
  assert.equal(memory.getGroupMode(g), "always");
});

test("groups.find matches by jid, unique substring, exact name, or returns candidates", () => {
  groups.upsert({ id: "1@g.us", subject: "Family Group", participants: [] });
  groups.upsert({ id: "2@g.us", subject: "AHD Team", participants: [] });
  groups.upsert({ id: "3@g.us", subject: "AHD Team Leads", participants: [] });
  assert.equal(groups.find("1@g.us").subject, "Family Group");
  assert.equal(groups.find("family").subject, "Family Group");
  assert.equal(groups.find("ahd team").subject, "AHD Team"); // exact wins over ambiguity
  assert.equal(groups.find("leads").subject, "AHD Team Leads");
  assert.equal(Array.isArray(groups.find("ahd")), true);
  assert.equal(groups.find("nope"), undefined);
});

test("chunkText keeps pieces under the limit and preserves all text", () => {
  const para = "word ".repeat(400).trim(); // ~2000 chars
  const text = [para, para, para].join("\n\n");
  const parts = chunkText(text, 3500);
  assert.ok(parts.length >= 2);
  assert.ok(parts.every((p) => p.length <= 3500));
  assert.equal(parts.join("\n\n").replace(/\s+/g, " "), text.replace(/\s+/g, " "));
  assert.deepEqual(chunkText("short"), ["short"]);
});
