# CLAUDE.md - Kluvs Discord Bot

## Quick Start

**Core files:**
- `bot.py::BookClubBot` — Main bot
- `cogs/` — Commands (general, session, admin)
- `api/bookclub_api.py` — Supabase API client
- `config.py::BotConfig` — Configuration
- `tests/` — Unit tests

**Commands:**
```bash
make test          # Run tests
make coverage      # Coverage report
make run           # Run bot
```

**Environment Variables (for development):**
```
ENV=dev
TEST_GUILD_ID=test_guild_snowflake_id
DEV_TOKEN=your_discord_bot_token
DEV_SUPABASE_URL=http://localhost:54321
DEV_SUPABASE_KEY=your_supabase_anon_key
KEY_OPEN_AI=your_openai_api_key
GOOGLE_BOOKS_API_KEY=your_google_books_api_key
```

**Environment Variables (for production):**
```
TOKEN=your_discord_bot_token
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
KEY_OPEN_AI=your_openai_api_key
GOOGLE_BOOKS_API_KEY=your_google_books_api_key
```

## Architecture

**Cog pattern:** Slash commands organized by functional area:
- `general_commands.py` — Help, usage, support, donate, feedback, vote, version
- `session_commands.py` — Reading sessions (view details, due dates, discussions)
- `member_commands.py` — Join/leave book clubs
- `admin_commands.py` — Server/club/member/session/discussion management (slash commands)

**Service layer:** `OpenAIService` (GPT summaries and chat), `BookClubAPI` (REST client)

**API client:** Custom exceptions, retry logic, guild-aware ops, book search autocomplete

**Database (Supabase):** Servers, Clubs, Members, Sessions, Books, Discussions with Discord event sync

## Project Structure

```
kluvs-bot/
├── api/              # Supabase API client
├── cogs/             # Commands (general, session, member, admin)
├── events/           # Message handlers
├── services/         # OpenAI integration
├── tests/            # Unit tests
├── utils/            # Utilities
├── bot.py            # Main bot
├── config.py         # Config
└── main.py           # Entry point
```

## Code Patterns

**Error handling:** Custom exceptions from `api.bookclub_api` (APIError, ResourceNotFoundError), user-friendly messages from `utils.constants`

**Embeds:** Use `utils.embeds.create_embed()` with colors from `utils.constants.COLORS`, include user context in messages

**Slash commands:** Use `@bot.tree.command()` decorator, support autocomplete for book search and discussion selection

**Async:** All commands/interactions are async; use `AsyncMock` in tests for async methods

**Logging:** Daily rotating logs in `logs/bot.log` with context (guild_id, user_id, member_id)

## Testing

```bash
python tests/run_tests.py              # Run all
coverage run --source=. tests/run_tests.py && coverage report  # With coverage
python -m unittest tests.test_bookclub_api  # Specific module
```

## When Working Here

1. **Always run tests** before changes
2. **Add tests** for new features
3. **Follow existing patterns** (cogs, services, API structure)
4. **Use user-friendly messages** from constants
5. **Log with context** (guild_id, user_id)
6. **Update CLAUDE.md** for architecture changes

## External Services

- **Discord API** — Bot interface
- **Supabase** — PostgreSQL + Edge Functions
- **OpenAI GPT-3.5** — Summaries & chat
