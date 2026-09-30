# Claude on WhatsApp (with group access)

Give Claude its own WhatsApp number. This bot links to a WhatsApp account the same way
WhatsApp Web does (scan a QR code), so it works with a normal number, no Meta Business
API or approval needed, and it can see and talk in every **group** that number is in.

What it does:

- **Direct chats**: anyone who messages the number gets a Claude reply, with per-chat memory.
- **Groups**: Claude sits in your groups, remembers what is said, and replies when
  it is @mentioned, replied to, or a message starts with a trigger word (`claude ...`, `!ai ...`).
  You can also set a group to `always` (reply to everything) or `off` (listen only).
- **Group tools** for the owner: `!groups` lists every group the number is in,
  `!summary` summarises a group's recent messages, `!ai on|off|always` changes how Claude
  behaves per group, all from inside WhatsApp (even from your own phone).
- **Images**: send a photo with a caption and Claude looks at it.

## 1. Setup

You need Node.js 20 or newer, git, and an Anthropic API key
(https://platform.claude.com -> API keys).

**Mac, first time only**: install Node.js with Homebrew, or download the installer
from https://nodejs.org (the "LTS" button) and run it.

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install node
node -v
```

Then get the code and start the bot (one command per line, no trailing comments):

```bash
git clone -b claude/whatsapp-groups-access-0jddmi https://github.com/ahdinstallation-sketch/ahdprofit.git
cd ahdprofit/whatsapp-bot
npm install
cp .env.example .env
open -e .env
```

In the `.env` file that opens, paste your key after `ANTHROPIC_API_KEY=` and put your
own number (digits only, with country code) after `OWNER_NUMBERS=`. Save, close, then:

```bash
npm start
```

A QR code prints in the terminal. On the phone that owns the WhatsApp number:
**WhatsApp -> Settings -> Linked devices -> Link a device**, then scan it.

Once it says `Connected`, message the number from another phone, or type `!help` in
any chat from your own phone.

> Use a spare number if you can. Linking Claude to your personal number works, but then
> every DM you receive gets answered by Claude (set `DM_ENABLED=false` to stop that).

The session is saved in `auth/`, so restarts don't need a new scan. `npm run logout`
wipes it if you ever want to link a different number.

## 2. Using it in groups

Add the number to a group like any contact. From then on the bot:

1. Remembers every message in that group (rolling window, `GROUP_MEMORY_MESSAGES`).
2. Replies when someone @mentions it, replies to one of its messages, or starts a
   message with a trigger word (`TRIGGER_WORDS`, default `!ai`, `claude`, `@claude`, `hey claude`).
3. When it replies, it sees the last `GROUP_CONTEXT_MESSAGES` messages of that group so
   the answer fits the conversation.

Owner commands (work in any chat, including from the linked phone itself):

| Command | What it does |
| --- | --- |
| `!help` | Show commands (anyone can run this one) |
| `!status` | Model, group count, current chat's mode |
| `!groups` | List every group the number is in, with member count, mode and JID |
| `!summary` | Summarise the last 50 messages of the current group |
| `!summary 200` | Summarise the last 200 messages |
| `!summary Family Group` | Summarise another group by name (works from a DM too) |
| `!ai always` | Claude answers every message in this group |
| `!ai on` | Back to mention/trigger-only (default) |
| `!ai off` | Claude stays silent in this group but keeps listening for `!summary` |
| `!clear` | Forget the conversation history of this chat |

To restrict the bot to certain groups only, set `ALLOWED_GROUPS` in `.env` to a
comma-separated list of group names (substring match) or JIDs from `!groups`.

## 3. Configuration

Everything lives in `.env` (see `.env.example` for all options):

| Variable | Default | Meaning |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | | required |
| `CLAUDE_MODEL` | `claude-opus-5-5` | any current Claude model id |
| `CLAUDE_EFFORT` | `medium` | `low` is fastest and cheapest, `high`/`xhigh` for harder questions |
| `BOT_NAME` / `SYSTEM_PROMPT` | Claude | personality and rules |
| `OWNER_NUMBERS` | | digits only, e.g. `923001234567,447700900123` |
| `DM_ENABLED` | `true` | reply to direct messages from anyone |
| `GROUP_MODE` | `mention` | default group behaviour: `mention`, `always` or `off` |
| `TRIGGER_WORDS` | `!ai,claude,@claude,hey claude` | words that summon Claude in a group |
| `ALLOWED_GROUPS` | (all) | restrict to some groups |
| `GROUP_CONTEXT_MESSAGES` | 40 | group messages Claude sees when replying |
| `GROUP_MEMORY_MESSAGES` | 300 | messages remembered per group for `!summary` |
| `HISTORY_TURNS` | 30 | conversation turns remembered per chat |

Refusal fallback is on: if the model declines a request for policy reasons, the API
automatically retries it on Anthropic's default substitute model in the same call.

## 4. Running it 24/7

The bot only sees messages while it is running, so keep it on a machine that stays up
(a cheap VPS, a Raspberry Pi, or Docker):

```bash
docker build -t claude-whatsapp .
docker run -it --env-file .env -v $(pwd)/auth:/app/auth -v $(pwd)/data:/app/data claude-whatsapp
# scan the QR once; afterwards run with -d instead of -it
```

Or with pm2: `npx pm2 start src/index.js --name claude-whatsapp`.

## 5. Notes and limits

- This uses the open-source Baileys library, which speaks the WhatsApp Web protocol.
  It is not an official WhatsApp API. Keep the bot polite (no spam, no mass messaging)
  or WhatsApp may block the number.
- The linked phone must stay registered on WhatsApp, but it does not need to stay online.
- Memory is a plain JSON file in `data/`. Delete it to start fresh.
- Only text and image messages are understood. Voice notes, videos and documents are
  noted as `[audio]`, `[video]`, `[document]` in the group log.

## Development

```bash
npm test   # unit tests for message routing, mention detection, chunking
```

Files:

- `src/index.js` connection, QR login, reconnects, event wiring
- `src/handler.js` decides when to answer and builds the prompt (group context, images)
- `src/commands.js` owner commands (`!groups`, `!summary`, `!ai`, ...)
- `src/groups.js` directory of groups the number is in
- `src/memory.js` per-chat history, per-group message log, per-group settings
- `src/claude.js` the Anthropic API call
