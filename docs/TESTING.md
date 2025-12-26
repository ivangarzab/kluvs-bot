# Testing Strategy & Guide

This document explains how testing works in the Kluvs Discord bot project, including our testing framework, strategy, and how to run tests.

## Table of Contents
- [Testing Framework](#testing-framework)
- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Coverage](#coverage)
- [Writing Tests](#writing-tests)
- [CI/CD Integration](#cicd-integration)
- [Testing Strategy](#testing-strategy)

## Testing Framework

### Core Tools
- **Framework**: Python's built-in `unittest` module
- **Async Support**: `unittest.IsolatedAsyncioTestCase` for async test methods
- **Mocking**: `unittest.mock` (MagicMock, AsyncMock, patch)
- **Coverage**: `coverage.py` with codecov integration
- **CI/CD**: GitHub Actions

### Why unittest?
We chose `unittest` over pytest because:
- Built-in to Python (no extra dependencies)
- Native async support with `IsolatedAsyncioTestCase`
- Familiar to Python developers
- Works seamlessly with VS Code's test runner

## Test Structure

### Directory Organization
```
tests/
├── run_tests.py                              # Test runner script
├── test_bookclub_api.py                      # API client tests (680+ lines)
├── test_session_commands.py                  # Session command tests (340 lines)
├── test_message_handler.py                   # Event handler tests
├── test_schedulers.py                        # Scheduled task tests
├── test_openai_service.py                    # OpenAI service tests
├── test_weather_service.py                   # Weather service tests
├── test_config.py                            # Configuration tests
├── test_embeds.py                            # Embed utility tests
├── test_admin_commands.py                    # Admin command tests
├── test_general_commands_comprehensive.py    # Help/usage command tests
├── test_utility_commands_comprehensive.py    # Utility command tests
├── test_fun_commands_comprehensive.py        # Fun command tests
├── test_fun_commands.py                      # (Legacy) Fun command tests
├── test_general_commands.py                  # (Legacy) General command tests
├── test_utility_commands.py                  # (Legacy) Utility command tests
├── test_message_handler_comprehensive.py     # (Legacy) Message handler tests
└── test_schedulers_comprehensive.py          # (Legacy) Scheduler tests
```

### Test File Naming Convention
- All test files must start with `test_` to be discovered
- Named after the module they test: `test_<module_name>.py`
- Comprehensive test files include `_comprehensive` suffix

### Test Class Structure
```python
import unittest
from unittest.mock import MagicMock, AsyncMock, patch

# For synchronous tests
class TestMyModule(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test"""
        pass

    def test_something(self):
        """Test description"""
        pass

# For asynchronous tests (Discord commands/events)
class TestAsyncModule(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        """Set up test fixtures before each test"""
        pass

    async def test_async_operation(self):
        """Test description"""
        pass
```

## Running Tests

### Quick Start (Using Makefile - Recommended)

```bash
# View all available commands
make help

# Run all tests
make test

# Run with coverage
make coverage

# Generate HTML coverage report
make coverage-html
# Open htmlcov/index.html in browser
```

### Alternative (Direct Python Commands)

```bash
# Run all tests
python tests/run_tests.py

# Run with coverage
coverage run --source=. tests/run_tests.py
coverage report

# Generate HTML coverage report
coverage html
# Open htmlcov/index.html in browser

# Generate XML for codecov
coverage xml
```

### Running Specific Tests
```bash
# Run a specific test file
python -m unittest tests.test_bookclub_api

# Run a specific test class
python -m unittest tests.test_bookclub_api.TestBookClubAPI

# Run a specific test method
python -m unittest tests.test_bookclub_api.TestBookClubAPI.test_register_server

# Run with verbose output
python -m unittest tests.test_bookclub_api -v
```

### VS Code Integration
The project is configured for VS Code's built-in test runner:

1. **Discover tests**: Click the beaker icon in the sidebar
2. **Run all tests**: Click the play button next to "tests"
3. **Run specific test**: Click the play button next to any test file/class/method
4. **Debug tests**: Click the debug icon next to any test

Configuration is in `.vscode/settings.json`:
```json
{
    "python.testing.unittestArgs": ["-v", "-s", "./tests", "-p", "test_*.py"],
    "python.testing.unittestEnabled": true
}
```

## Coverage

### Current Coverage: ~62%

**100% Coverage Achieved:**
- `events/message_handler.py` - Event handlers
- `utils/schedulers.py` - Scheduled tasks
- `services/weather_service.py` - Weather API
- `utils/constants.py` - Constants
- `utils/embeds.py` - Discord embeds
- `api/__init__.py` - API module init

**High Coverage (75%+):**
- `api/bookclub_api.py` - 76% - Main API client
- `config.py` - 82% - Configuration

**Excluded from Coverage:**
- `tests/*` - Test files themselves
- `main.py` - Entry point (just calls bot.run())
- `bot.py` - Discord bot initialization (complex, hard to test)
- `setup.py` - Package configuration

### Coverage Configuration
See `.coveragerc` for configuration:
```ini
[run]
source = .
omit =
    tests/*
    */__pycache__/*
    */site-packages/*
    setup.py
    main.py
    bot.py

[report]
precision = 2

[xml]
output = coverage.xml
```

### Coverage Goals
- **Current**: 62%
- **Target**: 70%+
- **Priority areas for improvement**:
  - Command cogs (currently 15-51%)
  - OpenAI service (currently 53%)

## Writing Tests

### General Principles

1. **One test, one assertion concept** - Each test should verify one specific behavior
2. **Arrange-Act-Assert** - Structure tests clearly:
   ```python
   def test_something(self):
       # Arrange: Set up test data
       data = {"key": "value"}

       # Act: Perform the operation
       result = function_under_test(data)

       # Assert: Verify the outcome
       self.assertEqual(result, expected_value)
   ```
3. **Use descriptive test names** - `test_user_registration_fails_with_invalid_email`
4. **Mock external dependencies** - Never make real API calls or database connections

### Testing Discord Commands

Discord commands are **asynchronous** and require special handling:

```python
class TestDiscordCommand(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        """Set up bot and command mocks"""
        self.bot = MagicMock()
        self.bot.tree = MagicMock()

        # Store registered commands
        self.commands = {}

        def mock_command(**kwargs):
            def decorator(func):
                self.commands[kwargs.get('name')] = {
                    'func': func,
                    'kwargs': kwargs
                }
                return func
            return decorator

        self.bot.tree.command = mock_command

        # Register commands
        setup_my_commands(self.bot)

    async def test_my_command(self):
        """Test the command"""
        # Create mock interaction
        interaction = AsyncMock()
        interaction.response.send_message = AsyncMock()

        # Get and call the command
        command_func = self.commands['my_command']['func']
        await command_func(interaction)

        # Verify behavior
        interaction.response.send_message.assert_called_once()
```

### Testing Event Handlers

Event handlers also require async testing:

```python
class TestEventHandler(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        """Set up bot and event handler mocks"""
        self.bot = MagicMock()
        self.handlers = {}

        def mock_event(func):
            self.handlers[func.__name__] = func
            return func

        self.bot.event = mock_event
        setup_message_handlers(self.bot)

    async def test_on_message(self):
        """Test message handler"""
        # Create mock message
        message = MagicMock()
        message.author = MagicMock(id=123)
        message.content = "test message"
        message.channel = AsyncMock()

        # Call handler
        handler = self.handlers['on_message']
        await handler(message)

        # Verify behavior
        message.channel.send.assert_called()
```

### Mocking Best Practices

#### AsyncMock for async methods
```python
# Correct - for async methods
interaction = AsyncMock()
interaction.response.send_message = AsyncMock()

# Wrong - will not work properly
interaction = MagicMock()  # Don't use for async!
```

#### Patch external dependencies
```python
@patch('requests.get')
def test_api_call(self, mock_get):
    # Mock the response
    mock_response = Mock()
    mock_response.json.return_value = {"data": "value"}
    mock_get.return_value = mock_response

    # Test your code
    result = my_function()

    # Verify
    mock_get.assert_called_once()
```

#### Control randomness
```python
# Make random behavior predictable
with patch('random.random', return_value=0.3):
    with patch('random.choice', return_value="specific_value"):
        # Test code that uses random
        result = function_with_randomness()
```

### Common Patterns

#### Testing API Clients
```python
@patch('requests.post')
def test_create_resource(self, mock_post):
    # Mock successful response
    mock_response = Mock()
    mock_response.json.return_value = {"id": 1, "name": "Test"}
    mock_response.raise_for_status = Mock()
    mock_post.return_value = mock_response

    # Test
    result = self.api.create_resource({"name": "Test"})

    # Verify
    self.assertEqual(result["name"], "Test")
    mock_post.assert_called_once()
```

#### Testing Error Handling
```python
@patch('requests.get')
def test_handles_404_error(self, mock_get):
    # Mock 404 error
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = requests.HTTPError(
        "404 Not Found", response=mock_response
    )
    mock_get.return_value = mock_response

    # Test
    with self.assertRaises(ResourceNotFoundError):
        self.api.get_resource("nonexistent")
```

## CI/CD Integration

### GitHub Actions Workflow

Location: `.github/workflows/run-tests.yml`

**Triggers:**
- All pull requests to `main` branch
- All pushes to `main` branch

**What it does:**
1. Sets up Python 3.9 environment
2. Installs dependencies: `make install`
3. Runs tests with coverage: `make coverage`
4. Generates coverage XML: `.venv/bin/python -m coverage xml`
5. Uploads coverage to codecov

**Required GitHub Secrets:**
- `DEV_TOKEN` - Discord bot token (for test environment)
- `KEY_WEATHER` - Weatherbit API key
- `KEY_OPEN_AI` - OpenAI API key
- `CODECOV_TOKEN` - Codecov upload token

### Codecov Integration

Coverage reports are automatically uploaded to [codecov.io](https://codecov.io) on every CI run.

**Setup:**
1. Sign up at codecov.io and link your GitHub repo
2. Add `CODECOV_TOKEN` to GitHub repository secrets
3. Coverage badge will update automatically in README

**Coverage badge:**
```markdown
[![codecov](https://codecov.io/gh/ivangarzab/quill-bot/branch/main/graph/badge.svg)](https://codecov.io/gh/ivangarzab/quill-bot)
```

## Testing Strategy

### What We Test

1. **API Client (`api/bookclub_api.py`)**
   - All CRUD operations for servers, clubs, members, sessions
   - Error handling (404, 400, 401, 500)
   - Request/response formatting
   - Custom exception types

2. **Commands (`cogs/*.py`)**
   - Command registration
   - Interaction handling
   - Response formatting (embeds)
   - Error cases (no guild, no session, etc.)

3. **Event Handlers (`events/message_handler.py`)**
   - Message processing
   - Bot mention responses
   - Keyword detection
   - Member join events

4. **Scheduled Tasks (`utils/schedulers.py`)**
   - Time-based triggering (5PM Pacific)
   - Probability checks (40% chance)
   - Missing channel handling

5. **Services**
   - OpenAI API calls and responses
   - Weather API calls and formatting
   - Retry logic and error handling

6. **Utilities**
   - Embed creation
   - Configuration loading
   - Constants and helpers

### What We Don't Test

1. **Entry Points** - `main.py` is just `bot.run()`, not worth testing
2. **Bot Initialization** - `bot.py` Discord initialization is complex and fragile
3. **Integration Tests** - We don't test actual Discord connections
4. **Database Schema** - We test the API client, not Supabase itself

### Mock vs Real

**We MOCK:**
- ✅ Discord interactions (commands, messages, events)
- ✅ HTTP requests (requests.get, requests.post, etc.)
- ✅ External APIs (OpenAI, Weather, Supabase)
- ✅ Time/randomness (datetime, random)
- ✅ File I/O operations

**We DON'T MOCK:**
- ❌ Pure functions (embed creation, data formatting)
- ❌ Configuration parsing
- ❌ Constants

### Test Coverage Philosophy

**We aim for:**
- **Business logic**: 80%+ coverage
- **API clients**: 75%+ coverage
- **Event handlers**: 100% coverage
- **Utilities**: 90%+ coverage

**We don't aim for:**
- 100% coverage on everything (diminishing returns)
- Testing framework code or external libraries
- Testing trivial getters/setters

## Troubleshooting

### Common Issues

**"coroutine was never awaited" warning**
- **Problem**: Test method is `async` but class doesn't inherit from `IsolatedAsyncioTestCase`
- **Solution**: Change `unittest.TestCase` to `unittest.IsolatedAsyncioTestCase`

**Mock not being called**
- **Problem**: Using `MagicMock` for async methods
- **Solution**: Use `AsyncMock` for any async method

**Random test failures**
- **Problem**: Tests depend on randomness or time
- **Solution**: Use `patch('random.random')` or `patch('datetime.now')`

**Import errors in tests**
- **Problem**: Python path not set correctly
- **Solution**: Run tests with `python -m unittest` or use `tests/run_tests.py`

### Debugging Tests

**Run specific failing test:**
```bash
python -m unittest tests.test_module.TestClass.test_method -v
```

**Add print statements:**
```python
def test_something(self):
    print(f"Debug: {some_variable}")
    result = function()
    print(f"Result: {result}")
```

**Use VS Code debugger:**
1. Set breakpoint in test file
2. Click debug icon next to test name
3. Step through code

## Best Practices

### DO ✅
- Write tests before fixing bugs (TDD for bug fixes)
- Test edge cases (empty input, None, wrong types)
- Use descriptive test names
- Keep tests independent (no shared state)
- Mock external dependencies
- Test error handling

### DON'T ❌
- Make real API calls in tests
- Share state between tests
- Test implementation details
- Write tests that depend on execution order
- Skip tests with `@unittest.skip` (fix them instead!)
- Copy-paste test code (use helper methods)

## Contributing

When adding new code:
1. Write tests for new functionality
2. Ensure tests pass: `make test` (or `python tests/run_tests.py`)
3. Check coverage doesn't decrease: `make coverage` (or `coverage run --source=. tests/run_tests.py && coverage report`)
4. All tests must pass before merging to `main`

## Resources

- [unittest documentation](https://docs.python.org/3/library/unittest.html)
- [unittest.mock documentation](https://docs.python.org/3/library/unittest.mock.html)
- [Coverage.py documentation](https://coverage.readthedocs.io/)
- [Discord.py testing guide](https://discordpy.readthedocs.io/en/stable/ext/test/)

---

**Last Updated**: December 2025
