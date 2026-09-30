import { downloadMediaMessage, isJidGroup } from "@whiskeysockets/baileys";
import { config } from "./config.js";
import { memory } from "./memory.js";
import { groups } from "./groups.js";
import { askClaude, describeError } from "./claude.js";
import { handleCommand } from "./commands.js";
import { parseMessage, selfJids, sameUser, chunkText, formatTime, phoneFromJid } from "./util.js";

const IMAGE_TYPES = new Set(["image/jpeg", "image/png", "image/gif", "image/webp"]);

/** Decide whether Claude should answer this group message. */
export function shouldReplyInGroup(msg, self, mode) {
  if (mode === "off") return { reply: false };
  if (mode === "always") return { reply: true, reason: "always" };

  // @mention of the bot (WhatsApp sends both phone-number and lid forms depending on the group)
  if (msg.mentionedJids.some((j) => [...self].some((s) => sameUser(j, s)))) {
    return { reply: true, reason: "mention" };
  }
  // reply to one of the bot's own messages
  if (msg.quotedMessageId && memory.isBotMessage(msg.quotedMessageId)) {
    return { reply: true, reason: "reply" };
  }
  if (msg.quotedParticipant && [...self].some((s) => sameUser(msg.quotedParticipant, s))) {
    return { reply: true, reason: "reply" };
  }
  // trigger word at the start of the message
  const lower = msg.text.toLowerCase();
  for (const w of config.triggerWords) {
    if (lower === w || lower.startsWith(w + " ") || lower.startsWith(w + ",") || lower.startsWith(w + ":")) {
      return { reply: true, reason: "trigger", strip: w.length };
    }
  }
  return { reply: false };
}

/** Remove @mentions of the bot and leading trigger words from the prompt text. */
export function cleanPrompt(msg, self, strip = 0) {
  let t = msg.text;
  if (strip) t = t.slice(strip).replace(/^[\s,:]+/, "");
  for (const s of self) {
    const num = phoneFromJid(s) || s.split("@")[0];
    if (num) t = t.replace(new RegExp(`@${num}\\b`, "g"), "").trim();
  }
  return t.replace(/\s{2,}/g, " ").trim();
}

export function isOwner(msg) {
  if (msg.fromMe) return true;
  const phone = phoneFromJid(msg.senderJid);
  return !!phone && config.ownerNumbers.includes(phone);
}

