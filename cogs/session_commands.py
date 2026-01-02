"""
Session-related commands (book, duedate, session, discussions)
"""
import discord
from discord import app_commands

from utils.embeds import create_embed
from api.bookclub_api import ResourceNotFoundError

def setup_session_commands(bot):
    """
    Setup session-related commands for the bot
    
    Args:
        bot: The bot instance
    """
    async def _get_active_session(interaction):
        """
        Helper function to get active session data
        """
        # Ensure we're in a guild
        if not interaction.guild_id:
            await interaction.followup.send("❌ This command can only be used in a Discord server, not in DMs.")
            return None, None
        
        guild_id = str(interaction.guild_id)
        channel_id = str(interaction.channel_id)
        
        # Find the club associated with this Discord channel
        club_data = bot.api.find_club_in_channel(channel_id, guild_id)
        
        if not club_data:
            print(f"[ERROR] No club found in channel {channel_id} for guild {guild_id}")
            # Raise an exception that the bot's error handler will catch
            raise ResourceNotFoundError(f"No book club found in channel {channel_id}")
        
        # Check if there's an active session
        if not club_data.get('active_session'):
            print(f"[INFO] No active session for club {club_data['name']} in guild {guild_id}")
            # This isn't really an error, so we'll handle it directly with a friendly message
            await interaction.followup.send(
                f"There is no active reading session for **{club_data['name']}** right now."
            )
            return None, None
            
        print(f"[INFO] Found active session for club {club_data['name']} in channel {channel_id}")
        return club_data, club_data['active_session']

    @bot.tree.command(name="book", description="Show current book details")
    async def book_command(interaction: discord.Interaction):
        if not interaction.guild_id:
            await interaction.response.send_message(
                "❌ This command can only be used in a Discord server, not in DMs.", 
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        # Get active session data - let exceptions bubble up to bot's error handler
        club_data, session = await _get_active_session(interaction)
        if not session:  # This handles the "no active session" case gracefully
            return
            
        book = session['book']
        
        embed = create_embed(
            title="📚 Current Book",
            description=f"**{book['title']}**",
            color_key="info",
            fields=[
                {"name": "Author", "value": f"{book['author']}"}
            ],
            footer="Happy reading! 📖"
        )
        
        # Add extra book details if available
        if book.get('year'):
            embed.add_field(name="Year", value=str(book['year']), inline=True)
        if book.get('edition'):
            embed.add_field(name="Edition", value=book['edition'], inline=True)
            
        await interaction.followup.send(embed=embed)
        print(f"[SUCCESS] Sent book command response: [Server: {club_data['server_id']}, Club: {club_data['id']}]")

    @bot.tree.command(name="duedate", description="Show the session's due date")
    async def duedate_command(interaction: discord.Interaction):
        if not interaction.guild_id:
            await interaction.response.send_message(
                "❌ This command can only be used in a Discord server, not in DMs.", 
                ephemeral=True
            )
            return
        await interaction.response.defer()
        
        # Get active session data
        club_data, session = await _get_active_session(interaction)
        if not session:
            return
            
        due_date = session['due_date']
        
        embed = create_embed(
            title="📅 Due Date",
            description=f"Session due date: **{due_date}**",
            color_key="warning"
        )
        await interaction.followup.send(embed=embed)
        print(f"[SUCCESS] Sent duedate command response: [Server: {club_data['server_id']}, Club: {club_data['id']}]")

    @bot.tree.command(name="session", description="Show current session details")
    async def session_command(interaction: discord.Interaction):
        if not interaction.guild_id:
            await interaction.response.send_message(
                "❌ This command can only be used in a Discord server, not in DMs.", 
                ephemeral=True
            )
            return
        await interaction.response.defer()
        
        # Get active session data
        club_data, session = await _get_active_session(interaction)
        if not session:
            return
            
        book = session['book']
        
        fields = [
            {
                "name": "Book",
                "value": f"{book['title']}",
                "inline": True
            },
            {
                "name": "Author",
                "value": f"{book['author']}",
                "inline": True
            },
            {
                "name": "Due Date",
                "value": f"{session['due_date']}",
                "inline": False
            }
        ]
        
        # Add discussion count if available
        if session.get('discussions') and len(session['discussions']) > 0:
            fields.append({
                "name": "Discussions",
                "value": f"{len(session['discussions'])} scheduled",
                "inline": True
            })
        
        embed = create_embed(
            title="📚 Current Session Details",
            color_key="info",
            fields=fields,
            footer="Keep reading! 📖"
        )
        await interaction.followup.send(embed=embed)
        print(f"[SUCCESS] Sent session command response: [Server: {club_data['server_id']}, Club: {club_data['id']}]")

    @bot.tree.command(name="discussions", description="Show the session's discussion details")
    async def discussions_command(interaction: discord.Interaction):
        if not interaction.guild_id:
            await interaction.response.send_message(
                "❌ This command can only be used in a Discord server, not in DMs.", 
                ephemeral=True
            )
            return
        await interaction.response.defer()
        
        # Get active session data
        club_data, session = await _get_active_session(interaction)
        if not session:
            return
            
        # Check if there are any discussions
        if not session.get('discussions') or len(session['discussions']) == 0:
            await interaction.followup.send("There are no discussions scheduled for this session.")
            return
            
        discussions = session['discussions']
        
        # Sort discussions by date
        discussions.sort(key=lambda x: x['date'])
        
        # Create fields for each discussion
        fields = []
        for i, discussion in enumerate(discussions):
            fields.append({
                "name": f"Discussion {i+1}: {discussion['title']}",
                "value": f"**Date**: {discussion['date']}\n**Location**: {discussion.get('location', 'TBD')}",
                "inline": False
            })
        
        embed = create_embed(
            title="📚 Book Discussion Details",
            color_key="info",
            fields=fields,
            footer="Don't stop reading! 📖"
        )
        await interaction.followup.send(embed=embed)
        print(f"[SUCCESS] Sent discussions command response: [Server: {club_data['server_id']}, Club: {club_data['id']}]")