"""
Constants used throughout the bot
"""
from discord import Color

# Default channel ID
DEFAULT_CHANNEL = 1327357851827572872

# Config variables
SCHEDULED_MESSAGE_HOUR = 17  # Hour to send sceheduled message
SCHEDULED_MESSAGE_PERCENTAGE = 0.25  # Chance to send scheduled messages
GREETING_MESSAGE_PERCENTAGE = 0.4  # Chance to send greeting on mention
REACT_TO_MENTION_PERCENTAGE = 0.5  # Chance to react to messages
REACT_TO_RANDOM_PERCENTAGE = 0.3  # Chance to react to random messages

# Color schemes for different embed types
COLORS = {
    "success": Color.green(),
    "info": Color.blue(),
    "warning": Color.yellow(),
    "error": Color.red(),
    "fun": Color.orange(),
    "purp": Color.purple(),
    "royal": Color.gold(),
    "misc": Color.teal(),
    "blank": Color.dark_grey()
}

# Message templates
GREETINGS = ['I am Quill', '👀', 'Let\'s get reading!']
REACTIONS = ['⚡️', '👽', '🍄', '🌙', '🔥', '👾', '🦉', '🐺', '🍁']

# Fun facts for the funfact command
FUN_FACTS = [
    'Abibliophobia is the fear of running out of reading material.',
    'The Harvard University library has four law books bound in human skin.',
    'The Adventures of Tom Sawyer is the first book written with a typewriter.',
    'The name Wendy was made up for the book Peter Pan.',
    'People in Iceland read more books per capita than any other country.',
    'J.R.R. Tolkien typed the entire Lord of the Rings trilogy with two fingers.',
    'Up to 50 books can be made from 1 tree.',
    'Bibliosmia is the word for loving the smell of old books.'
]

# Fun fact closers
FACT_CLOSERS = [
    'Did you know? 🤓',
    'Riddle me this ❔❓',
    'Knowledge is power! 💡',
    'Now you know ‼️',
    'Food for thought! 🍎',
    'Curiosity never killed the bookworm! 🐛'
]

# Daily reading reminders
READING_REMINDERS = [
    'Try to read a minimum of 10 pages per day!',
    'Have you read today?',
    'How many pages have you read today?',
    'If you read 20 minutes a day, you would have read 1.8 million words in a year.',
    'Have you been reading? I\'m watching 🦉',
    'Books are portals to new worlds—have you stepped through one today? 🌍',
    'A chapter a day keeps the boredom away!',
    'Remember, even one page is progress! 📖',
    'Reading expands your mind. What did you learn today?',
    'Take a moment to escape reality with a book!',
    'A few pages a day builds a lifetime of knowledge.',
    'Consistency is key! 💪 Keep turning those pages.',
    'Your book is waiting for you—don\'t keep it lonely!',
    'Reading is self-care. ☯️ Take some time for yourself today!',
    'Every page you read brings you closer to your goal. 🎯'
]

# Funny error messages with emojis
GENERIC_ERRORS = [
        "📚 Oops! I dropped my books! Give me a moment to pick them up...",
        "🤔 I seem to have lost my page. Can we try that again?",
        "😅 Even book clubs have technical difficulties sometimes!",
        "🙃 The bookmark fell out! Let's try again, shall we?",
        "🦉 Hoot! Something went wrong with my literary wisdom.",
        "📖 I need to re-read that chapter. Can you try again later?"
]
    
# More specific error messages
RESOURCE_NOT_FOUND_MESSAGES = [
    "🔍 I couldn't find that in my library! Does it exist?",
    "📚 That book seems to be checked out from my collection.",
    "🧐 I've searched all the shelves but couldn't find what you're looking for."
]

VALIDATION_MESSAGES = [
    "✏️ There seems to be a typo in your request.",
    "📝 The details don't look quite right. Could you check them?",
    "🔤 I think we're missing some important information here."
]

AUTH_MESSAGES = [
    "🔐 I need proper permission to access that section of the library.",
    "🚫 The library card for that resource has expired.",
    "👮 The librarian says I don't have access to that shelf."
]

CONNECTION_MESSAGES = [
    "📡 I seem to have lost my connection to the book database.",
    "🌐 The library network is down. Can we try again later?",
    "🔌 I got disconnected from the literary mainframe!"
]