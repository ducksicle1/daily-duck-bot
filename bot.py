import os
import asyncio
import random
import sqlite3
from datetime import datetime, timedelta, timezone

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks


# ============================================================
# SETTINGS
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing.")

DATABASE = "dailyduck.db"

DUCK_COLOR = 0xFFDE21

DUCK_TITLES = [
    "A Duck Has Appeared!",
    "A Duck Has Been Spotted!",
    "A Duck Is Here!",
    "The Duck Is Here!",
    "The Duck Has Arrived!",
    "Duck Incoming!",
    "Duck Detected!",
    "Duck Spotted!",
    "Duck Alert!",
    "Behold: A Duck",
    "Lo and Behold, Duck",
    "Oh Look, A Duck",
    "Look Who's Here: A Duck",
    "Guess Who Arrived?",
    "Well, Well, Well… A Duck",
    "Everyone, Remain Calm.",
    "Attention: There Is a Duck",
    "Attention! Duck!",
    "We Have Duck",
    "We Got Duck",
    "Duck Has Entered the Premises",
    "The Daily Duck Has Landed",
    "Your Duck Has Arrived",
    "Your Duck Delivery Is Here",
    "The Duck Has Been Delivered",
    "A Duck Has Entered the Chat!",
    "A Duck Has Been Deployed!",
    "A Duck Has Been Released!",
    "A Duck Has Spawned!",
    "A Duck Has Materialized!",
    "A Duck Has Manifested!",
    "A Duck Has Emerged!",
    "A Duck Has Landed!",
    "A Duck Has Arrived Safely!",
    "A Duck Is Approaching!",
    "Duck Approaching!",
    "Duck En Route!",
    "Duck Incoming, Brace Yourselves!",
    "Duck Has Been Detected!",
    "Duck Successfully Located!",
    "Duck Successfully Acquired!",
    "Duck Has Been Secured!",
    "Duck Has Been Obtained!",
    "Duck Has Been Dispatched!",
    "Duck Has Been Deployed!",
    "Duck Has Entered the Building!",
    "Duck Has Entered the Premises!",
    "There Is Now a Duck.",
    "There Is a Duck Here.",
    "There Appears to Be a Duck.",
    "We Have a Duck Situation.",
    "We Have Located the Duck.",
    "We Have Acquired a Duck.",
    "We Have Obtained Duck.",
    "Duck Has Been Delivered.",
    "Duck Delivery Complete!",
    "Your Duck Is Ready.",
    "Your Duck Has Arrived Safely.",
    "Today's Duck Has Arrived!",
    "Today's Duck Has Been Selected!",
    "Today's Duck Has Been Chosen.",
    "Today's Duck Has Been Located.",
    "Today's Duck Is Here.",
    "Please Welcome Today's Duck.",
    "Please Welcome: Duck.",
    "Introducing: A Duck.",
    "Presenting: A Duck.",
    "Now Presenting… Duck.",
    "May I Present: A Duck.",
    "Behold, Today's Duck.",
    "And Now… A Duck.",
    "Without Further Ado: Duck.",
    "As Promised: Duck.",
    "As Scheduled: Duck.",
    "The Duckening Continues.",
    "Another Duck Has Appeared.",
    "Yet Another Duck.",
    "Once Again: Duck.",
    "It Is Time for Duck.",
    "It Is Duck Time.",
    "Duck Time Has Arrived.",
    "The Hour of Duck Is Upon Us.",
    "The Duck Has Spoken.",
    "The Duck Demands Your Attention.",
    "The Duck Requires Your Attention.",
    "Please Direct Your Attention to the Duck.",
    "Kindly Observe the Duck.",
    "Please Observe: Duck.",
    "Everyone Look at This Duck."
]


# ============================================================
# DATABASE
# ============================================================

