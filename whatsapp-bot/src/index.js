import makeWASocket, {
  useMultiFileAuthState,
  fetchLatestBaileysVersion,
  makeCacheableSignalKeyStore,
  DisconnectReason,
  Browsers,
} from "@whiskeysockets/baileys";
import { Boom } from "@hapi/boom";
import pino from "pino";
import qrcode from "qrcode-terminal";
import { config, validateConfig } from "./config.js";
import { memory } from "./memory.js";
import { groups } from "./groups.js";
import { createMessageHandler } from "./handler.js";

const log = pino({ level: config.logLevel });
const problems = validateConfig();
if (problems.length) {
  for (const p of problems) console.error(`Config error: ${p}`);
  process.exit(1);
}

// Small cache of messages we sent, so WhatsApp can ask us to re-send one that failed to decrypt.
const sentCache = new Map();

async function start() {
  const { state, saveCreds } = await useMultiFileAuthState(config.authDir);
  const { version } = await fetchLatestBaileysVersion().catch(() => ({ version: undefined }));

  const sock = makeWASocket({
    version,
    logger: log,
    auth: {
      creds: state.creds,
      keys: makeCacheableSignalKeyStore(state.keys, log),
    },
    browser: Browsers.macOS("Desktop"),
    markOnlineOnConnect: false, // keep your phone receiving notifications
    generateHighQualityLinkPreview: false,
    syncFullHistory: false,
    cachedGroupMetadata: async (jid) => groups.groups.get(jid),
    getMessage: async (key) => sentCache.get(key.id),
  });

  sock.ev.on("creds.update", saveCreds);

  sock.ev.on("connection.update", async (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      console.log("\nScan this QR code with WhatsApp -> Linked devices -> Link a device:\n");
      qrcode.generate(qr, { small: true });
    }

    if (connection === "open") {
      const me = sock.user;
      console.log(`\n✅ Connected as ${me?.name || ""} (${me?.id})`);
      try {
        const all = await groups.refresh(sock);
        console.log(`   Member of ${all.size} group(s). Send !groups to list them, !help for commands.`);
      } catch (err) {
        console.warn("   Could not fetch groups yet:", err.message);
      }
    }

    if (connection === "close") {
      const code = new Boom(lastDisconnect?.error)?.output?.statusCode;
      if (code === DisconnectReason.loggedOut) {
        console.error("\n❌ Logged out from WhatsApp. Run `npm run logout` then `npm start` to link again.");
        memory.flush();
        process.exit(1);
      }
      const delay = code === DisconnectReason.restartRequired ? 0 : 3000;
      console.warn(`Connection closed (code ${code}). Reconnecting in ${delay / 1000}s...`);
      setTimeout(start, delay);
    }
  });

  // Keep the group directory fresh.
  sock.ev.on("groups.upsert", (metas) => metas.forEach((m) => groups.upsert(m)));
  sock.ev.on("groups.update", (updates) => updates.forEach((m) => groups.upsert(m)));
  sock.ev.on("group-participants.update", async ({ id }) => {
    try {
      groups.upsert(await sock.groupMetadata(id));
    } catch {
      /* ignore */
    }
  });

  const onMessage = createMessageHandler(sock, log);
  const originalSend = sock.sendMessage.bind(sock);
  sock.sendMessage = async (jid, content, options) => {
    const sent = await originalSend(jid, content, options);
    if (sent?.key?.id) {
      sentCache.set(sent.key.id, sent.message);
      if (sentCache.size > 500) sentCache.delete(sentCache.keys().next().value);
    }
    return sent;
  };

  sock.ev.on("messages.upsert", async ({ messages, type }) => {
    if (type !== "notify") return; // ignore history sync / offline backfill
    for (const m of messages) {
      onMessage(m).catch((err) => log.error({ err }, "message handler failed"));
    }
  });
}

process.on("SIGINT", () => {
  memory.flush();
  process.exit(0);
});
process.on("SIGTERM", () => {
  memory.flush();
  process.exit(0);
});

start().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
