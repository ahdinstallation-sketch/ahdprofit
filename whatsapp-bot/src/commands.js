import { config } from "./config.js";
import { memory } from "./memory.js";
import { groups } from "./groups.js";
import { askClaude, describeError } from "./claude.js";
import { formatTime } from "./util.js";

const HELP = `*${config.botName} on WhatsApp*

Talk to me directly, or in a group by @mentioning me, replying to me, or starting with one of: ${config.triggerWords.join(", ")}.

*Commands* (owner only unless noted)
!help - this message (anyone)
!status - connection + settings
!groups - list every group I'm in
!summary [n] - summarise the last n messages in this group (default 50)
!summary <group name> [n] - summarise another group (from anywhere)
!ai on|off|always - how I behave in this group
   on = reply when mentioned/triggered, always = reply to everything, off = stay silent
!clear - forget our conversation history in this chat`;

/**
 * Try to handle a command. Returns true if the message was a command (handled or rejected).
 * @param {object} ctx  { sock, msg, isOwner, reply }
 */
export async function handleCommand(ctx) {
  const { msg, isOwner, reply, sock } = ctx;
  const text = msg.text;
  if (!text.startsWith(config.commandPrefix)) return false;

  const [rawCmd, ...args] = text.slice(config.commandPrefix.length).trim().split(/\s+/);
  const cmd = (rawCmd || "").toLowerCase();
  const argStr = args.join(" ").trim();

  if (cmd === "help") {
    await reply(HELP);
    return true;
  }

  // "!ai" used as a trigger word ("!ai what's the weather") is not a command, let the chat flow handle it
  if (cmd === "ai" && !/^(on|off|always|mention)$/i.test(args[0] || "")) return false;

  if (!["status", "groups", "summary", "ai", "clear"].includes(cmd)) return false;

  if (!isOwner) {
    await reply("Sorry, only the owner of this number can use that command.");
    return true;
  }

  switch (cmd) {
    case "status": {
      const mode = msg.isGroup ? memory.getGroupMode(msg.chatJid) : "n/a (direct chat)";
      await reply(
        [
          `*Status*`,
          `Model: ${config.model} (effort ${config.effort})`,
          `Groups joined: ${groups.groups.size}`,
          `Default group mode: ${config.groupMode}`,
          `This chat's mode: ${mode}`,
          `Allowed groups: ${config.allowedGroups.length ? config.allowedGroups.join(", ") : "all"}`,
          `History kept: ${config.historyTurns} turns per chat`,
        ].join("\n")
      );
      return true;
    }

    case "groups": {
      if (Date.now() - groups.lastRefresh > 60_000) {
        try {
          await groups.refresh(sock);
        } catch (err) {
          console.warn("[groups] refresh failed:", err.message);
        }
      }
      const list = groups.list();
      if (!list.length) {
        await reply("I'm not in any groups yet.");
        return true;
      }
      const lines = list.map((g, i) => {
        const mode = memory.getGroupMode(g.id);
        const allowed = groups.isAllowed(g.id) ? "" : " (blocked by ALLOWED_GROUPS)";
        const seen = memory.getGroupLog(g.id).length;
        return `${i + 1}. *${g.subject}*\n   ${g.participants?.length ?? g.size ?? "?"} members - mode: ${mode}${allowed} - ${seen} msgs remembered\n   ${g.id}`;
      });
      await reply(`*Groups I'm in (${list.length})*\n\n${lines.join("\n\n")}`);
      return true;
    }

    case "summary": {
      let targetJid = msg.isGroup ? msg.chatJid : null;
      let n = 50;
      // Parse: "!summary", "!summary 100", "!summary Family Group", "!summary Family Group 100"
      const m = argStr.match(/^(.*?)(?:\s+(\d+))?$/);
      const namePart = (m?.[1] || "").trim();
      if (m?.[2]) n = Math.min(parseInt(m[2], 10), config.groupMemoryMessages);
      if (/^\d+$/.test(namePart)) {
        n = Math.min(parseInt(namePart, 10), config.groupMemoryMessages);
      } else if (namePart) {
        const found = groups.find(namePart);
        if (!found) {
          await reply(`I couldn't find a group matching "${namePart}". Try !groups.`);
          return true;
        }
        if (Array.isArray(found)) {
          await reply(
            `Several groups match "${namePart}":\n${found.map((g) => `- ${g.subject}`).join("\n")}\nBe more specific.`
          );
          return true;
        }
        targetJid = found.id;
      }
      if (!targetJid) {
        await reply("In a direct chat, tell me which group: !summary <group name> [n]");
        return true;
      }

      const log = memory.getGroupLog(targetJid, n);
      if (!log.length) {
        await reply(`I haven't seen any messages in *${groups.name(targetJid)}* yet. I only remember messages that arrive while I'm running.`);
        return true;
      }
      const transcript = log
        .map((e) => `[${formatTime(e.ts)}] ${e.sender}: ${e.text}`)
        .join("\n");
      try {
        const { text } = await askClaude({
          history: [],
          userContent: `Summarise this WhatsApp group conversation from "${groups.name(targetJid)}" (${log.length} most recent messages). Give the key topics, any decisions, questions left open, and action items with who owns them. Be concise and use WhatsApp-friendly plain text.\n\n${transcript}`,
        });
        await reply(`*Summary of ${groups.name(targetJid)}* (last ${log.length} messages)\n\n${text}`);
      } catch (err) {
        await reply(describeError(err));
      }
      return true;
    }

    case "ai": {
      if (!msg.isGroup) {
        await reply("Use !ai on|off|always inside the group you want to change.");
        return true;
      }
      const want = args[0].toLowerCase();
      const mode = want === "on" || want === "mention" ? "mention" : want;
      memory.setGroupMode(msg.chatJid, mode);
      const explain = {
        mention: "I'll reply here when @mentioned, replied to, or triggered.",
        always: "I'll reply to every message here.",
        off: "I'll stay silent here (still remembering messages for !summary).",
      }[mode];
      await reply(`Group mode set to *${mode}*. ${explain}`);
      return true;
    }

    case "clear": {
      memory.clearHistory(msg.chatJid);
      await reply("Conversation history for this chat cleared.");
      return true;
    }
  }
  return false;
}
