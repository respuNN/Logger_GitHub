# Importing modules
import asyncio
import re
import sqlite3

import discord
from discord.ext import commands


class findplayer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Successfully initialized find cog")

    @commands.command()
    async def find(self, ctx, value):
        # Determine the search type based on input
        if re.match(r"^[1-9]\d{0,2}$", value):  # matches 1-999
            search_type = "game_id"
        elif len(value) == 18 and value.isdigit():
            search_type = "discord_id"
        elif len(value) == 15:
            search_type = "steam_hex"
        else:
            await ctx.send("Invalid input.")
            return

        try:
            conn = sqlite3.connect("players.db")
            cursor = conn.cursor()

            # If the search was by game_id, we need to first fetch the discord_id
            if search_type == "game_id":
                cursor.execute(
                    "SELECT discord_id FROM all_players WHERE game_id=?", (value,)
                )
                discord_id_row = cursor.fetchone()

                if not discord_id_row:
                    await ctx.send(f"No player found with the given {search_type}.")
                    return

                value = discord_id_row[0]
                search_type = "discord_id"

            # Fetch all records for that discord_id
            cursor.execute(
                f"SELECT * FROM all_players WHERE {search_type}=? ORDER BY game_id DESC",
                (value,),
            )
            records = cursor.fetchall()
            conn.close()

            if not records:
                await ctx.send(
                    f"No records found for the user with the given {search_type}."
                )
                return

            index = 0

            message = await ctx.send(
                embed=self.create_player_embed(records[0], index + 1, len(records))
            )

            if len(records) > 1:
                await message.add_reaction("⬅️")
                await message.add_reaction("➡️")

                def check(reaction, user):
                    return user == ctx.author and str(reaction.emoji) in ["⬅️", "➡️"]

                while True:
                    try:
                        reaction, user = await self.bot.wait_for(
                            "reaction_add", timeout=60.0, check=check
                        )
                        if str(reaction.emoji) == "➡️" and index < len(records) - 1:
                            index += 1
                            await message.edit(
                                embed=self.create_player_embed(
                                    records[index], index + 1, len(records)
                                )
                            )
                        elif str(reaction.emoji) == "⬅️" and index > 0:
                            index -= 1
                            await message.edit(
                                embed=self.create_player_embed(
                                    records[index], index + 1, len(records)
                                )
                            )
                        await message.remove_reaction(reaction, user)
                    except asyncio.TimeoutError:
                        await message.clear_reactions()
                        break

        except sqlite3.Error as e:
            await ctx.send(f"Database error: {e}")
        except Exception as e:
            await ctx.send(f"Unexpected error: {e}")

    def create_player_embed(self, player, index, total_pages):
        embed = discord.Embed(
            title=f"{player[1]} - #{player[0]}",
            color=discord.Color.from_rgb(255, 255, 255),
        )
        embed.add_field(
            name="Discord ID",
            value=f"<@{player[2]}>",
            inline=True,
        )
        embed.add_field(
            name="Joined At",
            value=player[9],
            inline=True,
        )
        embed.add_field(
            name="Left At",
            value=player[10],
            inline=True,
        )
        discord_link = f"https://discordapp.com/users/{player[2]}"
        embed.add_field(
            name="",
            value=f"[Discord Profile]({discord_link})",
            inline=False,
        )
        # Convert steam_hex to decimal and generate the link
        steam_decimal = int(player[3], 16)  # Convert hex to decimal
        steam_link = f"https://steamcommunity.com/profiles/{steam_decimal}"
        embed.add_field(
            name="",
            value=f"[Steam Profile]({steam_link})",
            inline=False,
        )
        if total_pages > 1:
            embed.set_footer(text=f"Page {index}/{total_pages}")
        return embed


def setup(bot):
    bot.add_cog(findplayer(bot))
