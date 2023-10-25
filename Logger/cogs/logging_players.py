# Importing modules
import asyncio
import json
import re
import sqlite3
import time
from datetime import datetime, time, timedelta

import discord
import requests
from cogs.databases import *
from discord.ext import commands, tasks


class logging_players(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message_sent = False
        self.old_list_from_outside = []
        self.logging_executed = True
        self.is_running = False

    @commands.Cog.listener()
    async def on_ready(self):
        print("Successfully initialized logging_players cog")

        # Check config data
        playerdata, _, channelid = fetch_config_from_db()
        if playerdata is None or channelid is None:
            print("Correct your config file")
            await self.bot.change_presence(
                status=discord.Status.online,
                activity=discord.Activity(
                    type=discord.ActivityType.watching, name=f"!config file"
                ),
            )
            return  # Exit the method without starting the loop

        # If all checks passed, start the loop
        try:
            self.logging_players_loop.start()
            print("Successfully initialized loop")
        except:
            print("Couldn't initialize loop")

    @tasks.loop(seconds=1)
    async def logging_players_loop(self):
        if self.is_running:
            print("Previous loop iteration still running. Skipping this iteration.")
            return

        self.is_running = True

        try:
            try:
                _, _, channelid = fetch_config_from_db()
                channel = self.bot.get_channel(channelid)
                response = await connecting_json_data(self)

                if response == 1:
                    self.logging_players_loop.cancel()
                    return

                gmt_plus_3_time = datetime.utcnow() + timedelta(hours=3)
                full_date_str = gmt_plus_3_time.strftime("%H:%M:%S - %d/%m/%Y")

                conn = sqlite3.connect("players.db")
                cursor = conn.cursor()

                try:
                    old_list = self.old_list_from_outside
                    new_list = []

                    for player in response:
                        game_id = player["id"]
                        steam_name = player["name"]
                        discord_id = next(
                            (
                                identifier[8:]
                                for identifier in player["identifiers"]
                                if identifier.startswith("discord:")
                            ),
                            None,
                        )
                        steam_hex = next(
                            (
                                identifier[6:]
                                for identifier in player["identifiers"]
                                if identifier.startswith("steam:")
                            ),
                            None,
                        )
                        fivem_id = next(
                            (
                                identifier[6:]
                                for identifier in player["identifiers"]
                                if identifier.startswith("fivem:")
                            ),
                            None,
                        )
                        license_id = next(
                            (
                                identifier[8:]
                                for identifier in player["identifiers"]
                                if identifier.startswith("license:")
                            ),
                            None,
                        )
                        license2_id = next(
                            (
                                identifier[9:]
                                for identifier in player["identifiers"]
                                if identifier.startswith("license2:")
                            ),
                            None,
                        )
                        xbl = next(
                            (
                                identifier[4:]
                                for identifier in player["identifiers"]
                                if identifier.startswith("xbl:")
                            ),
                            None,
                        )
                        live_id = next(
                            (
                                identifier[5:]
                                for identifier in player["identifiers"]
                                if identifier.startswith("live:")
                            ),
                            None,
                        )

                        player_data = {
                            "game_id": game_id,
                            "steam_name": steam_name,
                            "discord_id": discord_id,
                            "steam_hex": steam_hex,
                            "fivem_id": fivem_id,
                            "license_id": license_id,
                            "license2_id": license2_id,
                            "xbl": xbl,
                            "live_id": live_id,
                        }

                        if self.logging_executed:
                            # Insert or update the player into all_players
                            cursor.execute(
                                """
                            INSERT INTO all_players 
                            (game_id, name, discord_id, steam_hex, fivem_id, license_id, license2_id, xbl, live_id, joined_at, left_at) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                                (
                                    game_id,
                                    steam_name,
                                    discord_id,
                                    steam_hex,
                                    fivem_id,
                                    license_id,
                                    license2_id,
                                    xbl,
                                    live_id,
                                    full_date_str,
                                    "Hasn't left yet.",
                                ),
                            )
                            conn.commit()

                            # Insert the player into current_players
                            cursor.execute(
                                """
                            INSERT INTO current_players 
                            (game_id, name, discord_id, steam_hex, fivem_id, license_id, license2_id, xbl, live_id) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                                (
                                    game_id,
                                    steam_name,
                                    discord_id,
                                    steam_hex,
                                    fivem_id,
                                    license_id,
                                    license2_id,
                                    xbl,
                                    live_id,
                                ),
                            )
                            conn.commit()

                        new_list.append(player_data)

                    if not self.logging_executed:
                        old_set = set(player["game_id"] for player in old_list)
                        new_set = set(player["game_id"] for player in new_list)
                        deleted_players = old_set - new_set
                        added_players = new_set - old_set

                        for second_game_id in deleted_players:
                            player_data = next(
                                player
                                for player in old_list
                                if player["game_id"] == second_game_id
                            )

                            await create_and_send_embed(
                                self,
                                channel,
                                f"{player_data['steam_name']} Left the Server",
                                player_data["discord_id"],
                                player_data["steam_hex"],
                                player_data["game_id"],
                                f"Left at {full_date_str}",
                                discord.Color.from_rgb(231, 143, 142),
                            )

                            # Update the all_players with left_at timestamp
                            cursor.execute(
                                "UPDATE all_players SET left_at = ? WHERE game_id = ?",
                                (full_date_str, player_data["game_id"]),
                            )
                            conn.commit()

                            # Remove the player from current_players
                            cursor.execute(
                                "DELETE FROM current_players WHERE game_id = ?",
                                (player_data["game_id"],),
                            )
                            conn.commit()

                        for second_game_id in added_players:
                            player_data = next(
                                player
                                for player in new_list
                                if player["game_id"] == second_game_id
                            )

                            await create_and_send_embed(
                                self,
                                channel,
                                f"{player_data['steam_name']} Joined the Server",
                                player_data["discord_id"],
                                player_data["steam_hex"],
                                player_data["game_id"],
                                f"Joined at {full_date_str}",
                                discord.Color.from_rgb(27, 153, 139),
                            )

                            # Insert or update the player into all_players
                            cursor.execute(
                                """
                            INSERT INTO all_players 
                            (game_id, name, discord_id, steam_hex, fivem_id, license_id, license2_id, xbl, live_id, joined_at, left_at) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                                (
                                    player_data["game_id"],
                                    player_data["steam_name"],
                                    player_data["discord_id"],
                                    player_data["steam_hex"],
                                    player_data["fivem_id"],
                                    player_data["license_id"],
                                    player_data["license2_id"],
                                    player_data["xbl"],
                                    player_data["live_id"],
                                    full_date_str,
                                    "Hasn't left yet.",
                                ),
                            )
                            conn.commit()


                            # Insert the player into current_players
                            cursor.execute(
                                """
                            INSERT INTO current_players 
                            (game_id, name, discord_id, steam_hex, fivem_id, license_id, license2_id, xbl, live_id) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                                (
                                    player_data["game_id"],
                                    player_data["steam_name"],
                                    player_data["discord_id"],
                                    player_data["steam_hex"],
                                    player_data["fivem_id"],
                                    player_data["license_id"],
                                    player_data["license2_id"],
                                    player_data["xbl"],
                                    player_data["live_id"],
                                ),
                            )
                            conn.commit()

                    if self.logging_executed:
                        self.logging_executed = False

                    self.old_list_from_outside = new_list

                    await self.bot.change_presence(
                        status=discord.Status.online,
                        activity=discord.Activity(
                            type=discord.ActivityType.watching,
                            name=f"{len(response)} players",
                        ),
                    )

                except Exception as e:
                    print(f"Database error: {e}")

                finally:
                    conn.close()

            except Exception as e:
                conn.close()
                print(f"Unhandled error in logging_players_loop: {e}")

            finally:
                conn.close()

        finally:
            conn.close()
            self.is_running = False

    @commands.command()
    async def config(
        self, ctx, server_ip: str = None, port: int = None, channel_id: int = None
    ):
        embednotok = discord.Embed(title="", color=discord.Color.from_rgb(236, 100, 75))
        embedok = discord.Embed(title="", color=discord.Color.from_rgb(111, 194, 118))
        embed = discord.Embed(title="", color=discord.Color.from_rgb(250, 237, 227))

        try:
            if server_ip == "view":
                playerdata, _, channelid = fetch_config_from_db()
                if playerdata:
                    match = re.search(r"http://(.*):(.*)/players.json", playerdata)
                    if match:
                        domain_part = match.group(1)
                        port_part = match.group(2)
                        embed.add_field(
                            name=f"Your current configuration:",
                            value=f"Server IP: **{domain_part}**\nServer IP Port: **{port_part}**\nLogging Channel ID: **{channelid}** | <#{channelid}>",
                            inline=True,
                        )
                        await ctx.send(embed=embed)
                        return
                    else:
                        embed.add_field(
                            name=f"Your current configuration:",
                            value=f"Your current configuration is corrupted.",
                            inline=True,
                        )
                        await ctx.send(embed=embed)
                        return
                else:
                    embed.add_field(
                        name=f"Your current configuration:",
                        value=f"You currently do not have any configurations.",
                        inline=True,
                    )
                    await ctx.send(embed=embed)
                    return

            # Check if the provided table name is valid to avoid SQL injection
            if server_ip == None or port == None or channel_id == None:
                embednotok.add_field(
                    name=f"Command failed.",
                    value=f"Invalid use of command. Correct way is `!config server_ip port channel_id`.",
                    inline=True,
                )
                await ctx.send(embed=embednotok)
                return

            data_check_1 = f"http://{server_ip}:{port}/players.json"

            try:
                response = requests.get(data_check_1).json()
                pass
            except requests.exceptions.RequestException as e:
                embednotok.add_field(
                    name=f"Command failed.",
                    value=f"Couldn't connect to the IP.\nCheck your details.\nFor more information check console.",
                    inline=True,
                )
                await ctx.send(embed=embednotok)
                print(e)
                return

            conn = sqlite3.connect("config.db")
            cursor = conn.cursor()

            cursor.execute("DELETE FROM details")
            cursor.execute(
                "INSERT INTO details (server_ip, port, channel_id) VALUES (?, ?, ?)",
                (
                    server_ip,
                    port,
                    channel_id,
                ),
            )

            conn.commit()
            conn.close()

            embedok.add_field(
                name=f"Your current updated.",
                value=f"Configuration updated successfully with:\n\nServer IP: **{server_ip}**\nServer IP Port: **{port}**\nLogging Channel ID: **{channel_id}** | <#{channel_id}>",
                inline=True,
            )
            await ctx.send(embed=embedok)
            try:
                self.logging_players_loop.start()
                print("Successfully initialized loop")
            except:
                print("Couldn't initialize loop")
        except commands.NotOwner:
            embednotok.add_field(
                name=f"Command failed.",
                value=f"You are not authorized to use this command.",
                inline=True,
            )
            await ctx.send(embed=embednotok)


async def create_and_send_embed(
    self, channel, title, discord_id, steam_hex, game_id, footer_text, color
):
    user = await self.bot.fetch_user(discord_id)
    discord_username = user.name
    user_avatar_url = str(user.avatar.url)
    bot_avatar_url = str(self.bot.user.avatar.url)
    discord_link = f"https://discordapp.com/users/{discord_id}"

    steam_decimal = int(steam_hex, 16)
    steam_link = f"https://steamcommunity.com/profiles/{steam_decimal}"

    embed = discord.Embed(title=title, color=color)
    embed.set_author(name=discord_username, icon_url=user_avatar_url)
    embed.set_thumbnail(url=bot_avatar_url)
    embed.add_field(name=f"", value=f"**Ingame ID:** {game_id}", inline=False)
    embed.add_field(
        name=f"", value=f"**Discord ID:** [{discord_id}]({discord_link})", inline=False
    )
    embed.add_field(
        name=f"", value=f"**Steam Hex:** [{steam_hex}]({steam_link})", inline=False
    )
    embed.set_footer(text=footer_text)

    await channel.send(embed=embed)


# Function to fetch config data from the database
def fetch_config_from_db():
    conn = sqlite3.connect("config.db")
    cursor = conn.cursor()

    # Fetch server_ip and channel_id
    cursor.execute(
        "SELECT server_ip, port, channel_id FROM details LIMIT 1"
    )  # Fetch only one record, assuming only one config exists
    details = cursor.fetchone()

    conn.close()

    if details:
        playerdata = f"http://{details[0]}:{details[1]}/players.json"
        serverdata = f"http://{details[0]}:{details[1]}/info.json"
        channelid = details[2]
        return (
            playerdata,
            serverdata,
            channelid,
        )  # return playerdata, serverdata and channelid
    return None, None, None  # Return None if no record found


async def send_embed_json(channel, description, color, full_date_str):
    embed = discord.Embed(title="", color=color)
    embed.add_field(name=description, value=full_date_str, inline=False)
    await channel.send(embed=embed)


async def set_bot_status_json(status, activity_type, name):
    await logging_players.bot.change_presence(
        status=status,
        activity=discord.Activity(type=activity_type, name=name),
    )


async def connecting_json_data(self):
    playerdata, _, channelid = fetch_config_from_db()
    channel = self.bot.get_channel(channelid)

    for _ in range(3):  # Try 3 times to make a request
        try:
            utc_now = datetime.utcnow()
            gmt_plus_3_time = utc_now + timedelta(hours=3)
            full_date_str = gmt_plus_3_time.strftime("%H:%M:%S - %d/%m/%Y")
            current_time = gmt_plus_3_time.time()

            if time(17, 0) <= current_time <= time(17, 4) or time(6, 0) <= current_time <= time(6, 4):
                await send_embed_json(
                    channel,
                    "Server is probably restarting.\nBot will try again in 5 minutes.",
                    discord.Color.from_rgb(139, 139, 174),
                    full_date_str,
                )
                
                await self.bot.change_presence(
                    status=discord.Status.online,
                    activity=discord.Activity(
                        type=discord.ActivityType.watching, name="restart procedure"
                    ),
                )

                databases.delete_all_data(self)
                self.old_list_from_outside = []
                await asyncio.sleep(300)  # Wait for 5 minutes

            response = requests.get(playerdata)
            response.raise_for_status()  # Raise an HTTPError if an error occurs

            json_data = response.json()

            if not self.message_sent:
                await send_embed_json(
                    channel,
                    "Json file reached, logging.",
                    discord.Color.from_rgb(255, 225, 168),
                    full_date_str,
                )
                self.message_sent = True

            return json_data

        except Exception as e:
            print(f"Error in connecting_json_data: {e}")
            await asyncio.sleep(60)  # Wait for 60 seconds

    await send_embed_json(
        channel,
        "Logging player loop aborted.\nBot could not connect json data 3 times.",
        discord.Color.from_rgb(217, 51, 51),
        full_date_str,
    )
    await set_bot_status_json(
        discord.Status.online, discord.ActivityType.watching, "emptiness"
    )

    logging_players.logging_players_loop.cancel()
    return 1


def setup(bot):
    bot.add_cog(logging_players(bot))
