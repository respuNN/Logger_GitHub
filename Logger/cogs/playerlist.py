# Importing modules
import asyncio
import sqlite3

import discord
from discord.ext import commands

from cogs.logging_players import fetch_config_from_db

PAGE_LENGTH = 24


class playerlist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Successfully initialized playerlist cog")

        # Check config data
        playerdata, _, channelid = fetch_config_from_db()
        if playerdata is None or channelid is None:
            print("Correct your config file")
            return  # Exit the method without starting the loop

    @commands.command()
    async def players(self, ctx):
        players, admin, potential_pd = fetch_players_from_db()

        if not players:  # If no players are fetched
            await ctx.send(
                embed=discord.Embed(
                    title="Bluesky's Playerlist",
                    description="There are currently 0 players in the server.",
                    color=discord.Color.red(),
                )
            )
            return

        players_embeds = create_embeds(players, admin, potential_pd)

        message = await ctx.send(embed=players_embeds[0])
        if len(players) > PAGE_LENGTH:
            await message.add_reaction("⬅️")
            await message.add_reaction("➡️")

        page_number = 0

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["⬅️", "➡️"]

        while True:
            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add", timeout=60.0, check=check
                )
                if (
                    str(reaction.emoji) == "➡️"
                    and page_number < len(players_embeds) - 1
                ):
                    page_number += 1
                    await message.edit(embed=players_embeds[page_number])
                elif str(reaction.emoji) == "⬅️" and page_number > 0:
                    page_number -= 1
                    await message.edit(embed=players_embeds[page_number])
                await message.remove_reaction(reaction, user)
            except asyncio.TimeoutError:
                await message.clear_reactions()
                break

    @commands.command()
    async def allplayers(self, ctx):
        all_players = fetch_all_players_from_db()

        if not all_players:  # If no players are fetched
            await ctx.send(
                embed=discord.Embed(
                    title="All Players List",
                    description="No players have joined the server yet.",
                    color=discord.Color.red(),
                )
            )
            return

        all_players_embeds = create_all_players_embeds(all_players)

        message = await ctx.send(embed=all_players_embeds[0])
        if len(all_players) > PAGE_LENGTH:
            await message.add_reaction("⬅️")
            await message.add_reaction("➡️")

        page_number = 0

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["⬅️", "➡️"]

        while True:
            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add", timeout=60.0, check=check
                )
                if (
                    str(reaction.emoji) == "➡️"
                    and page_number < len(all_players_embeds) - 1
                ):
                    page_number += 1
                    await message.edit(embed=all_players_embeds[page_number])
                elif str(reaction.emoji) == "⬅️" and page_number > 0:
                    page_number -= 1
                    await message.edit(embed=all_players_embeds[page_number])
                await message.remove_reaction(reaction, user)
            except asyncio.TimeoutError:
                await message.clear_reactions()
                break

    @commands.command()
    @commands.is_owner()  # Ensures only the bot owner can start/stop the log
    async def add_user(
        self, ctx, list_name: str = None, user_id: int = None, name: str = None
    ):
        # Embeds
        embedok = discord.Embed(title="", color=discord.Color.from_rgb(111, 194, 118))
        embednotok = discord.Embed(title="", color=discord.Color.from_rgb(236, 100, 75))

        try:
            try:
                conn = sqlite3.connect("specialplayers.db")
                cursor = conn.cursor()

                # Check table names to avoid SQL injection
                if (list_name == None and user_id == None) or list_name not in [
                    "admin",
                    "potential_pd",
                ]:
                    embednotok.add_field(
                        name=f"Invalid use of command.",
                        value=f"Correct way is `!add_user list_name user_id`.\nList names: admin or potential_pd",
                        inline=True,
                    )
                    await ctx.send(embed=embednotok)
                    return

                # Check if user already exists
                cursor.execute(
                    f"SELECT user_id FROM {list_name} WHERE user_id=?", (user_id,)
                )
                existing_user = cursor.fetchone()

                if existing_user:
                    embednotok.add_field(
                        name=f"Command failed.",
                        value=f"User <@{user_id}> is already in the {list_name} list.",
                        inline=True,
                    )
                    await ctx.send(embed=embednotok)
                    return  # Exit function

                if list_name in ["admin", "potential_pd"]:
                    cursor.execute(
                        f"INSERT OR REPLACE INTO {list_name} (user_id) VALUES(?)",
                        (user_id,),
                    )
                    embedok.add_field(
                        name=f"Successfully added user.",
                        value=f"Added user with <@{user_id}> to {list_name}.",
                        inline=True,
                    )
                    await ctx.send(embed=embedok)

                conn.commit()
                conn.close()

            except sqlite3.Error as e:
                print(f"SQLite error: {e}")
                embednotok.add_field(
                    name=f"Command failed.",
                    value=f"An error occurred. Please try again later.\nCheck console for more details.",
                    inline=True,
                )
                await ctx.send(embed=embednotok)
        except commands.NotOwner:
            embednotok.add_field(
                name=f"Command failed.",
                value=f"You are not authorized to use this command.",
                inline=True,
            )
            await ctx.send(embed=embednotok)

    @commands.command()
    @commands.is_owner()
    async def remove_user(self, ctx, user_id: int = None):
        # Embeds
        embedok = discord.Embed(title="", color=discord.Color.from_rgb(111, 194, 118))
        embednotok = discord.Embed(title="", color=discord.Color.from_rgb(236, 100, 75))

        try:
            try:
                conn = sqlite3.connect("specialplayers.db")
                cursor = conn.cursor()

                if user_id == None:
                    embednotok.add_field(
                        name=f"Command failed.",
                        value=f"Invalid use of command. Correct way is `!remove_user user_id`.",
                        inline=True,
                    )
                    await ctx.send(embed=embednotok)
                    return

                # List of tables to check
                tables = ["admin", "potential_pd"]
                found_and_deleted = False

                for table in tables:
                    cursor.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))

                    if cursor.rowcount > 0:
                        embedok.add_field(
                            name=f"Successfully removed user.",
                            value=f"Removed user with <@{user_id}> from {table}.",
                            inline=True,
                        )
                        await ctx.send(embed=embedok)
                        found_and_deleted = True

                if not found_and_deleted:
                    embednotok.add_field(
                        name=f"Command failed.",
                        value=f"No user with <@{user_id}> found in any list.",
                        inline=True,
                    )
                    await ctx.send(embed=embednotok)

                conn.commit()
                conn.close()

            except sqlite3.Error as e:
                print(f"SQLite error: {e}")
                embednotok.add_field(
                    name=f"Command failed.",
                    value=f"An error occurred. Please try again later.\nCheck console for more details.",
                    inline=True,
                )
                await ctx.send(embed=embednotok)
        except commands.NotOwner:
            embednotok.add_field(
                name=f"Command failed.",
                value=f"You are not authorized to use this command.",
                inline=True,
            )
            await ctx.send(embed=embednotok)

    @commands.command()
    @commands.is_owner()
    async def delete_all(self, ctx, list_name: str = None):
        embednotok = discord.Embed(title="", color=discord.Color.from_rgb(236, 100, 75))
        embedok = discord.Embed(title="", color=discord.Color.from_rgb(111, 194, 118))

        try:
            # Check if the provided table name is valid to avoid SQL injection
            if list_name == None or list_name not in ["admin", "potential_pd"]:
                embednotok.add_field(
                    name=f"Command failed.",
                    value=f"Invalid use of command. Correct way is `!delete_all list_name`.\nList names: admin or potential_pd",
                    inline=True,
                )
                await ctx.send(embed=embednotok)
                return

            try:
                conn = sqlite3.connect("specialplayers.db")
                cursor = conn.cursor()

                # Delete all data from the specified table
                cursor.execute(f"DELETE FROM {list_name}")
                conn.commit()
                conn.close()

                embedok.add_field(
                    name=f"Successfully deleted data.",
                    value=f"All data from the {list_name} list has been deleted.",
                    inline=True,
                )
                await ctx.send(embed=embedok)

            except sqlite3.Error as e:
                print(f"SQLite error: {e}")
                embednotok.add_field(
                    name=f"Command failed.",
                    value=f"An error occurred. Please try again later.",
                    inline=True,
                )
                await ctx.send(embed=embednotok)
        except commands.NotOwner:
            embednotok.add_field(
                name=f"Command failed.",
                value=f"You are not authorized to use this command.",
                inline=True,
            )
            await ctx.send(embed=embednotok)


