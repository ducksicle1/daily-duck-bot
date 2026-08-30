import os
import discord
from discord.ext import tasks
import aiohttp

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("DUCK_CHANNEL_ID"))

intents = discord.Intents.default()
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

    if not duck_loop.is_running():
        duck_loop.start()


@tasks.loop(hours=5)
async def duck_loop():
    channel = client.get_channel(CHANNEL_ID)

    if channel is None:
        print("Could not find the duck channel.")
        return

    url = "https://random-d.uk/api/random"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                print(f"Duck API returned status {response.status}")
                return

            data = await response.json()

    image_url = data["url"]

    embed = discord.Embed()
    embed.set_image(url=image_url)
    embed.set_footer(text="🦆 Daily Duck")

    await channel.send(embed=embed)
    print("Duck posted successfully!")


@duck_loop.before_loop
async def before_duck_loop():
    await client.wait_until_ready()


client.run(TOKEN)

client.run(TOKEN)
