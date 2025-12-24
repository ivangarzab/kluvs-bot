"""
Handlers for message and member events
"""
import random
import discord
from utils.constants import GREETINGS, REACTIONS, GREETING_MESSAGE_PERCENTAGE, REACT_TO_MENTION_PERCENTAGE, REACT_TO_RANDOM_PERCENTAGE
from utils.embeds import create_embed

def setup_message_handlers(bot):
    """Setup message and event handlers for the bot"""
    
    @bot.event
    async def on_message(message):
        """Handle incoming messages."""
        if message.author == bot.user:
            return
            
        print(f"Received message: {message.content}\n\tfrom: {message.author}\n\tin: {message.channel}\n\tat: {message.guild}")
        msg_content = message.content.lower()
        
        # Handle mentions
        if bot.user in message.mentions:
            if random.random() < GREETING_MESSAGE_PERCENTAGE:
                await message.channel.send(random.choice(GREETINGS))
                print("Sent greeting message.")
            elif random.random() > REACT_TO_MENTION_PERCENTAGE:
                await message.add_reaction(random.choice(REACTIONS))
                print("Added reaction to message.")
                
        # Handle keywords
        if 'together' in msg_content:
            await message.channel.send('Reading is done best in community.')
            
        # Random reactions
        if not message.content.startswith('!') and random.random() < REACT_TO_RANDOM_PERCENTAGE:
            await message.add_reaction(random.choice(REACTIONS))
            
        await bot.process_commands(message)

    @bot.event
    async def on_member_join(member):
        """Welcome new members."""
        print(f"New member joined: {member.name}")
        channel = bot.get_channel(bot.config.DEFAULT_CHANNEL)
        if channel:
            greetings = ["Welcome", "Bienvenido", "Willkommen", "Bienvenue", "Bem-vindo", "Welkom", "Καλως"]
            embed = create_embed(
                title="👋 New Member!",
                description=f"{random.choice(greetings)}, {member.mention}!",
                color_key="success",
                footer="Welcome to the Book Club!"
            )
            await channel.send(embed=embed)
        
        # Save new member to the database
        bot.db.save_club({
            "id": 0,  # Assuming club_id is 0
            "name": "Quill's Bookclub",
            "members": [{"id": member.id, "name": member.name, "points": 0, "number_of_books_read": 0}]
        })