def create_embeds(players, admin, potential_pd):
    players_embeds = []
    total_players = len(players)
    players_per_page = PAGE_LENGTH

    total_pages = (len(players) + players_per_page - 1) // players_per_page

    for i in range(0, len(players), players_per_page):
        embed = discord.Embed(
            title="Bluesky's Playerlist", color=discord.Color.from_rgb(255, 255, 255)
        )
        page = players[i : i + players_per_page]
        admincount = 0
        potentialpdcount = 0

        for player in page:
            discord_id = int(player["discord_id"])
            player_name = f"{player['name']} - #{player['game_id']}"
            discord_mention = f"<@{discord_id}>"

            if discord_id in admin:
                embed.add_field(
                    name=player_name, value=f"{discord_mention}\nᴀᴅᴍɪɴ", inline=True
                )
                admincount += 1
            elif discord_id in potential_pd:
                embed.add_field(
                    name=player_name,
                    value=f"{discord_mention}\nᴘᴏᴛᴇɴᴛɪᴀʟ ᴘᴅ",
                    inline=True,
                )
                potentialpdcount += 1
            else:
                embed.add_field(name=player_name, value=discord_mention, inline=True)

        align_value = len(page)
        while align_value % 3 != 0:
            embed.add_field(name="\u200b", value="\u200b", inline=True)
            align_value += 1

        current_page = i // players_per_page + 1
        embed.set_footer(
            text=f"Page {current_page}/{total_pages} | Total players: {str(total_players)} | Potential PD count: {str(potentialpdcount)} | There are {str(admincount)} admin(s) on the server!"
        )
        players_embeds.append(embed)

    return players_embeds


