import {
  getContentType,
  normalizeMessageContent,
  jidNormalizedUser,
  isJidGroup,
  isJidBroadcast,
  isJidNewsletter,
  isJidStatusBroadcast,
} from "@whiskeysockets/baileys";

const MEDIA_TYPES = {
  imageMessage: "image",
  videoMessage: "video",
  audioMessage: "audio",
  documentMessage: "document",
  stickerMessage: "sticker",
  contactMessage: "contact",
  locationMessage: "location",
  liveLocationMessage: "location",
  pollCreationMessage: "poll",
  pollCreationMessageV3: "poll",
};

/**
 * Pull the useful parts out of a Baileys WAMessage.
 * Returns null for messages we should ignore entirely (protocol/system messages, status updates).
 */
export function parseMessage(msg) {
  const key = msg.key || {};
  const chatJid = key.remoteJid;
  if (!chatJid) return null;
  if (isJidStatusBroadcast(chatJid) || isJidBroadcast(chatJid) || isJidNewsletter(chatJid)) return null;

  const content = normalizeMessageContent(msg.message);
  if (!content) return null;
  const type = getContentType(content);
  if (!type || type === "protocolMessage" || type === "senderKeyDistributionMessage" || type === "reactionMessage") {
    return null;
  }

  const inner = content[type];
  const isGroup = !!isJidGroup(chatJid);
  const senderJid = isGroup ? key.participant || msg.participant : chatJid;

  let text = "";
  if (type === "conversation") text = content.conversation || "";
  else if (type === "extendedTextMessage") text = inner?.text || "";
  else if (inner && typeof inner === "object" && typeof inner.caption === "string") text = inner.caption;

  const mediaType = MEDIA_TYPES[type] || null;
  const contextInfo = inner && typeof inner === "object" ? inner.contextInfo || null : null;

  return {
    id: key.id,
    chatJid,
    isGroup,
    fromMe: !!key.fromMe,
    senderJid: senderJid || chatJid,
    senderName: msg.pushName || phoneFromJid(senderJid) || "Unknown",
    text: text.trim(),
    type,
    mediaType,
    mimetype: inner?.mimetype || null,
    contextInfo,
    mentionedJids: contextInfo?.mentionedJid || [],
    quotedMessageId: contextInfo?.stanzaId || null,
    quotedParticipant: contextInfo?.participant || null,
    quotedText: quotedTextOf(contextInfo),
    timestamp: Number(msg.messageTimestamp) || Math.floor(Date.now() / 1000),
    raw: msg,
  };
}

function quotedTextOf(contextInfo) {
  const q = contextInfo?.quotedMessage;
  if (!q) return null;
  const c = normalizeMessageContent(q);
  const t = getContentType(c);
  if (!t) return null;
  if (t === "conversation") return c.conversation || null;
  const inner = c[t];
  return inner?.text || inner?.caption || (MEDIA_TYPES[t] ? `[${MEDIA_TYPES[t]}]` : null);
}

/** "923001234567@s.whatsapp.net" -> "923001234567". LIDs return null. */
export function phoneFromJid(jid) {
  if (!jid || !jid.endsWith("@s.whatsapp.net")) return null;
  return jid.split("@")[0].split(":")[0];
}

/** All JIDs (phone + lid forms) that identify the bot itself, normalized. */
export function selfJids(sock) {
  const out = new Set();
  const me = sock?.user;
  if (me?.id) out.add(jidNormalizedUser(me.id));
  if (me?.lid) out.add(jidNormalizedUser(me.lid));
  return out;
}

export function sameUser(a, b) {
  if (!a || !b) return false;
  return jidNormalizedUser(a) === jidNormalizedUser(b);
}

/** Split long text so every piece fits comfortably in one WhatsApp message. */
export function chunkText(text, max = 3500) {
  if (text.length <= max) return [text];
  const chunks = [];
  let rest = text;
  while (rest.length > max) {
    let cut = rest.lastIndexOf("\n\n", max);
    if (cut < max * 0.5) cut = rest.lastIndexOf("\n", max);
    if (cut < max * 0.5) cut = rest.lastIndexOf(" ", max);
    if (cut < max * 0.5) cut = max;
    chunks.push(rest.slice(0, cut).trimEnd());
    rest = rest.slice(cut).trimStart();
  }
  if (rest) chunks.push(rest);
  return chunks;
}

export function formatTime(ts) {
  const d = new Date(ts * 1000);
  return d.toISOString().replace("T", " ").slice(0, 16);
}
