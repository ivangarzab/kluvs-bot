"""
Member-related commands (join, leave)
"""
import discord
from discord import app_commands

from utils.embeds import create_embed
from api.bookclub_api import ResourceNotFoundError, ValidationError

def setup_member_commands(bot):
    """
    Setup member-related commands for the bot

    Args:
        bot: The bot instance
    """

    @bot.tree.command(name="join", description="Join the book club in this channel")
    @app_commands.guild_only()
    async def join_command(interaction: discord.Interaction):
        """Join the book club linked to the current channel."""
        if not interaction.guild_id:
            await interaction.response.send_message(
                "❌ This command can only be used in a Discord server, not in DMs.",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        guild_id = str(interaction.guild_id)
        channel_id = str(interaction.channel_id)
        discord_id = str(interaction.user.id)

        # Find the club associated with this Discord channel
        club_data = bot.api.find_club_in_channel(channel_id, guild_id)

        if not club_data:
            await interaction.followup.send(
                f"❌ No book club found in this channel. Please ask an admin to link a club here."
            )
            print(f"[ERROR] No club found in channel {channel_id} for guild {guild_id}")
            return

        club_id = club_data['id']
        club_name = club_data['name']

        # Check if the user is already a member
        existing_member = bot.api.get_member_by_discord_id(discord_id)
        if existing_member and club_id in [club['id'] for club in existing_member.get('clubs', [])]:
            await interaction.followup.send(
                f"ℹ️ You're already a member of **{club_name}**!"
            )
            print(f"[INFO] User {discord_id} already a member of club {club_id}")
            return

        # Create or update the member
        member_data = {
            "name": interaction.user.display_name,
            "discord_id": discord_id,
            "handle": interaction.user.name,
            "avatar_url": str(interaction.user.display_avatar.url),
            "clubs": [club_id]
        }

        # If the user is already a member of other clubs, preserve those
        if existing_member:
            existing_clubs = [club['id'] for club in existing_member.get('clubs', [])]
            member_data["clubs"] = list(set(existing_clubs + [club_id]))
            member_id = existing_member['id']
            bot.api.update_member(member_id, member_data)
        else:
            bot.api.create_member(member_data)

        embed = create_embed(
            title="📚 Welcome to the Club!",
            description=f"You've successfully joined **{club_name}**!",
            color_key="success",
            footer="Happy reading! 📖"
        )
        await interaction.followup.send(embed=embed)
        print(f"[SUCCESS] User {discord_id} joined club {club_id} ({club_name})")

    @bot.tree.command(name="leave", description="Leave the book club in this channel")
    @app_commands.guild_only()
    async def leave_command(interaction: discord.Interaction):
        """Leave the book club linked to the current channel."""
        if not interaction.guild_id:
            await interaction.response.send_message(
                "❌ This command can only be used in a Discord server, not in DMs.",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        guild_id = str(interaction.guild_id)
        channel_id = str(interaction.channel_id)
        discord_id = str(interaction.user.id)

        # Find the club associated with this Discord channel
        club_data = bot.api.find_club_in_channel(channel_id, guild_id)

        if not club_data:
            await interaction.followup.send(
                f"❌ No book club found in this channel. Please ask an admin to link a club here."
            )
            print(f"[ERROR] No club found in channel {channel_id} for guild {guild_id}")
            return

        club_id = club_data['id']
        club_name = club_data['name']

        # Get the member by Discord ID
        member = bot.api.get_member_by_discord_id(discord_id)

        if not member:
            await interaction.followup.send(
                f"ℹ️ You're not a member of **{club_name}**."
            )
            print(f"[INFO] User {discord_id} is not a member")
            return

        # Check if the user is in this club
        member_clubs = [club['id'] for club in member.get('clubs', [])]
        if club_id not in member_clubs:
            await interaction.followup.send(
                f"ℹ️ You're not a member of **{club_name}**."
            )
            print(f"[INFO] User {discord_id} is not a member of club {club_id}")
            return

        # Remove the user from the club
        member_id = member['id']
        remaining_clubs = [c for c in member_clubs if c != club_id]

        if remaining_clubs:
            # Update member to remove this club
            bot.api.update_member(member_id, {"clubs": remaining_clubs})
        else:
            # Delete the member entirely if they have no other clubs
            bot.api.delete_member(member_id)

        embed = create_embed(
            title="👋 See You Later!",
            description=f"You've left **{club_name}**.",
            color_key="info",
            footer="We hope to see you again! 📖"
        )
        await interaction.followup.send(embed=embed)
        print(f"[SUCCESS] User {discord_id} left club {club_id} ({club_name})")
