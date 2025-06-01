"""
Admin commands (verison)
"""
import re
import os
import discord
from discord.ext import commands

from utils.embeds import create_embed

def setup_admin_commands(bot):
    """
    Setup admin (prefix) commands

    Args:
        bot: The bot instance
    """
    @bot.command(name="version", help="Shows the current version of the bot")
    async def version(ctx: commands.Context):
        """
        Extracts and displays the current version from setup.py
        Usage: !version
        """
        try:
            # Find setup.py in the project root directory
            setup_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "setup.py")

            # Read the setup.py file
            with open(setup_path, "r") as file:
                setup_content = file.read()
            
            # Extract version using regex
            version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', setup_content)
            
            if version_match:
                version = version_match.group(1)
                
                # Create and send a pretty embed
                embed = create_embed(
                    title=f"📚 Quill Bot version: v{version}",
                    color_key="blank",
                    timestamp=True
                )
                await ctx.send(embed=embed)
            else:
                # Send error embed if version not found
                embed = create_embed(
                    title="❌ Error",
                    description="Couldn't find version information in setup.py",
                    color_key="error"
                )
                await ctx.send(embed=embed)
        except Exception as e:
            # Send error embed for any exceptions
            embed = create_embed(
                title="❌ Error",
                description=f"Error retrieving version: {str(e)}",
                color_key="error"
            )
            await ctx.send(embed=embed)