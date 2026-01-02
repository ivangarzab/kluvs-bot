"""
Brains commands - AI-powered interactions via kluvs-reader

This module provides commands that leverage the brains service (kluvs-reader SDK)
for intelligent, RAG-powered interactions about books.
"""
import discord
from discord import app_commands

from utils.embeds import create_embed
from api.bookclub_api import ResourceNotFoundError


def setup_brains_commands(bot):
    """
    Setup AI-powered commands using the brains service.

    Args:
        bot: The bot instance with brains_service initialized
    """

    @bot.tree.command(name="ask", description="Ask a question about the current book (AI-powered)")
    @app_commands.describe(question="What would you like to know about the book?")
    async def ask_command(interaction: discord.Interaction, question: str):
        """
        Ask the AI a question about the current book using RAG and Socratic tutoring.

        This command uses the brains service to:
        1. Search for relevant excerpts from the current book
        2. Generate a Socratic response with hints and thought-provoking questions
        3. Cite page numbers from the actual text

        The command requires an active reading session in the current channel.
        """
        # Ensure we're in a guild (not DMs)
        if not interaction.guild_id:
            await interaction.response.send_message(
                "❌ This command can only be used in a Discord server, not in DMs.",
                ephemeral=True
            )
            return

        # Defer response since AI call may take time
        await interaction.response.defer()

        try:
            guild_id = str(interaction.guild_id)
            channel_id = str(interaction.channel_id)

            # Find the club associated with this Discord channel
            club_data = bot.api.find_club_in_channel(channel_id, guild_id)

            if not club_data:
                print(f"[ERROR] No club found in channel {channel_id} for guild {guild_id}")
                raise ResourceNotFoundError(f"No book club found in channel {channel_id}")

            # Check for active session
            if not club_data.get('active_session'):
                print(f"[INFO] No active session for club {club_data['name']} in guild {guild_id}")
                await interaction.followup.send(
                    f"There is no active reading session for **{club_data['name']}** right now. "
                    f"I need an active book to answer questions about!"
                )
                return

            session = club_data['active_session']
            book_title = session['book']['title']
            book_author = session['book']['author']

            print(f"[INFO] Processing /ask for book: '{book_title}' by {book_author}")
            print(f"[INFO] Question: {question}")

            # Call the brains service
            response = await bot.brains_service.ask(question, book_title)

            # Send response in a styled embed
            embed = create_embed(
                title=f"🧠 About '{book_title}'",
                description=response,
                color_key="info",
                footer="Powered by Kluvs Brains"
            )

            await interaction.followup.send(embed=embed)
            print(f"[SUCCESS] Sent /ask response for '{book_title}'")

        except ResourceNotFoundError as e:
            # Let this bubble up to bot's global error handler
            # It will show a user-friendly "book club not found" message
            raise

        except Exception as e:
            # Catch any other errors and show user-friendly message
            print(f"[ERROR] /ask command failed: {str(e)}")
            error_embed = create_embed(
                title="❌ Error",
                description="I encountered an error while processing your question. Please try again later.",
                color_key="error"
            )
            await interaction.followup.send(embed=error_embed)
