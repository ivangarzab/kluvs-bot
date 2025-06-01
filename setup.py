from setuptools import setup, find_packages

setup(
    name="quill-bot",
    version="0.0.1",
    description="A Discord bot for managing book clubs",
    author="Ivan Garza Bermea",
    author_email="ivangb6@gmail.com",
    packages=find_packages(),
    install_requires=[
        "discord.py",
        "python-dotenv",
        "supabase",
        "pytz",
        "requests",
        "openai",
        "coverage"
    ],
    python_requires=">=3.8",
    entry_points={
        'console_scripts': [
            'quill-bot=main:main',
        ],
    },
)