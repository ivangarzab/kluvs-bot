# CLAUDE.md - AI Assistant Context Guide

This document provides comprehensive context about the Quill the Librarian Discord bot for AI assistants working on this codebase.

## Project Overview

**Project Name:** Quill the Librarian
**Type:** Discord Bot for Book Clubs
**Language:** Python 3.9+
**Architecture:** Modular command-based bot with external API integration
**Current Version:** 0.0.1
**Repository:** https://github.com/ivangarzab/quill-bot.git

### Purpose

Quill is a Discord bot designed to manage book club activities across multiple Discord servers. It handles session management, member tracking, discussion scheduling, and provides AI-powered book summaries and interactions. The bot features a librarian personality with book-themed responses.

## Project Structure

```
quill-bot/
├── api/                    # Supabase Edge Functions API client
│   └── bookclub_api.py    # Full REST API client (716 lines)
├── cogs/                   # Discord command modules (organized by category)
│   ├── admin_commands.py  # Bot administration
│   ├── fun_commands.py    # Entertainment commands
│   ├── general_commands.py # Help and usage info
│   ├── session_commands.py # Book session management
│   └── utility_commands.py # Weather, AI chat, fun facts
├── events/                # Discord event handlers
│   └── message_handler.py # Message events, greetings, reactions
├── services/              # External service integrations
│   ├── openai_service.py  # OpenAI GPT-3.5-turbo wrapper
│   └── weather_service.py # Weatherbit.io API wrapper
├── tests/                 # Comprehensive unit test suite (18 test files)
│   ├── test_*.py          # Individual test modules
│   └── run_tests.py       # Test runner
├── utils/                 # Shared utilities
│   ├── constants.py       # Bot messages, colors, fun facts
│   ├── embeds.py          # Discord embed helpers
│   └── schedulers.py      # Scheduled tasks (daily reminders)
├── .github/workflows/     # CI/CD configuration
│   └── run-tests.yml      # GitHub Actions test workflow with codecov
├── bot.py                 # Main BookClubBot class
├── main.py                # Application entry point
├── config.py              # Environment configuration management
└── setup.py               # Package configuration
```

## Architecture Patterns

### 1. Command Cog Pattern
Commands are organized into Discord.py cogs by functional area:
- **General**: Help and orientation commands
- **Session**: Book club session management
- **Fun**: Entertainment and random commands
- **Utility**: Weather, AI chat, fun facts
- **Admin**: Bot administration (prefix commands)

### 2. Service Layer Pattern
External services are abstracted into dedicated service classes:
- `OpenAIService`: Handles GPT API calls with retry logic and rate limiting
- `WeatherService`: Handles Weatherbit.io API calls with error handling

### 3. API Client Pattern
The `BookClubAPI` class provides a complete REST client for Supabase Edge Functions:
- Custom exception hierarchy for different error types
- Guild-aware operations (multi-server support)
- Comprehensive CRUD operations for all resources
- Retry logic and detailed error handling

