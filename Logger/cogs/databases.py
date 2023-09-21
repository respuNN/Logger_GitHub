# Importing modules
import os
import shutil
import sqlite3
from datetime import datetime

from discord.ext import commands


class databases(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Successfully initialized databases cog")
        try:
            self.initialize_players()
            self.initialize_config()
            self.initialize_scripts()
            self.initialize_specialplayers()
        except Exception as e:
            print(f"Couldn't initialize databases: {e}")
        try:
            self.delete_all_data()
        except Exception as e:
            print(f"Couldn't delete all the data from players.db: {e}")

    def initialize_players(self):
        print("Successfully initialized players database")
        # Initialize players.db
        conn = sqlite3.connect("players.db")
        cursor = conn.cursor()

        # Configuration table
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS all_players (
            game_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            discord_id TEXT NOT NULL,
            steam_hex TEXT NOT NULL,
            fivem_id TEXT,
            license_id TEXT,
            license2_id TEXT,
            xbl TEXT,
            live_id TEXT,
            joined_at TEXT NOT NULL,
            left_at TEXT
        )
        """
        )

        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS current_players (
            game_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            discord_id TEXT NOT NULL,
            steam_hex TEXT NOT NULL,
            fivem_id TEXT,
            license_id TEXT,
            license2_id TEXT,
            xbl TEXT,
            live_id TEXT
        )
        """
        )

        # Commit the changes to players.db and close the connection
        conn.commit()
        conn.close()

    def initialize_config(self):
        print("Successfully initialized config database")
        # Initialize config.db
        conn = sqlite3.connect("config.db")
        cursor = conn.cursor()

        # Configuration table
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS details (server_ip TEXT, port INTEGER, channel_id INTEGER)"""
        )

        # Commit the changes to config.db and close the connection
        conn.commit()
        conn.close()

    def initialize_scripts(self):
        print("Successfully initialized scripts database")
        # Initialize scripts.db
        conn = sqlite3.connect("scripts.db")
        cursor = conn.cursor()

        # Create resources table
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS resources (script_name TEXT UNIQUE)"""
        )

        # Commit the changes to scripts.db and close the connection
        conn.commit()
        conn.close()

    def initialize_specialplayers(self):
        print("Successfully initialized specialplayers database")
        # Initialize specialplayers.db
        conn = sqlite3.connect("specialplayers.db")
        cursor = conn.cursor()

        # Create the admin and potential_pd tables
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS admin (user_id INTEGER PRIMARY KEY)"""
        )
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS potential_pd (user_id INTEGER PRIMARY KEY)"""
        )

        # Commit the changes to specialplayers.db and close the connection
        conn.commit()
        conn.close()

    # Deleting all players data when starting bot
    def delete_all_data(self):
        backup_dir = "backups"
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)

        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_name = os.path.join(backup_dir, f"players_backup_{current_time}.db")
        shutil.copy2("players.db", backup_name)

        conn = sqlite3.connect("players.db")
        cursor = conn.cursor()

        # List all tables you want to clear
        tables = ["all_players", "current_players"]

        for table in tables:
            cursor.execute(f"DELETE FROM {table}")

        conn.commit()
        conn.close()


def setup(bot):
    bot.add_cog(databases(bot))
