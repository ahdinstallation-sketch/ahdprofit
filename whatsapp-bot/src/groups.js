import { config } from "./config.js";

/**
 * Directory of the groups the linked number is a member of.
 * Refreshed from WhatsApp on connect and whenever group events arrive.
 */
class GroupDirectory {
  constructor() {
    /** @type {Map<string, import("@whiskeysockets/baileys").GroupMetadata>} */
    this.groups = new Map();
    this.lastRefresh = 0;
  }

  async refresh(sock) {
    const all = await sock.groupFetchAllParticipating();
    this.groups = new Map(Object.entries(all));
    this.lastRefresh = Date.now();
    return this.groups;
  }

  upsert(meta) {
    if (meta?.id) this.groups.set(meta.id, { ...(this.groups.get(meta.id) || {}), ...meta });
  }

  async get(sock, jid) {
    if (!this.groups.has(jid)) {
      try {
        const meta = await sock.groupMetadata(jid);
        this.upsert(meta);
      } catch {
        return undefined;
      }
    }
    return this.groups.get(jid);
  }

  name(jid) {
    return this.groups.get(jid)?.subject || jid;
  }

  list() {
    return [...this.groups.values()].sort((a, b) => (a.subject || "").localeCompare(b.subject || ""));
  }

  /** Find a group by exact JID or a case-insensitive substring of its name. */
  find(query) {
    if (!query) return undefined;
    const q = query.trim().toLowerCase();
    if (this.groups.has(query)) return this.groups.get(query);
    const matches = this.list().filter((g) => (g.subject || "").toLowerCase().includes(q));
    if (matches.length === 1) return matches[0];
    const exact = matches.find((g) => (g.subject || "").toLowerCase() === q);
    return exact || (matches.length ? matches : undefined);
  }

  /** Is the bot allowed to operate in this group (ALLOWED_GROUPS)? */
  isAllowed(jid) {
    if (!config.allowedGroups.length) return true;
    const name = this.name(jid).toLowerCase();
    return config.allowedGroups.some((rule) => rule === jid || name.includes(rule.toLowerCase()));
  }
}

export const groups = new GroupDirectory();