### 4. Multi-Server Architecture
Recent addition (PR #8) to support multiple Discord servers:
- Server registration and management
- Guild ID passed with all API calls
- Clubs can exist across different servers

## Core Components

### Bot Initialization (bot.py)

The `BookClubBot` class extends `discord.Client`:
- Loads all command cogs automatically
- Sets up daily rotating log files (logs/bot.log)
- Implements global error handling with user-friendly messages
- Manages command tree synchronization
- Uses Discord intents: guilds, members, messages, message_content

### Configuration (config.py)

The `BotConfig` class manages environment variables:
- Dev/Prod mode switching (ENV=dev or ENV=prod)
- Token management (DEV_TOKEN vs TOKEN)
- API key validation (OpenAI, Weather, Supabase)
- Currently has hardcoded club IDs (TODO: migrate to dynamic lookup)

### API Client (api/bookclub_api.py)

Comprehensive REST API client with custom exceptions:

**Exception Hierarchy:**
- `APIError` (base exception)
  - `ResourceNotFoundError` (404 errors)
  - `ValidationError` (400 errors)
  - `AuthenticationError` (401 errors)

**Resource Operations:**
- Servers: register, get, update, delete
- Clubs: create, read, update, delete, find_by_channel
- Members: create, read, update, delete
- Sessions: create, read, update, delete

**Error Handling:**
- Automatic retry with exponential backoff
- User-friendly error messages from `utils.constants`
- Detailed logging

### Database Schema

**Main Tables (Supabase PostgreSQL):**
= `Servers` - Discord server definitions (linked to Clubs)
- `Clubs` - Book club definitions (linked to Discord channels)
- `Members` - User profiles (shared across clubs)
- `MemberClubs` - Many-to-many relationship
- `Books` - Book information
- `Sessions` - Active reading sessions
- `Discussions` - Scheduled discussion topics
- `ShameList` - Members who didn't finish books

All database operations are handled through the `api/bookclub_api.py` client which communicates with Supabase Edge Functions.

## Commands Reference

### Slash Commands

**General Commands:**
- `/help` - Getting started guide and orientation
- `/usage` - Complete list of available commands

**Session Commands:**
- `/book` - Display current book information
- `/duedate` - Show when the current session is due
- `/session` - Full session details (book, dates, progress)
- `/discussions` - View scheduled discussion topics
- `/book_summary` - AI-generated summary of the current book

**Fun Commands:**
- `/rolldice` - Roll a six-sided die
- `/flipcoin` - Flip a coin (heads/tails)
- `/choose <options>` - Randomly choose from comma-separated options

**Utility Commands:**
- `/weather <city>` - Get current weather for a city
- `/funfact` - Random book-related fun fact
- `/robot <prompt>` - Chat with AI (also works with text: "robot, <message>")

**Admin Commands:**
- `!version` - Display bot version (prefix command, not slash)

### Event Handlers

**Message Events (events/message_handler.py):**
- Random bot greetings (10% chance)
- Random reactions to messages (10% chance)
- Keyword detection for "robot" commands
- Member join welcome messages (multilingual)

**Scheduled Tasks (utils/schedulers.py):**
- Daily reading reminders at 5:00 PM Pacific Time
- 40% probability trigger for each reminder
- Uses Discord task loop

## Testing Infrastructure

### Test Framework
- **Framework:** Python unittest
- **Coverage Tool:** Coverage.py with codecov integration
- **Runner:** Custom runner in `tests/run_tests.py`
- **IDE Support:** VS Code unittest configuration

### Test Organization
18 test files covering all major components:
- `test_bookclub_api.py` (680+ lines) - API client comprehensive tests
- `test_session_commands.py` (340 lines) - Session command tests
- `test_general_commands_comprehensive.py` - Help and usage commands
- `test_utility_commands_comprehensive.py` - Weather, funfact, robot commands
- `test_fun_commands_comprehensive.py` - Dice, coin, choose commands
- `test_message_handler_comprehensive.py` - Event handler tests
- `test_schedulers_comprehensive.py` - Scheduled task tests
- `test_admin_commands.py` - Admin command tests
- `test_openai_service.py` (230 lines) - OpenAI service tests
- `test_utility_commands.py` (200 lines) - Utility commands
- `test_schedulers.py` (191 lines) - Scheduled tasks
- `test_fun_commands.py` (145 lines) - Fun commands
- `test_message_handler.py` (145 lines) - Event handlers
- `test_config.py` (132 lines) - Configuration
- `test_embeds.py` (127 lines) - Embed utilities
- `test_weather_service.py` (112 lines) - Weather service
- `test_general_commands.py` (103 lines) - General commands
- `run_tests.py` (21 lines) - Test runner

### Coverage Configuration
Current coverage: **~37%** (tracked via codecov)

Coverage excludes:
- `tests/*` - Test files themselves
- `*/__pycache__/*` - Compiled bytecode
- `*/site-packages/*` - Dependencies
- `setup.py` - Package config

### Running Tests

**Locally:**
```bash
# Run all tests
python tests/run_tests.py

# With coverage
coverage run --source=. tests/run_tests.py
coverage report
coverage xml  # Generate XML for codecov
```

**CI/CD:**
Tests run automatically on:
- Pull requests to main
- Pushes to main branch
- Coverage uploaded to codecov automatically

## Dependencies

### Core Dependencies
```
discord.py      # Discord bot framework
python-dotenv   # Environment variable management
supabase        # Supabase client library
pytz            # Timezone support (Pacific Time)
requests        # HTTP library
openai          # OpenAI API client
coverage        # Code coverage tool
codecov         # Codecov integration
```

### External Services
1. **Discord API** - Bot interface
2. **Supabase** - PostgreSQL database with Edge Functions
3. **OpenAI GPT-3.5-turbo** - AI summaries and chat
4. **Weatherbit.io** - Weather data

## Environment Variables

### Required for Production
```bash
ENV=prod
TOKEN=<discord_bot_token>
KEY_SUPABASE=<supabase_anon_key>
KEY_OPEN_AI=<openai_api_key>
KEY_WEATHER=<weatherbit_api_key>
URL_SUPABASE=<supabase_project_url>
URL_EDGE_FUNCTION=<edge_function_base_url>
```

### Required for Development
```bash
ENV=dev
DEV_TOKEN=<discord_dev_bot_token>
KEY_SUPABASE=<supabase_anon_key>
KEY_OPEN_AI=<openai_api_key>
KEY_WEATHER=<weatherbit_api_key>
URL_SUPABASE=<supabase_project_url>
URL_EDGE_FUNCTION=<edge_function_base_url>
```

## Development Workflow

### Local Setup
1. Clone repository
2. Create virtual environment: `python -m venv .venv`
3. Activate: `source .venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Create `.env` file with required variables
6. Run bot: `python main.py`
7. Run tests: `python tests/run_tests.py`

### Git Workflow
- **Main branch:** `main`
- **Current feature branch:** `feature/quality-of-life-w-claude`
- **CI/CD:** GitHub Actions runs tests on PR and push to main

### Code Style
- No formal linting configured (opportunity for improvement)
- Follow existing patterns in codebase
- Add tests for new features
- Update CLAUDE.md when making architectural changes

## Common Patterns and Conventions

### Error Handling
1. Use custom exceptions from `api.bookclub_api` for API errors
2. User-friendly error messages from `utils.constants.ERROR_MESSAGES`
3. Log all errors with appropriate context
4. Send contextual error embeds to users

### Discord Embeds
- Use `utils.embeds.create_embed()` for consistency
- Color scheme defined in `utils.constants.COLORS`
- Timestamps automatically use Pacific timezone
- Include relevant fields and footers

### Async Patterns
- All Discord commands and interactions are async
- Use `AsyncMock` in tests for Discord interactions
- Services like OpenAI have async wrappers

### Logging
- Daily rotating logs in `logs/bot.log`
- Retention: 7 days
- Comprehensive logging in API client and services
- Include context (guild_id, user_id) in log messages

## Recent Changes and Evolution

### Major Milestones
1. **Multi-Server Support (PR #8)** - Added guild awareness
2. **Unit Test Setup (PR #7)** - VS Code integration and cleanup
3. **Supabase Edge Functions (PR #6)** - New API architecture
4. **Monolith Teardown (PR #5)** - Modular structure
5. **CI/CD (commit b054341)** - GitHub Actions workflow
6. **Supabase Backend (PR #4)** - Database migration
7. **OpenAI Integration (PR #3)** - AI features

### Migration Notes
- All database operations now go through `api/bookclub_api.py` (Supabase Edge Functions)
- Hardcoded club IDs in config.py need migration to dynamic lookup

## Known Issues and TODOs

### Active TODOs (from code comments)
1. **config.py**: Hardcoded CLUB_IDS need to be dynamic
2. **Type hints**: Missing in cog files
3. **Linting**: No automated code style checks in CI

### Improvement Opportunities
1. Increase test coverage from 39% to 70%+
2. Add type hints throughout codebase
3. Implement pre-commit hooks for formatting
4. Add linting (pylint, flake8, or ruff)
5. Document API endpoints
6. Add integration tests for Discord interactions
7. Implement rate limiting for commands
8. Add command cooldowns

## Bot Personality and Theme

### Librarian Persona
- Named "Quill the Librarian"
- Book-themed responses and terminology
- Error messages reference library/book concepts
- Professional but friendly tone

### Message Templates
Defined in `utils/constants.py`:
- **Greetings:** Various casual greetings
- **Reactions:** Book-related reactions to messages
- **Fun Facts:** Book trivia and statistics
- **Reading Reminders:** Encouraging daily reading messages
- **Error Messages:** Contextual error responses (404, 400, 401, connection)

### Timing and Automation
- Daily reminders at 5:00 PM Pacific Time
- 40% probability for reminder trigger
- 10% chance of random greeting
- 10% chance of random reaction

## Debugging Tips

### Common Issues
1. **Import Errors:** Ensure virtual environment is activated
2. **Database Connection:** Check Supabase credentials in .env
3. **API Errors:** Verify Edge Function URL and API keys
4. **Discord Permissions:** Bot needs appropriate intents enabled

### Useful Commands
```bash
# Check coverage
coverage run --source=. tests/run_tests.py && coverage report

# View logs
tail -f logs/bot.log

# Test specific module
python -m unittest tests.test_bookclub_api

# Run all tests
python tests/run_tests.py
```

### Log Locations
- Application logs: `logs/bot.log` (rotates daily, 7-day retention)
- Test output: stdout during test execution
- Coverage reports: `coverage.xml`, `htmlcov/` (ignored in git)

## CI/CD Pipeline

### GitHub Actions Workflow
**File:** `.github/workflows/run-tests.yml`

**Triggers:**
- Pull requests to main
- Pushes to main

**Steps:**
1. Checkout code
2. Setup Python 3.9
3. Install dependencies
4. Run tests with coverage
5. Generate coverage XML
6. Upload to codecov

**Secrets Required:**
- `DEV_TOKEN` - Discord bot token
- `KEY_WEATHER` - Weatherbit API key
- `KEY_OPEN_AI` - OpenAI API key
- `CODECOV_TOKEN` - Codecov upload token

## API Architecture

### Supabase Edge Functions
The bot communicates with a Supabase backend via Edge Functions (serverless):

**Base URL Pattern:** `{URL_EDGE_FUNCTION}/{resource}`

**Resources:**
- `/servers` - Discord guild registration
- `/clubs` - Book club CRUD
- `/members` - Member management
- `/sessions` - Session management

**Authentication:**
- Supabase anon key in headers
- Guild ID for multi-server isolation

**Error Handling:**
- HTTP status codes map to custom exceptions
- Retry logic for transient failures
- Detailed error messages for users

## Final Notes for AI Assistants

### When Working on This Codebase
1. **Always run tests** before submitting changes
2. **Add tests** for new features
3. **Update CLAUDE.md** if architecture changes
4. **Follow existing patterns** (cogs, services, API client structure)
5. **Check coverage** impact of changes
6. **Use user-friendly error messages** from constants.py
7. **Log appropriately** with context
8. **Maintain Discord best practices** (embeds, interactions, permissions)

### Quick Reference
- **Main entry:** `main.py`
- **Bot class:** `bot.py::BookClubBot`
- **Commands:** `cogs/*.py`
- **API client:** `api/bookclub_api.py`
- **Config:** `config.py::BotConfig`
- **Tests:** `tests/test_*.py`
- **Run tests:** `python tests/run_tests.py`
- **Coverage:** `coverage run --source=. tests/run_tests.py && coverage report`

### Contact
**Maintainer:** Ivan Garza (ivangb6@gmail.com)
**Repository:** https://github.com/ivangarzab/quill-bot.git
**Discord Install:** https://discord.com/oauth2/authorize?client_id=1327910712454152275