def init_database():
    connection = sqlite3.connect(DATABASE)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS servers (
            guild_id INTEGER PRIMARY KEY,
            channel_id INTEGER,
            schedule_type TEXT,
            interval_minutes INTEGER,
            daily_time TEXT,
            enabled INTEGER DEFAULT 0,
            last_title TEXT
        )
    """)

    connection.commit()
    connection.close()


def get_server(guild_id):
    connection = sqlite3.connect(DATABASE)

    cursor = connection.execute(
        "SELECT * FROM servers WHERE guild_id = ?",
        (guild_id,)
    )

    result = cursor.fetchone()

    connection.close()

    return result


def save_channel(guild_id, channel_id):
    connection = sqlite3.connect(DATABASE)

    connection.execute("""
        INSERT INTO servers (guild_id, channel_id, enabled)
        VALUES (?, ?, 0)
        ON CONFLICT(guild_id)
        DO UPDATE SET channel_id = excluded.channel_id
    """, (guild_id, channel_id))

    connection.commit()
    connection.close()


def save_interval(guild_id, minutes):
    connection = sqlite3.connect(DATABASE)

    connection.execute("""
        INSERT INTO servers
        (guild_id, schedule_type, interval_minutes, enabled)
        VALUES (?, 'interval', ?, 1)

        ON CONFLICT(guild_id)
        DO UPDATE SET
            schedule_type = 'interval',
            interval_minutes = excluded.interval_minutes,
            enabled = 1
    """, (guild_id, minutes))

    connection.commit()
    connection.close()


def save_daily(guild_id, time_string):
    connection = sqlite3.connect(DATABASE)

    connection.execute("""
        INSERT INTO servers
        (guild_id, schedule_type, daily_time, enabled)
        VALUES (?, 'daily', ?, 1)

        ON CONFLICT(guild_id)
        DO UPDATE SET
            schedule_type = 'daily',
            daily_time = excluded.daily_time,
            enabled = 1
    """, (guild_id, time_string))

    connection.commit()
    connection.close()


def disable_autopost(guild_id):
    connection = sqlite3.connect(DATABASE)

    connection.execute(
        "UPDATE servers SET enabled = 0 WHERE guild_id = ?",
        (guild_id,)
    )

    connection.commit()
    connection.close()


def save_last_title(guild_id, title):
    connection = sqlite3.connect(DATABASE)

    connection.execute(
        "UPDATE servers SET last_title = ? WHERE guild_id = ?",
        (title, guild_id)
    )

    connection.commit()
    connection.close()


# ============================================================
# DISCORD BOT
# ============================================================

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# ============================================================
# DUCK POSTING
# ============================================================

async def get_random_duck():
    api_url = "https://random-d.uk/api/v2/random"

    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as response:

            if response.status != 200:
                print(
                    f"Duck API returned status {response.status}"
                )
                return None

            data = await response.json()

    return data["url"]


async def post_duck(guild_id, channel=None):

    server = get_server(guild_id)

    if not server:
        return False

    configured_channel_id = server[1]

    if channel is None:
        channel = bot.get_channel(configured_channel_id)

    if channel is None:
        print(
            f"Could not find channel for server {guild_id}"
        )
        return False

    image_url = await get_random_duck()

    if not image_url:
        return False

    previous_title = server[6]

    available_titles = [
        title
        for title in DUCK_TITLES
        if title != previous_title
    ]

    title = random.choice(available_titles)

    save_last_title(guild_id, title)

    embed = discord.Embed(
        title=title,
        color=DUCK_COLOR
    )

    embed.set_image(url=image_url)
    embed.set_footer(text="dailyduck 🦆")

    try:
        await channel.send(embed=embed)
        print(
            f"Duck posted in {guild_id}: {title}"
        )
        return True

    except discord.Forbidden:
        print(
            f"Missing permission in server {guild_id}"
        )
        return False


# ============================================================
# AUTPOST LOOP
# ============================================================

@tasks.loop(minutes=1)
async def autopost_checker():

    connection = sqlite3.connect(DATABASE)

    servers = connection.execute("""
        SELECT
            guild_id,
            channel_id,
            schedule_type,
            interval_minutes,
            daily_time,
            enabled
        FROM servers
        WHERE enabled = 1
    """).fetchall()

    connection.close()

    now = datetime.now(timezone.utc)

    for server in servers:

        guild_id = server[0]
        schedule_type = server[2]
        interval_minutes = server[3]
        daily_time = server[4]

        # ----------------------------------------------------
        # INTERVAL SCHEDULE
        # ----------------------------------------------------

        if schedule_type == "interval":

            connection = sqlite3.connect(DATABASE)

            row = connection.execute("""
                SELECT last_post
                FROM post_times
                WHERE guild_id = ?
            """, (guild_id,)).fetchone()

            connection.close()

            if row is None:
                should_post = True
            else:
                last_post = datetime.fromisoformat(row[0])

                should_post = (
                    now - last_post
                    >= timedelta(minutes=interval_minutes)
                )

            if should_post:
                success = await post_duck(guild_id)

                if success:
                    record_post_time(guild_id, now)


        # ----------------------------------------------------
        # DAILY SCHEDULE
        # ----------------------------------------------------

        elif schedule_type == "daily":

            try:
                hour, minute = map(
                    int,
                    daily_time.split(":")
                )

            except (ValueError, AttributeError):
                continue

            current_time = now.astimezone().replace(
                second=0,
                microsecond=0
            )

            if (
                current_time.hour == hour
                and current_time.minute == minute
            ):

                connection = sqlite3.connect(DATABASE)

                row = connection.execute("""
                    SELECT last_post
                    FROM post_times
                    WHERE guild_id = ?
                """, (guild_id,)).fetchone()

                connection.close()

                already_posted_today = False

                if row:
                    last_post = datetime.fromisoformat(row[0])

                    if last_post.date() == current_time.date():
                        already_posted_today = True

                if not already_posted_today:
                    success = await post_duck(guild_id)

                    if success:
                        record_post_time(guild_id, now)


# ============================================================
# POST TIME DATABASE
# ============================================================

def init_post_times():

    connection = sqlite3.connect(DATABASE)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS post_times (
            guild_id INTEGER PRIMARY KEY,
            last_post TEXT
        )
    """)

    connection.commit()
    connection.close()


