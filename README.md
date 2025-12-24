# Quill the Librarian

[![Tests](https://github.com/ivangarzab/quill-bot/workflows/Run%20Tests/badge.svg)](https://github.com/ivangarzab/quill-bot/actions)
[![codecov](https://codecov.io/gh/ivangarzab/quill-bot/branch/main/graph/badge.svg)](https://codecov.io/gh/ivangarzab/quill-bot)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Discord.py](https://img.shields.io/badge/discord.py-latest-blue.svg)](https://github.com/Rapptz/discord.py)

A Discord bot designed to be the ultimate companion for book clubs! Quill manages reading sessions, tracks member progress, schedules discussions, and provides AI-powered book summaries and interactive features.

![Quill the Librarian](/assets/avatar-v1.png)

## Features

### Book Club Management
- **Multi-Server Support** - Manage book clubs across different Discord servers
- **Session Tracking** - Keep track of current books, due dates, and reading progress
- **Member Management** - Track member participation and points
- **Discussion Scheduling** - Organize and schedule discussion topics
- **Shame List** - Light-hearted tracking of members who don't finish books

### AI-Powered Features
- **Book Summaries** - Get AI-generated summaries of your current book using GPT-3.5-turbo
- **Interactive Chat** - Chat with Quill using the `/robot` command or natural language
- **Smart Responses** - Context-aware error messages and helpful guidance

### Utility Commands
- **Weather Integration** - Check current weather conditions for any city
- **Fun Facts** - Learn random book-related trivia
- **Interactive Games** - Dice rolling, coin flipping, and random choice selection

### Personality
Quill has a friendly librarian personality with:
- Book-themed responses and reactions
- Random greetings and interactions (10% chance)
- Daily reading reminders at 5:00 PM Pacific Time
- Multilingual welcome messages for new members

## Quick Start

### Installation

1. **Invite Quill to your Discord server:**

   [Click here to invite Quill](https://discord.com/oauth2/authorize?client_id=1327910712454152275)

2. **Set up your book club:**

   Use `/help` to get started with setting up your first book club session.

### Available Commands

#### General Commands
- `/help` - Get started guide and orientation
- `/usage` - View complete list of available commands

#### Session Management
- `/book` - Display current book information
- `/duedate` - Show when the current session is due
- `/session` - View full session details (book, dates, progress)
- `/discussions` - See scheduled discussion topics
- `/book_summary` - Get an AI-generated summary of the current book

#### Fun & Interactive
- `/rolldice` - Roll a six-sided die
- `/flipcoin` - Flip a coin (heads or tails)
- `/choose <options>` - Randomly choose from comma-separated options

#### Utilities
- `/weather <city>` - Get current weather for a city
- `/funfact` - Learn a random book-related fun fact
- `/robot <prompt>` - Chat with Quill's AI (also works with "robot, <message>")

#### Admin
- `!version` - Display bot version (prefix command)

## Development

### Prerequisites
- Python 3.9 or higher
- Discord Developer Account
- Supabase Account (for database)
- OpenAI API Key (for AI features)
- Weatherbit.io API Key (for weather features)

### Local Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ivangarzab/quill-bot.git
   cd quill-bot
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**

   Create a `.env` file in the project root:
   ```bash
   # Development Mode
   ENV=dev
   DEV_TOKEN=your_discord_bot_token_here

   # API Keys
   KEY_SUPABASE=your_supabase_anon_key
   KEY_OPEN_AI=your_openai_api_key
   KEY_WEATHER=your_weatherbit_api_key

   # Supabase Configuration
   URL_SUPABASE=your_supabase_project_url
   URL_EDGE_FUNCTION=your_edge_function_base_url
   ```

5. **Run the bot:**
   ```bash
   python main.py
   ```

### Running Tests

Run all tests:
```bash
python tests/run_tests.py
```

Run tests with coverage:
```bash
coverage run --source=. tests/run_tests.py
coverage report
```

Generate HTML coverage report:
```bash
coverage html
# Open htmlcov/index.html in your browser
```

### Project Structure

```
quill-bot/
├── api/                    # Supabase Edge Functions API client
├── cogs/                   # Discord command modules
│   ├── admin_commands.py
│   ├── fun_commands.py
│   ├── general_commands.py
│   ├── session_commands.py
│   └── utility_commands.py
├── database/              # Database clients and utilities
├── events/                # Discord event handlers
├── services/              # External service integrations
│   ├── openai_service.py
│   └── weather_service.py
├── tests/                 # Unit test suite (13 test files)
├── utils/                 # Shared utilities
├── bot.py                 # Main bot class
├── main.py                # Application entry point
└── config.py              # Configuration management
```

## Architecture

### Technology Stack
- **Discord.py** - Discord bot framework with slash commands
- **Supabase** - PostgreSQL database with Edge Functions
- **OpenAI GPT-3.5-turbo** - AI-powered features
- **Weatherbit.io** - Weather data provider
- **Python 3.9+** - Core runtime

### Design Patterns
- **Command Cog Pattern** - Commands organized by functional area
- **Service Layer Pattern** - External services abstracted into dedicated classes
- **API Client Pattern** - Comprehensive REST client for backend communication
- **Multi-Server Architecture** - Guild-aware operations for multiple Discord servers

### Database Schema
- **Servers** - Discord guild registrations
- **Clubs** - Book club definitions linked to channels
- **Members** - User profiles shared across clubs
- **Sessions** - Active reading sessions
- **Books** - Book information
- **Discussions** - Scheduled discussion topics
- **ShameList** - Members who didn't finish books

## Testing

The project maintains comprehensive test coverage with:
- **13 test files** covering all major components
- **~37% code coverage** (tracked via codecov)
- **Automated CI/CD** via GitHub Actions
- **Mock-based testing** for Discord and external API interactions

See [CLAUDE.md](CLAUDE.md) for detailed testing documentation.

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Write tests for new features
4. Ensure all tests pass
5. Submit a pull request to `main`

All pull requests trigger automated testing and coverage reporting.

## CI/CD

The project uses GitHub Actions for continuous integration:
- **Automated Testing** on all PRs and pushes to main
- **Code Coverage** reporting via codecov
- **Python 3.9** test environment
- **Environment Variables** managed via GitHub Secrets

## Documentation

- **[CLAUDE.md](CLAUDE.md)** - Comprehensive guide for AI assistants and developers
- **[SECURITY.md](SECURITY.md)** - Privacy policy and security measures
- **[TERMS.md](TERMS.md)** - Terms of use and disclaimers

## Roadmap

### Current Focus
- Increasing test coverage to 70%+
- Migrating hardcoded club IDs to dynamic lookup
- Fixing database schema mismatches

### Future Enhancements
- Command cooldowns and rate limiting
- Type hints throughout codebase
- Automated code formatting and linting
- Integration tests for Discord interactions
- Additional AI features (book recommendations, reading analytics)

## License

This project is currently unlicensed. See [TERMS.md](TERMS.md) for usage terms.

## Contact

**Maintainer:** Ivan Garza
**Email:** ivangb6@gmail.com
**Repository:** https://github.com/ivangarzab/quill-bot.git

## Acknowledgments

- Built with [Discord.py](https://github.com/Rapptz/discord.py)
- Database powered by [Supabase](https://supabase.com)
- AI features powered by [OpenAI](https://openai.com)
- Weather data from [Weatherbit.io](https://www.weatherbit.io)

---

Made with books and code by Ivan Garza
