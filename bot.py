import os
import random
import discord
from discord.ext import tasks

TOKEN = os.environ["DISCORD_TOKEN"]
CHANNEL_ID = int(os.environ["DUCK_CHANNEL_ID"])

intents = discord.Intents.default()
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    duck_loop.start()


@tasks.loop(hours=5)
async def duck_loop():
    channel = client.get_channel(CHANNEL_ID)

    if channel is None:
        print("Could not find the duck channel.")
        return

    duck_urls = [
        "https://random-d.uk/api/v2/img",
    ]

    import aiohttp

    async with aiohttp.ClientSession() as session:
        async with session.get(duck_urls[0]) as response:
            data = await response.json()

    image_url = data["url"]

    embed = discord.Embed()
    embed.set_image(url=image_url)
    embed.set_footer(text="🦆 Daily Duck")

    await channel.send(embed=embed)


client.run(TOKEN)