def record_post_time(guild_id, timestamp):

    connection = sqlite3.connect(DATABASE)

    connection.execute("""
        INSERT INTO post_times (guild_id, last_post)
        VALUES (?, ?)

        ON CONFLICT(guild_id)
        DO UPDATE SET last_post = excluded.last_post
    """, (
        guild_id,
        timestamp.isoformat()
    ))

    connection.commit()
    connection.close()


# ============================================================
# /SETUP
# ============================================================

@bot.tree.command(
    name="setup",
    description="Choose which channel DailyDuck should post in."
)
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(
    channel="The channel where ducks should be posted."
)
async def setup(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):

    save_channel(
        interaction.guild.id,
        channel.id
    )

    await interaction.response.send_message(
        f"🦆 **DailyDuck is ready!**\n"
        f"Ducks will be posted in {channel.mention}.",
        ephemeral=True
    )


# ============================================================
# /DUCK
# ============================================================

@bot.tree.command(
    name="duck",
    description="Immediately summon a random duck!"
)
async def duck(interaction: discord.Interaction):

    server = get_server(
        interaction.guild.id
    )

    if not server or not server[1]:

        await interaction.response.send_message(
            "🦆 I don't have a duck channel configured yet!\n"
            "Use `/setup` first.",
            ephemeral=True
        )

        return

    await interaction.response.defer()

    success = await post_duck(
        interaction.guild.id
    )

    if success:
        await interaction.followup.send(
            "🦆 Duck deployed!",
            ephemeral=True
        )

    else:
        await interaction.followup.send(
            "I couldn't post the duck. "
            "Make sure I can view and send messages in "
            "the configured channel.",
            ephemeral=True
        )


# ============================================================
# /AUTOPOST
# ============================================================

