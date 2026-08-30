import os
import asyncio
import discord
from discord.ext import tasks
import aiohttp

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("DUCK_CHANNEL_ID"))

intents = discord.Intents.default()
client = discord.Client(intents=intents)


async def post_duck():
    channel = client.get_channel(CHANNEL_ID)

    if channel is None:
        print("Could not find the duck channel.")
        return

    api_url = "https://random-d.uk/api/v2/random"

    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as response:
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


async def duck_schedule():
    await client.wait_until_ready()

    while not client.is_closed():
        await post_duck()
        await asyncio.sleep(5 * 60 * 60)


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

    if not hasattr(client, "duck_task"):
        client.duck_task = asyncio.create_task(duck_schedule())


client.run(TOKEN)
