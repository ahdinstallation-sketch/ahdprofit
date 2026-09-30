import fs from "node:fs";
import path from "node:path";
import { config } from "./config.js";

/**
 * Persistent memory:
 *  - history[chatJid]  : Claude conversation turns (what Claude was asked / answered)
 *  - groupLog[groupJid]: rolling log of every message seen in a group (for context + !summary)
 *  - groupSettings[jid]: per-group overrides { mode: 'mention'|'always'|'off' }
 *  - botMessageIds     : ids of messages the bot sent (to detect replies to the bot)
 */
class Memory {
  constructor(file) {
    this.file = file;
    this.state = { history: {}, groupLog: {}, groupSettings: {}, botMessageIds: [] };
    this._saveTimer = null;
    this.load();
  }

  load() {
    try {
      if (fs.existsSync(this.file)) {
        const raw = JSON.parse(fs.readFileSync(this.file, "utf8"));
        this.state = { ...this.state, ...raw };
      }
    } catch (err) {
      console.warn(`[memory] could not read ${this.file}: ${err.message}. Starting fresh.`);
    }
  }

  save() {
    clearTimeout(this._saveTimer);
    this._saveTimer = setTimeout(() => {
      try {
        fs.mkdirSync(path.dirname(this.file), { recursive: true });
        const tmp = `${this.file}.tmp`;
        fs.writeFileSync(tmp, JSON.stringify(this.state));
        fs.renameSync(tmp, this.file);
      } catch (err) {
        console.warn(`[memory] could not write ${this.file}: ${err.message}`);
      }
    }, 500);
  }

  flush() {
    clearTimeout(this._saveTimer);
    this._saveTimer = null;
    try {
      fs.mkdirSync(path.dirname(this.file), { recursive: true });
      fs.writeFileSync(this.file, JSON.stringify(this.state));
    } catch (err) {
      console.warn(`[memory] could not write ${this.file}: ${err.message}`);
    }
  }

  // ---- conversation history (Anthropic MessageParam[]) ----
  getHistory(jid) {
    return this.state.history[jid] || [];
  }

  pushTurn(jid, userContent, assistantText) {
    const h = this.state.history[jid] || [];
    h.push({ role: "user", content: userContent });
    h.push({ role: "assistant", content: assistantText });
    const max = config.historyTurns * 2;
    this.state.history[jid] = h.length > max ? h.slice(h.length - max) : h;
    this.save();
  }

  clearHistory(jid) {
    delete this.state.history[jid];
    this.save();
  }

  // ---- group message log ----
  logGroupMessage(groupJid, entry) {
    const log = this.state.groupLog[groupJid] || [];
    log.push(entry);
    const max = config.groupMemoryMessages;
    this.state.groupLog[groupJid] = log.length > max ? log.slice(log.length - max) : log;
    this.save();
  }

  getGroupLog(groupJid, n = Infinity) {
    const log = this.state.groupLog[groupJid] || [];
    return n === Infinity ? log : log.slice(-n);
  }

  // ---- per-group settings ----
  getGroupMode(groupJid) {
    return this.state.groupSettings[groupJid]?.mode || config.groupMode;
  }

  setGroupMode(groupJid, mode) {
    this.state.groupSettings[groupJid] = { ...(this.state.groupSettings[groupJid] || {}), mode };
    this.save();
  }

  // ---- bot-sent message ids ----
  rememberBotMessage(id) {
    if (!id) return;
    this.state.botMessageIds.push(id);
    if (this.state.botMessageIds.length > 2000) {
      this.state.botMessageIds = this.state.botMessageIds.slice(-2000);
    }
    this.save();
  }

  isBotMessage(id) {
    return !!id && this.state.botMessageIds.includes(id);
  }
}

export const memory = new Memory(path.join(config.dataDir, "memory.json"));