@bot.tree.command(
    name="autopost",
    description="Configure automatic duck posting."
)
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(
    mode="Choose interval, daily, or off.",
    amount="How many minutes/hours for interval mode.",
    unit="The interval unit.",
    time="Daily posting time in 24-hour format, e.g. 18:30."
)
@app_commands.choices(
    mode=[
        app_commands.Choice(
            name="Interval",
            value="interval"
        ),
        app_commands.Choice(
            name="Daily",
            value="daily"
        ),
        app_commands.Choice(
            name="Off",
            value="off"
        )
    ],
    unit=[
        app_commands.Choice(
            name="Minutes",
            value="minutes"
        ),
        app_commands.Choice(
            name="Hours",
            value="hours"
        )
    ]
)
async def autopost(
    interaction: discord.Interaction,
    mode: app_commands.Choice[str],
    amount: int | None = None,
    unit: app_commands.Choice[str] | None = None,
    time: str | None = None
):

    guild_id = interaction.guild.id

    server = get_server(guild_id)

    if not server or not server[1]:

        await interaction.response.send_message(
            "🦆 Please use `/setup` first so I know "
            "where to post.",
            ephemeral=True
        )

        return


    # OFF
    if mode.value == "off":

        disable_autopost(guild_id)

        await interaction.response.send_message(
            "🛑 Automatic duck posting has been disabled.",
            ephemeral=True
        )

        return


    # INTERVAL
    if mode.value == "interval":

        if amount is None or unit is None:

            await interaction.response.send_message(
                "Please provide both an amount and a unit.",
                ephemeral=True
            )

            return

        if amount <= 0:

            await interaction.response.send_message(
                "The interval must be greater than 0.",
                ephemeral=True
            )

            return

        if unit.value == "hours":
            minutes = amount * 60
        else:
            minutes = amount

        save_interval(
            guild_id,
            minutes
        )

        await interaction.response.send_message(
            f"🦆 **Autopost enabled!**\n"
            f"I'll post a duck every **{amount} "
            f"{unit.value}**.",
            ephemeral=True
        )

        return


    # DAILY
    if mode.value == "daily":

        if not time:

            await interaction.response.send_message(
                "Please provide a time in 24-hour format, "
                "such as `18:30`.",
                ephemeral=True
            )

            return

        try:

            datetime.strptime(
                time,
                "%H:%M"
            )

        except ValueError:

            await interaction.response.send_message(
                "❌ Invalid time. Please use `HH:MM`, "
                "such as `18:30`.",
                ephemeral=True
            )

            return

        save_daily(
            guild_id,
            time
        )

        await interaction.response.send_message(
            f"🦆 **Daily autopost enabled!**\n"
            f"I'll post a duck every day at **{time}**.",
            ephemeral=True
        )


# ============================================================
# /SETTINGS
# ============================================================

@bot.tree.command(
    name="settings",
    description="View the current DailyDuck settings."
)
async def settings(
    interaction: discord.Interaction
):

    server = get_server(
        interaction.guild.id
    )

    if not server or not server[1]:

        await interaction.response.send_message(
            "🦆 DailyDuck hasn't been configured yet.\n"
            "Use `/setup` to get started.",
            ephemeral=True
        )

        return

    channel = bot.get_channel(server[1])

    channel_text = (
        channel.mention
        if channel
        else "Unknown channel"
    )

    enabled = server[5]

    if not enabled:

        schedule = "Disabled"

    elif server[2] == "interval":

        minutes = server[3]

        if minutes % 60 == 0:
            schedule = (
                f"Every {minutes // 60} hour(s)"
            )
        else:
            schedule = (
                f"Every {minutes} minute(s)"
            )

    elif server[2] == "daily":

        schedule = (
            f"Daily at {server[4]}"
        )

    else:

        schedule = "Not configured"

    embed = discord.Embed(
        title="🦆 DailyDuck Settings",
        color=DUCK_COLOR
    )

    embed.add_field(
        name="Posting Channel",
        value=channel_text,
        inline=False
    )

    embed.add_field(
        name="Autopost",
        value=schedule,
        inline=False
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# ============================================================
# ERROR HANDLING
# ============================================================

@setup.error
@autopost.error
async def permission_error(
    interaction: discord.Interaction,
    error
):

    if isinstance(
        error,
        app_commands.errors.MissingPermissions
    ):

        await interaction.response.send_message(
            "🦆 You need the **Manage Server** "
            "permission to change DailyDuck settings.",
            ephemeral=True
        )

    else:

        print(error)

        if not interaction.response.is_done():

            await interaction.response.send_message(
                "Something went wrong.",
                ephemeral=True
            )


# ============================================================
# STARTUP
# ============================================================

@bot.event
async def on_ready():

    print(
        f"Logged in as {bot.user}"
    )

    try:

        synced = await bot.tree.sync()

        print(
            f"Synced {len(synced)} slash commands."
        )

    except Exception as error:

        print(
            f"Failed to sync commands: {error}"
        )

    if not autopost_checker.is_running():
        autopost_checker.start()


init_database()
init_post_times()

bot.run(TOKEN)
