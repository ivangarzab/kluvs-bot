"""
Task scheduling utilities
"""
import random
from datetime import datetime
import pytz
from discord.ext import tasks

from utils.constants import READING_REMINDERS, SCHEDULED_MESSAGE_HOUR, SCHEDULED_MESSAGE_PERCENTAGE
from utils.embeds import create_embed

def setup_scheduled_tasks(bot):
    """Setup all scheduled tasks for the bot"""
    
    @tasks.loop(hours=1)
    async def send_reminder_message():
        """Send daily reading reminders."""
        sf_timezone = pytz.timezone('US/Pacific')
        now_pacific = datetime.now(tz=sf_timezone)
        
        # if it is 5PM Pacific time, send a reminder with a given percentage chance
        if now_pacific.hour == SCHEDULED_MESSAGE_HOUR and random.random() < SCHEDULED_MESSAGE_PERCENTAGE:
            channel = bot.get_channel(bot.config.DEFAULT_CHANNEL)
            if channel:
                embed = create_embed(
                    title="📚 Daily Reading Reminder", 
                    description=random.choice(READING_REMINDERS),
                    color_key="purp"
                )
                await channel.send(embed=embed)
                print("Reminder message sent.")
    
    # Start the scheduled tasks
    send_reminder_message.start()
    
    # Return the task so it can be stopped if needed
    return send_reminder_message