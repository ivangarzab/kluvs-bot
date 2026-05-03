"""
General commands (help, usage, support, donate, bug, feedback)
"""
import os

import aiohttp
import discord

from utils.embeds import create_embed


class BugReportModal(discord.ui.Modal, title='Report a Bug'):
    issue_title = discord.ui.TextInput(
        label='Issue Title',
        placeholder='Brief description of the bug',
        max_length=100
    )
    steps = discord.ui.TextInput(
        label='Steps to Reproduce / Description',
        style=discord.TextStyle.paragraph,
        placeholder='Describe the bug and steps to reproduce...',
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        embed = create_embed(
            title=f"🐛 Bug Report: {self.issue_title.value}",
            description=self.steps.value,
            color_key="error"
        )
        embed.add_field(
            name="Reported By",
            value=f"{interaction.user.name} (ID: {interaction.user.id})",
            inline=True
        )
        embed.add_field(
            name="Server",
            value=interaction.guild.name if interaction.guild else "DM",
            inline=True
        )

        webhook_url = os.getenv("BUG_WEBHOOK_URL")
        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(webhook_url, session=session)
            await webhook.send(embed=embed, thread_name=self.issue_title.value)

        view = discord.ui.View()
        channel_url = os.getenv("BUG_CHANNEL_URL")
        if channel_url:
            view.add_item(discord.ui.Button(label="Go to #bug-reports", url=channel_url))

        await interaction.response.send_message(
            "✅ Your bug report has been posted! Feel free to follow up in the Community Server.",
            view=view,
            ephemeral=True
        )


class FeedbackModal(discord.ui.Modal, title='Send Feedback'):
    topic = discord.ui.TextInput(
        label='Topic',
        placeholder='What is your feedback about?',
        max_length=100
    )
    feedback = discord.ui.TextInput(
        label='Your Feedback',
        style=discord.TextStyle.paragraph,
        placeholder='Share your thoughts...',
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        embed = create_embed(
            title=f"📫 Feedback: {self.topic.value}",
            description=self.feedback.value,
            color_key="info"
        )
        embed.add_field(
            name="Submitted By",
            value=f"{interaction.user.name} (ID: {interaction.user.id})",
            inline=True
        )
        embed.add_field(
            name="Server",
            value=interaction.guild.name if interaction.guild else "DM",
            inline=True
        )

        webhook_url = os.getenv("FEEDBACK_WEBHOOK_URL")
        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(webhook_url, session=session)
            await webhook.send(embed=embed, thread_name=self.topic.value)

        view = discord.ui.View()
        channel_url = os.getenv("FEEDBACK_CHANNEL_URL")
        if channel_url:
            view.add_item(discord.ui.Button(label="Go to #feedback", url=channel_url))

        await interaction.response.send_message(
            "✅ Your feedback has been posted! Feel free to follow up  in the Community Server.",
            view=view,
            ephemeral=True
        )


def setup_general_commands(bot):
    """
    Setup general commands for the bot

    Args:
        bot: The bot instance
    """
    @bot.tree.command(name="help", description="Show help prompt")
    async def help_command(interaction: discord.Interaction):
        embed = create_embed(
            title="🦉 Quill's Orientation",
            description="Welcome to Kluvs! I'm here to help you with all things about our book club.",
            color_key="info"
        )

        embed.add_field(
            name="👤 New to this server?",
            value="Start with `/join` to join the book club, then check `/session` to see the current book.\n\nUse `/usage` for all available commands.",
            inline=False
        )

        embed.add_field(
            name="👑 Server owner?",
            value="Run `!setup` to initialize your server and create a book club.",
            inline=False
        )

        embed.set_footer(text=f"Happy reading! 📚")
        await interaction.response.send_message(embed=embed)
        print("Sent help command response.")

    @bot.tree.command(name="usage", description="Show all available commands")
    async def usage_command(interaction: discord.Interaction):
        embed = create_embed(
            title="📚 Quill's Commands",
            description="Here are all the commands available to you.",
            color_key="info"
        )

        embed.add_field(
            name="📖 Reading Commands",
            value="• `/session` - Show all session details\n"
                  "• `/book` - Show current book details\n"
                  "• `/duedate` - Show the session's due date\n"
                  "• `/discussions` - Show the session's discussion details\n"
                  "• `/book_summary` - AI-generated book summary",
            inline=False
        )

        embed.add_field(
            name="👥 Member Commands",
            value="• `/join` - Join the book club in the current channel\n"
                  "• `/leave` - Leave the book club in the current channel",
            inline=False
        )

        embed.add_field(
            name="⚙️ Admin Commands",
            value="Admins and server owners: type `!admin_help` for admin commands.",
            inline=False
        )

        embed.set_footer(text=f"Use / for slash commands, ! for admin commands")
        await interaction.response.send_message(embed=embed)
        print("Sent usage command response.")

    @bot.tree.command(name="support", description="Get support for Kluvs")
    async def support_command(interaction: discord.Interaction):
        embed = create_embed(
            title="🤝 Community Support",
            description="Need help? Join our community Discord for support, answers, and updates!",
            color_key="info"
        )
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Join Community", url="https://kluvs.com/discord"))
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @bot.tree.command(name="donate", description="Support the Kluvs project")
    async def donate_command(interaction: discord.Interaction):
        embed = create_embed(
            title="☕ Support Kluvs",
            description="Kluvs is an indie project built with love. Your support helps keep it alive and growing!\n\nEvery contribution, big or small, means the world to us. Thank you! 🙏",
            color_key="royal"
        )
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Buy Me a Coffee", url="https://buymeacoffee.com/kluvs"))
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @bot.tree.command(name="bug", description="Report a bug to the Kluvs team")
    async def bug_command(interaction: discord.Interaction):
        await interaction.response.send_modal(BugReportModal())

    @bot.tree.command(name="feedback", description="Send feedback to the Kluvs team")
    async def feedback_command(interaction: discord.Interaction):
        await interaction.response.send_modal(FeedbackModal())
