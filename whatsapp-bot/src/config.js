import "dotenv/config";

const bool = (v, d) => (v === undefined || v === "" ? d : /^(1|true|yes|on)$/i.test(v));
const int = (v, d) => {
  const n = parseInt(v, 10);
  return Number.isFinite(n) && n > 0 ? n : d;
};
const list = (v) =>
  (v || "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);

const GROUP_MODES = new Set(["mention", "always", "off"]);
const groupMode = (process.env.GROUP_MODE || "mention").toLowerCase();

export const config = {
  anthropicApiKey: process.env.ANTHROPIC_API_KEY || "",
  model: process.env.CLAUDE_MODEL || "claude-opus-5-5",
  effort: process.env.CLAUDE_EFFORT || "medium",
  maxTokens: int(process.env.CLAUDE_MAX_TOKENS, 4096),

  botName: process.env.BOT_NAME || "Claude",
  systemPrompt:
    process.env.SYSTEM_PROMPT ||
    "You are Claude, a helpful assistant chatting on WhatsApp. Keep replies concise and conversational. Use plain text: no markdown headers or tables; *bold*, _italics_ and - bullet lists are fine.",

  ownerNumbers: list(process.env.OWNER_NUMBERS).map((n) => n.replace(/\D/g, "")),
  dmEnabled: bool(process.env.DM_ENABLED, true),
  groupMode: GROUP_MODES.has(groupMode) ? groupMode : "mention",
  triggerWords: list(process.env.TRIGGER_WORDS || "!ai,claude,@claude,hey claude").map((w) =>
    w.toLowerCase()
  ),
  allowedGroups: list(process.env.ALLOWED_GROUPS),
  groupContextMessages: int(process.env.GROUP_CONTEXT_MESSAGES, 40),
  groupMemoryMessages: int(process.env.GROUP_MEMORY_MESSAGES, 300),
  historyTurns: int(process.env.HISTORY_TURNS, 30),

  authDir: process.env.AUTH_DIR || "./auth",
  dataDir: process.env.DATA_DIR || "./data",
  logLevel: process.env.LOG_LEVEL || "warn",

  commandPrefix: "!",
};

export function validateConfig() {
  const problems = [];
  if (!config.anthropicApiKey) {
    problems.push("ANTHROPIC_API_KEY is not set (copy .env.example to .env and fill it in).");
  }
  return problems;
}
