import os
import asyncio
import random
import discord
import aiohttp

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("DUCK_CHANNEL_ID"))

intents = discord.Intents.default()
client = discord.Client(intents=intents)


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


last_title = None


async def post_duck():
    global last_title

    channel = client.get_channel(CHANNEL_ID)

    if channel is None:
        print("Could not find the duck channel.")
        return

    # Get a random duck
    api_url = "https://random-d.uk/api/v2/random"

    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as response:
            if response.status != 200:
                print(f"Duck API returned status {response.status}")
                return

            data = await response.json()

    image_url = data["url"]

    # Pick a title that is different from the previous one
    available_titles = [
        title for title in DUCK_TITLES
        if title != last_title
    ]

    title = random.choice(available_titles)
    last_title = title

    # Create the embed
    embed = discord.Embed(
        title=title,
        color=0xFFDE21
    )

    embed.set_image(url=image_url)
    embed.set_footer(text="dailyduck 🦆")

    await channel.send(embed=embed)

    print(f"Duck posted successfully! Title: {title}")


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
