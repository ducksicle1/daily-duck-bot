import os
import random
import sqlite3
import asyncio
from datetime import datetime, timedelta, timezone

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands


# ============================================================
# CONFIGURATION
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing from Railway variables.")

DATABASE = "dailyduck.db"
DUCK_FOLDER = "ducks"

DUCK_COLOR = 0xFFDE21


# ============================================================
# DUCK TITLES
# ============================================================

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
            last_title TEXT,
            last_post TEXT
        )
    """)

    connection.commit()
    connection.close()


def get_server(guild_id):

    connection = sqlite3.connect(DATABASE)

    result = connection.execute("""
        SELECT
            guild_id,
            channel_id,
            schedule_type,
            interval_minutes,
            daily_time,
            enabled,
            last_title,
            last_post
        FROM servers
        WHERE guild_id = ?
    """, (guild_id,)).fetchone()

    connection.close()

    return result


def ensure_server(guild_id):

    if get_server(guild_id) is None:

        connection = sqlite3.connect(DATABASE)

        connection.execute("""
            INSERT OR IGNORE INTO servers
            (guild_id, enabled)
            VALUES (?, 0)
        """, (guild_id,))

        connection.commit()
        connection.close()


def save_channel(guild_id, channel_id):

    ensure_server(guild_id)

    connection = sqlite3.connect(DATABASE)

    connection.execute("""
        UPDATE servers
        SET channel_id = ?
        WHERE guild_id = ?
    """, (channel_id, guild_id))

    connection.commit()
    connection.close()


def save_interval(guild_id, minutes):

    ensure_server(guild_id)

    connection = sqlite3.connect(DATABASE)

    connection.execute("""
        UPDATE servers
        SET
            schedule_type = 'interval',
            interval_minutes = ?,
            daily_time = NULL,
            enabled = 1,
            last_post = NULL
        WHERE guild_id = ?
    """, (minutes, guild_id))

    connection.commit()
    connection.close()


def save_daily(guild_id, time_string):

    ensure_server(guild_id)

    connection = sqlite3.connect(DATABASE)

    connection.execute("""
        UPDATE servers
        SET
            schedule_type = 'daily',
            daily_time = ?,
            interval_minutes = NULL,
            enabled = 1,
            last_post = NULL
        WHERE guild_id = ?
    """, (time_string, guild_id))

    connection.commit()
    connection.close()


def disable_autopost(guild_id):

    ensure_server(guild_id)

    connection = sqlite3.connect(DATABASE)

    connection.execute("""
        UPDATE servers
        SET enabled = 0
        WHERE guild_id = ?
    """, (guild_id,))

    connection.commit()
    connection.close()


def save_last_title(guild_id, title):

    connection = sqlite3.connect(DATABASE)

    connection.execute("""
        UPDATE servers
        SET last_title = ?
        WHERE guild_id = ?
    """, (title, guild_id))

    connection.commit()
    connection.close()


def save_last_post(guild_id, timestamp):

    connection = sqlite3.connect(DATABASE)

    connection.execute("""
        UPDATE servers
        SET last_post = ?
        WHERE guild_id = ?
    """, (timestamp.isoformat(), guild_id))

    connection.commit()
    connection.close()


# ============================================================
# BOT
# ============================================================

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# ============================================================
# FIND LOCAL DUCKS
# ============================================================

def get_local_ducks():

    if not os.path.exists(DUCK_FOLDER):
        return []

    allowed_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp"
    }

    ducks = []

    for filename in os.listdir(DUCK_FOLDER):

        extension = os.path.splitext(
            filename
        )[1].lower()

        if extension in allowed_extensions:

            ducks.append(
                os.path.join(
                    DUCK_FOLDER,
                    filename
                )
            )

    return ducks


# ============================================================
# GET RANDOM DUCK
# ============================================================

async def get_random_duck():

    local_ducks = get_local_ducks()

    # 50% chance of choosing from your own
    # collection when local ducks exist.
    if local_ducks and random.choice([True, False]):

        local_file = random.choice(
            local_ducks
        )

        return (
            f"file://{os.path.abspath(local_file)}",
            local_file
        )

    # Otherwise use Random-D.uk.
    try:

        api_url = "https://random-d.uk/api/v2/random"

        async with aiohttp.ClientSession() as session:

            async with session.get(
                api_url,
                timeout=10
            ) as response:

                if response.status != 200:

                    print(
                        f"Random-D.uk returned "
                        f"HTTP {response.status}"
                    )

                else:

                    data = await response.json()

                    image_url = data.get("url")

                    if image_url:
                        return image_url, None

    except Exception as error:

        print(
            f"Random-D.uk error: {error}"
        )

    # If Random-D.uk fails, fall back to your ducks.
    if local_ducks:

        local_file = random.choice(
            local_ducks
        )

        return (
            f"file://{os.path.abspath(local_file)}",
            local_file
        )

    return None, None


# ============================================================
# POST DUCK
# ============================================================

async def post_duck(guild_id):

    server = get_server(guild_id)

    if not server:
        return False

    channel_id = server[1]

    if not channel_id:

        print(
            f"No channel configured for {guild_id}"
        )

        return False

    channel = bot.get_channel(
        channel_id
    )

    if channel is None:

        try:

            channel = await bot.fetch_channel(
                channel_id
            )

        except Exception as error:

            print(
                f"Could not access channel: {error}"
            )

            return False

    image_result = await get_random_duck()

    if not image_result:
        return False

    image_url, local_file = image_result

    previous_title = server[6]

    available_titles = [
        title
        for title in DUCK_TITLES
        if title != previous_title
    ]

    title = random.choice(
        available_titles
    )

    embed = discord.Embed(
        title=title,
        color=DUCK_COLOR
    )

    embed.set_footer(
        text="dailyduck 🦆"
    )

    try:

        if local_file:

            file = discord.File(
                local_file,
                filename=os.path.basename(local_file)
            )

            embed.set_image(
                url=f"attachment://{os.path.basename(local_file)}"
            )

            await channel.send(
                embed=embed,
                file=file
            )

        else:

            embed.set_image(
                url=image_url
            )

            await channel.send(
                embed=embed
            )

        save_last_title(
            guild_id,
            title
        )

        save_last_post(
            guild_id,
            datetime.now(timezone.utc)
        )

        print(
            f"Duck posted successfully! "
            f"Server: {guild_id}"
        )

        return True

    except discord.Forbidden:

        print(
            f"Missing permissions in channel "
            f"{channel_id}"
        )

        return False

    except Exception as error:

        print(
            f"Error posting duck: {error}"
        )

        return False


# ============================================================
# AUTOPOST
# ============================================================

async def autopost_loop():

    await bot.wait_until_ready()

    print(
        "Autopost scheduler started."
    )

    while not bot.is_closed():

        try:

            connection = sqlite3.connect(
                DATABASE
            )

            servers = connection.execute("""
                SELECT
                    guild_id,
                    schedule_type,
                    interval_minutes,
                    daily_time,
                    last_post
                FROM servers
                WHERE enabled = 1
            """).fetchall()

            connection.close()

            now = datetime.now(
                timezone.utc
            )

            for server in servers:

                guild_id = server[0]
                schedule_type = server[1]
                interval_minutes = server[2]
                daily_time = server[3]
                last_post_string = server[4]

                should_post = False

                # INTERVAL
                if schedule_type == "interval":

                    if not interval_minutes:
                        continue

                    if last_post_string is None:

                        should_post = True

                    else:

                        try:

                            last_post = datetime.fromisoformat(
                                last_post_string
                            )

                            elapsed = (
                                now - last_post
                            ).total_seconds() / 60

                            if elapsed >= interval_minutes:
                                should_post = True

                        except ValueError:

                            should_post = True

                # DAILY
                elif schedule_type == "daily":

                    if not daily_time:
                        continue

                    try:

                        hour, minute = map(
                            int,
                            daily_time.split(":")
                        )

                    except ValueError:

                        continue

                    target_time = now.replace(
                        hour=hour,
                        minute=minute,
                        second=0,
                        microsecond=0
                    )

                    if now >= target_time:

                        if last_post_string is None:

                            should_post = True

                        else:

                            try:

                                last_post = datetime.fromisoformat(
                                    last_post_string
                                )

                                if (
                                    last_post.date()
                                    != now.date()
                                ):

                                    should_post = True

                            except ValueError:

                                should_post = True

                if should_post:

                    await post_duck(
                        guild_id
                    )

                    await asyncio.sleep(1)

        except Exception as error:

            print(
                f"Scheduler error: {error}"
            )

        await asyncio.sleep(30)


# ============================================================
# /SETUP
# ============================================================

@bot.tree.command(
    name="setup",
    description="Choose the channel where DailyDuck will post."
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
@app_commands.describe(
    channel="The channel where ducks should appear."
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
async def duck(
    interaction: discord.Interaction
):

    server = get_server(
        interaction.guild.id
    )

    if not server or not server[1]:

        await interaction.response.send_message(
            "🦆 DailyDuck hasn't been set up yet.\n"
            "A server administrator needs to use "
            "`/setup` first.",
            ephemeral=True
        )

        return

    await interaction.response.defer(
        ephemeral=True
    )

    success = await post_duck(
        interaction.guild.id
    )

    if success:

        await interaction.delete_original_response()

    else:

        await interaction.edit_original_response(
            content=(
                "🦆 I couldn't post the duck. "
                "Please check my permissions in "
                "the configured channel."
            )
        )


# ============================================================
# /AUTOPOST
# ============================================================

@bot.tree.command(
    name="autopost",
    description="Configure automatic duck posting."
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
@app_commands.describe(
    mode="Choose interval, daily, or off.",
    amount="Number of minutes or hours.",
    unit="Choose minutes or hours.",
    time="Daily time in 24-hour format, such as 18:30."
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

    server = get_server(
        guild_id
    )

    if not server or not server[1]:

        await interaction.response.send_message(
            "🦆 Please use `/setup` first.",
            ephemeral=True
        )

        return

    if mode.value == "off":

        disable_autopost(
            guild_id
        )

        await interaction.response.send_message(
            "🛑 **DailyDuck autoposting disabled.**",
            ephemeral=True
        )

        return

    if mode.value == "interval":

        if amount is None or unit is None:

            await interaction.response.send_message(
                "Please provide an amount and unit.",
                ephemeral=True
            )

            return

        if amount <= 0:

            await interaction.response.send_message(
                "The amount must be greater than 0.",
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
            f"A duck will be posted every "
            f"**{amount} {unit.value}**.",
            ephemeral=True
        )

        return

    if mode.value == "daily":

        if not time:

            await interaction.response.send_message(
                "Please provide a time in `HH:MM` format.",
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
                "❌ Invalid time. Use `HH:MM`, "
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
            f"A duck will be posted every day at "
            f"**{time} UTC**.",
            ephemeral=True
        )


# ============================================================
# /SETTINGS
# ============================================================

@bot.tree.command(
    name="settings",
    description="View the current DailyDuck configuration."
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def settings(
    interaction: discord.Interaction
):

    server = get_server(
        interaction.guild.id
    )

    if not server or not server[1]:

        await interaction.response.send_message(
            "🦆 DailyDuck hasn't been configured yet.",
            ephemeral=True
        )

        return

    channel = bot.get_channel(
        server[1]
    )

    channel_text = (
        channel.mention
        if channel
        else f"<#{server[1]}>"
    )

    if not server[5]:

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
            f"Daily at {server[4]} UTC"
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
# /HELP
# ============================================================

@bot.tree.command(
    name="help",
    description="Learn how to use DailyDuck."
)
async def help_command(
    interaction: discord.Interaction
):

    embed = discord.Embed(
        title="🦆 DailyDuck",
        description=(
            "Your server's daily dose of duck.\n\n"
            "**Commands**\n"
            "`/duck` — Immediately post a random duck.\n"
            "`/setup` — Choose the duck channel.\n"
            "`/autopost` — Configure automatic posting.\n"
            "`/settings` — View the current configuration."
        ),
        color=DUCK_COLOR
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
@settings.error
async def command_error(
    interaction: discord.Interaction,
    error
):

    if isinstance(
        error,
        app_commands.errors.MissingPermissions
    ):

        message = (
            "🦆 You need the **Manage Server** "
            "permission to use this command."
        )

    else:

        print(
            f"Command error: {error}"
        )

        message = (
            "Something went wrong while processing "
            "that command."
        )

    if interaction.response.is_done():

        await interaction.followup.send(
            message,
            ephemeral=True
        )

    else:

        await interaction.response.send_message(
            message,
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

    if not hasattr(
        bot,
        "scheduler_task"
    ):

        bot.scheduler_task = asyncio.create_task(
            autopost_loop()
        )


# ============================================================
# START
# ============================================================

init_database()

bot.run(TOKEN)
