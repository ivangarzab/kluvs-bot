# 📚 Kluvs - Discord Book Club Bot

[![Tests](https://github.com/kluvs-app/kluvs-bot/workflows/Run%20Tests/badge.svg)](https://github.com/kluvs-app/kluvs-bot/actions)
[![codecov](https://codecov.io/gh/kluvs-app/kluvs-bot/branch/main/graph/badge.svg)](https://codecov.io/gh/kluvs-app/kluvs-bot)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Discord.py](https://img.shields.io/badge/discord.py-latest-blue.svg)](https://github.com/Rapptz/discord.py)

<div align="center">

[![Discord Bots](https://top.gg/api/widget/1327360422294192199.svg)](https://top.gg/bot/1327360422294192199)

</div>

A focused Discord bot for managing book clubs with session tracking, member management, and AI-powered features.

## Features

- **Multi-Server Support** — Manage book clubs across different Discord servers
- **Session Tracking** — Track current books, due dates, and reading progress
- **Member Management** — Track participation and member details
- **Discussion Scheduling** — Organize discussion topics for sessions
- **AI Features** — Book summaries and chat with OpenAI GPT-3.5-turbo
- **Personality** — Librarian-themed responses and book-focused interactions

## Commands

### Reading Commands
- `/help` — Getting started guide
- `/usage` — View all available commands
- `/session` — Show all session details
- `/book` — Show current book details
- `/due_date` — Show session due date
- `/discussions` — View scheduled discussion topics
- `/book_summary` — AI-generated book summary

### Member Commands
- `/join` — Join the book club in the current channel
- `/leave` — Leave the book club in the current channel

### Admin Commands
*Requires guild owner or club admin role*

**Setup & Server (guild owner only):**
- `/setup` — First-run wizard: register server and create a club
- `/server_register` — Register this Discord server
- `/server_update` — Update server name
- `/server_delete` — Delete server and all data

**Club Management:**
- `/club_create` — Create a new book club
- `/club_update` — Update club details (name, channel)
- `/club_delete` — Delete the club

**Member Management:**
- `/member_add` — Add a member to the club
- `/member_remove` — Remove a member
- `/member_role` — Set member role (admin/member)

**Session Management:**
- `/session_create` — Create a reading session
- `/session_update` — Update session (due date, book)
- `/session_delete` — Delete the active session

**Discussion Management:**
- `/discussion_add` — Add a discussion topic to a session
- `/discussion_update` — Update a discussion
- `/discussion_delete` — Delete a discussion
- `/discussion_sync` — Sync discussions to Discord events

**Other:**
- `/admin_help` — Show detailed admin command reference
- `/version` — Display bot version

## Quick Start

### Invite to Server
[Click to invite Kluvs bot](https://discord.com/oauth2/authorize?client_id=1327360422294192199)


### Local Development

**Prerequisites:**
- Python 3.9+
- Discord Bot Token
- Supabase Account
- OpenAI API Key

**Setup:**
```bash
git clone https://github.com/kluvs-app/kluvs-bot.git
cd kluvs-bot
make install
```

**Create `.env` file:**
```
ENV=dev
TOKEN=your_discord_bot_token
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
KEY_OPEN_AI=your_openai_api_key
GOOGLE_BOOKS_API_KEY=your_google_books_api_key
```

**Run:**
```bash
make run
```

**Tests:**
```bash
make test          # Run all tests
make coverage      # Run with coverage report
```

## Architecture

- **discord.py** — Discord bot framework
- **Supabase** — PostgreSQL database with Edge Functions
- **OpenAI** — AI summaries and chat
- **Python 3.9+** — Core runtime

**Design patterns:**
- Command cogs organized by functional area
- Service layer for external API integrations
- API client with custom exception handling
- Multi-server guild-aware operations

## Testing

Run tests with:
```bash
make test
```

View coverage:
```bash
make coverage
```

## Development

- Follow existing code patterns
- Add tests for new features
- Run `make test` before submitting PRs
- Update CLAUDE.md for architectural changes
