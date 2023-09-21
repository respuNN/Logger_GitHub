# Importing modules
import sqlite3

import discord
import requests
from discord.ext import commands

from cogs.logging_players import fetch_config_from_db


class scriptlist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.scripts_executed = True

    @commands.Cog.listener()
    async def on_ready(self):
        print("Successfully initialized scriptlist cog")

    # You can check the resources with the !scripts command
    @commands.command()
    async def scripts(self, ctx):
        try:
            old_scripts = fetch_scripts_from_db()
            _, serverdata, _ = fetch_config_from_db()

            try:
                response = requests.get(serverdata).json()
            except requests.exceptions.RequestException as e:
                print(e)  # Printing error

            new_scripts = response.get("resources", [])

            added_scripts = list(set(new_scripts) - set(old_scripts))
            deleted_scripts = list(set(old_scripts) - set(new_scripts))

            conn = sqlite3.connect("scripts.db")
            cursor = conn.cursor()

            if self.scripts_executed:
                # Add newly added scripts to the database
                for script in added_scripts:
                    cursor.execute(
                        "INSERT OR IGNORE INTO resources (script_name) VALUES (?)",
                        (script,),
                    )

                # Delete scripts that no longer exist from the database
                for script in deleted_scripts:
                    cursor.execute(
                        "DELETE FROM resources WHERE script_name = ?", (script,)
                    )

                conn.commit()
                self.scripts_executed = False
                added_scripts = list(set(new_scripts) - set(old_scripts))
                deleted_scripts = list(set(old_scripts) - set(new_scripts))

            # Add newly added scripts to the database
            for script in added_scripts:
                cursor.execute(
                    "INSERT OR IGNORE INTO resources (script_name) VALUES (?)",
                    (script,),
                )

            # Delete scripts that no longer exist from the database
            for script in deleted_scripts:
                cursor.execute("DELETE FROM resources WHERE script_name = ?", (script,))

            conn.commit()
            conn.close()

            added_scripts_string = "\n".join(added_scripts) if added_scripts else "None"
            deleted_scripts_string = (
                "\n".join(deleted_scripts) if deleted_scripts else "None"
            )

            embed = discord.Embed(color=discord.Color.from_rgb(204, 255, 204))
            if added_scripts or deleted_scripts:
                embed.add_field(
                    name="Added script(s):", value=added_scripts_string, inline=False
                )
                embed.add_field(
                    name="Deleted script(s):",
                    value=deleted_scripts_string,
                    inline=False,
                )
                embed.set_footer(text=f"Total number of script(s): {len(new_scripts)}")
            else:
                embed.add_field(
                    name=f"There are no scripts added or deleted.", value=""
                )
                embed.set_footer(text=f"Total number of script(s): {len(new_scripts)}")
            await ctx.send(embed=embed)
        except Exception as e:
            print(f"An error occurred: {e}")


# Function to fetch all the scripts from the database
def fetch_scripts_from_db():
    conn = sqlite3.connect("scripts.db")
    cursor = conn.cursor()

    cursor.execute("SELECT script_name FROM resources")
    scripts = [row[0] for row in cursor.fetchall()]

    conn.close()

    return scripts


def setup(bot):
    bot.add_cog(scriptlist(bot))