# Function to fetch all the players from the database
def fetch_players_from_db():
    conn = sqlite3.connect("specialplayers.db")
    cursor = conn.cursor()

    cursor.execute("SELECT user_id FROM admin")
    admin = {row[0] for row in cursor.fetchall()}

    cursor.execute("SELECT user_id FROM potential_pd")
    potential_pd = {row[0] for row in cursor.fetchall()}

    conn.close()

    conn = sqlite3.connect("players.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM current_players")
    players = [
        {
            "game_id": row[0],
            "name": row[1],
            "discord_id": row[2],
            "steam_hex": row[3],
            "fivem_id": row[4],
            "license_id": row[5],
            "license2_id": row[6],
            "xbl": row[7],
            "live_id": row[8],
        }
        for row in cursor.fetchall()
    ]

    conn.close()

    return players, admin, potential_pd


def create_all_players_embeds(all_players):
    all_players_embeds = []
    total_players = len(all_players)

    for i in range(0, len(all_players), PAGE_LENGTH):
        embed = discord.Embed(
            title="All Players List", color=discord.Color.from_rgb(255, 255, 255)
        )
        page = all_players[i : i + PAGE_LENGTH]

        for player in page:
            embed.add_field(
                name=f"{player['name']} - #{player['game_id']}",
                value=f"Discord: <@{player['discord_id']}>\nJoined: {player['joined_at']}\nLeft: {player['left_at']}",
                inline=True,
            )

        align_value = len(page)
        while align_value % 3 != 0:
            embed.add_field(name="\u200b", value="\u200b", inline=True)
            align_value += 1

        current_page = i // PAGE_LENGTH + 1
        total_pages = (total_players + PAGE_LENGTH - 1) // PAGE_LENGTH
        embed.set_footer(
            text=f"Page {current_page}/{total_pages} | Total players: {str(total_players)}"
        )
        all_players_embeds.append(embed)

    return all_players_embeds


def fetch_all_players_from_db():
    conn = sqlite3.connect("players.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM all_players")
    all_players = [
        {
            "game_id": row[0],
            "name": row[1],
            "discord_id": row[2],
            "joined_at": row[9],
            "left_at": row[10],
        }
        for row in cursor.fetchall()
    ]

    conn.close()

    return all_players


def setup(bot):
    bot.add_cog(playerlist(bot))
