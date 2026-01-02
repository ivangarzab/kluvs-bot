"""
Utility commands (weather, funfact)
"""
import random
import discord
from discord import app_commands

from utils.constants import FUN_FACTS, FACT_CLOSERS
from utils.embeds import create_embed
from services.weather_service import WeatherService

def setup_utility_commands(bot):
    """
    Setup utility commands for the bot
    
    Args:
        bot: The bot instance
    """
    weather_service = WeatherService(bot.config.KEY_WEATHER)
    
    @bot.tree.command(name="weather", description="Get the weather for a specific city")
    @app_commands.describe(location="The city to get weather for")
    async def weather_command(interaction: discord.Interaction, location: str):
        print(f"Weather command received for location: {location}")
        await interaction.response.defer()  # Defer the response since weather API call might take time
        
        weather_info = await weather_service.get_weather(location)
        embed = create_embed(
            title=f"🌤 Weather for {location.title()}",
            description=weather_info,
            color_key="info",
            timestamp=True,
            footer="Weather information last updated"
        )
        
        await interaction.followup.send(embed=embed)
        print("Sent weather command response.")

    @bot.tree.command(name="funfact", description="Get a random book-related fun fact")
    async def funfact_command(interaction: discord.Interaction):
        embed = create_embed(
            title="📚 Book Fun Fact",
            description=random.choice(FUN_FACTS),
            color_key="purp",
            footer=random.choice(FACT_CLOSERS)
        )
        await interaction.response.send_message(embed=embed)
        print("Sent funfact command response.")