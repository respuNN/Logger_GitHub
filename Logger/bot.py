# Importing modules
import asyncio

# You need to create ".env" file for secure your token then import it
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")


# Import the cogs
from cogs.databases import databases
from cogs.findplayer import findplayer
from cogs.logging_players import logging_players
from cogs.playerlist import playerlist
from cogs.scriptlist import scriptlist


async def setup():
    # Assigning bot.
    bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
    bot.remove_command("help")

    # Add the cogs to the bot (await the add_cog() method calls)
    await bot.add_cog(logging_players(bot))
    await bot.add_cog(databases(bot))
    await bot.add_cog(playerlist(bot))
    await bot.add_cog(scriptlist(bot))
    await bot.add_cog(findplayer(bot))

    # To get a reaction and enter details when the bot is ready
    @bot.event
    async def on_ready():
        # Printing bot's details
        print("Connected to bot: {}".format(bot.user.name))
        print("Bot ID: {}".format(bot.user.id))

    await bot.start(TOKEN)


asyncio.run(setup())