export function createMessageHandler(sock, log) {
  const self = selfJids(sock);

  async function send(jid, text, quoted) {
    for (const part of chunkText(text)) {
      const sent = await sock.sendMessage(jid, { text: part }, quoted ? { quoted } : undefined);
      memory.rememberBotMessage(sent?.key?.id);
      if (isJidGroup(jid)) {
        memory.logGroupMessage(jid, { ts: Math.floor(Date.now() / 1000), sender: config.botName, text: part });
      }
      quoted = undefined; // only quote on the first chunk
    }
  }

  return async function onMessage(raw) {
    const msg = parseMessage(raw);
    if (!msg) return;

    // Bot replies are logged in send(); when WhatsApp echoes them back, don't log them twice.
    const isEchoOfBot = msg.fromMe && memory.isBotMessage(msg.id);

    // In groups, remember everything (including the owner's own messages) for context/!summary.
    if (msg.isGroup && !isEchoOfBot && (msg.text || msg.mediaType)) {
      memory.logGroupMessage(msg.chatJid, {
        ts: msg.timestamp,
        sender: msg.fromMe ? `${msg.senderName} (owner)` : msg.senderName,
        text: msg.text || `[${msg.mediaType}]`,
      });
    }

    // Anything the bot itself sent comes back as fromMe. Ignore it unless it's a command typed
    // from the linked phone by the owner (so you can drive the bot from your own WhatsApp).
    const owner = isOwner(msg);
    if (msg.fromMe) {
      if (msg.text.startsWith(config.commandPrefix) && !isEchoOfBot) {
        await handleCommand({ sock, msg, isOwner: true, reply: (t) => send(msg.chatJid, t) });
      }
      return;
    }

    if (!msg.text && !msg.mediaType) return;

    if (msg.isGroup) {
      if (!groups.isAllowed(msg.chatJid)) return;
      await groups.get(sock, msg.chatJid); // warm the directory for names
    } else if (!config.dmEnabled && !owner) {
      return;
    }

    const reply = (t) => send(msg.chatJid, t, raw);

    // Commands work everywhere; in groups they run even when the group is in "off" mode.
    if (msg.text.startsWith(config.commandPrefix)) {
      const handled = await handleCommand({ sock, msg, isOwner: owner, reply });
      if (handled) return;
    }

    let strip = 0;
    if (msg.isGroup) {
      const decision = shouldReplyInGroup(msg, self, memory.getGroupMode(msg.chatJid));
      if (!decision.reply) return;
      strip = decision.strip || 0;
      log.info(`[group:${groups.name(msg.chatJid)}] ${msg.senderName} -> ${decision.reason}`);
    } else {
      log.info(`[dm] ${msg.senderName}`);
    }

    const prompt = cleanPrompt(msg, self, strip);
    const content = await buildUserContent(sock, msg, prompt, log);
    if (!content) return;

    try {
      await sock.sendPresenceUpdate("composing", msg.chatJid);
    } catch {
      /* presence is best-effort */
    }

    let extraSystem;
    if (msg.isGroup) {
      const meta = groups.groups.get(msg.chatJid);
      const recent = memory
        .getGroupLog(msg.chatJid, config.groupContextMessages)
        .map((e) => `[${formatTime(e.ts)}] ${e.sender}: ${e.text}`)
        .join("\n");
      extraSystem =
        `You are replying inside the WhatsApp group "${meta?.subject || msg.chatJid}"` +
        (meta?.desc ? ` (description: ${meta.desc})` : "") +
        `. The message you are answering is from ${msg.senderName}. ` +
        `Recent messages in this group, oldest first, are below for context; the last one is the message you are answering. ` +
        `Address the group naturally, don't repeat the transcript.\n\n${recent}`;
    }

    try {
      const { text } = await askClaude({
        history: memory.getHistory(msg.chatJid),
        userContent: content,
        extraSystem,
      });
      await reply(text);
      // Store a text-only version of the turn so history stays small.
      const storedUser = msg.isGroup ? `${msg.senderName}: ${prompt || `[${msg.mediaType}]`}` : prompt || `[${msg.mediaType}]`;
      memory.pushTurn(msg.chatJid, storedUser, text);
    } catch (err) {
      log.error({ err }, "claude request failed");
      await reply(describeError(err));
    } finally {
      try {
        await sock.sendPresenceUpdate("paused", msg.chatJid);
      } catch {
        /* ignore */
      }
    }
  };
}

/** Build the Anthropic user-content for this message: text plus an image if one was sent. */
async function buildUserContent(sock, msg, prompt, log) {
  const blocks = [];

  if (msg.mediaType === "image" && IMAGE_TYPES.has(msg.mimetype)) {
    try {
      const buf = await downloadMediaMessage(msg.raw, "buffer", {}, { logger: log, reuploadRequest: sock.updateMediaMessage });
      blocks.push({ type: "image", source: { type: "base64", media_type: msg.mimetype, data: buf.toString("base64") } });
    } catch (err) {
      log.warn({ err }, "image download failed");
    }
  }

  let text = prompt;
  if (msg.quotedText && !msg.isGroup) text = `(replying to: "${msg.quotedText}")\n${text}`;
  if (!text && blocks.length) text = "What do you make of this image?";
  if (!text && msg.mediaType) text = `[The user sent a ${msg.mediaType} that I can't view.] Reply briefly.`;
  if (!text) return null;

  blocks.push({ type: "text", text });
  return blocks.length === 1 ? text : blocks;
}
