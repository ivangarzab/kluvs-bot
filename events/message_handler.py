"""
Handlers for message and member events
"""
import asyncio
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
    async def on_guild_join(guild):
        """Post a welcome embed when the bot joins a new server."""
        print(f"Joined new guild: {guild.name} ({guild.id})")
        channel = guild.system_channel
        if channel is None:
            for c in guild.text_channels:
                if c.permissions_for(guild.me).send_messages:
                    channel = c
                    break
        if channel is None:
            print(f"[WARN] No writable channel found in guild {guild.id}")
            return
        embed = create_embed(
            title="📚 Hi! I'm Kluvs, your book club keeper!",
            description=(
                "I help book clubs manage reading sessions, track members, and keep discussions organized.\n\n"
                "**To get started**, run `!setup` in your book club channel and I'll walk you through everything."
            ),
            color_key="info",
            footer="Run !setup to register your server and create your first book club."
        )
        await channel.send(embed=embed)

    @bot.event
    async def on_member_join(member):
        """Welcome new members."""
        print(f"New member joined: {member.name}")
        channel = None
        try:
            clubs = await asyncio.to_thread(bot.api.get_server_clubs, str(member.guild.id))
            if clubs:
                discord_channel_id = clubs[0].get('discord_channel')
                if discord_channel_id:
                    channel = bot.get_channel(int(discord_channel_id))
        except Exception as e:
            print(f"[ERROR] Failed to fetch clubs for guild {member.guild.id}: {e}")
        if channel:
            greetings = ["Welcome", "Bienvenido", "Willkommen", "Bienvenue", "Bem-vindo", "Welkom", "Καλως"]
            embed = create_embed(
                title="👋 New Member!",
                description=f"{random.choice(greetings)}, {member.mention}!",
                color_key="success",
                footer="Welcome to the Book Club!"
            )
            await channel.send(embed=embed)
