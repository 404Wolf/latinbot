import asyncio
import aiohttp
import discord
import json
from bs4 import BeautifulSoup as bs


config = json.load(open("config.json"))
client = discord.Bot()


@client.event
async def on_ready():
    """
    Set bot status + announce that bot has booted.
    """

    game = discord.Game("DM me latin!")
    await client.change_presence(status=discord.Status.online, activity=game)
    print("Bot has booted")


@client.event
async def on_message(message: discord.Message):
    """
    Activate when dmed messages.
    """

    # ensure bot doesn't trigger itself
    if message.author == client.user:
        return

    # ensure it is a dm message
    if not isinstance(message.channel, discord.channel.DMChannel):
        return

    # ensure messages is only letters
    if not message.content.isalpha():
        await message.reply(
            "Please ensure that only letter characters are used in your message."
        )
        return

    translations = [
        "\n```" + translation.replace(";\n", ";\n\n")[1:].replace("\n\n*\n","")+"```"
        for translation in await fetch(message.content)
    ]

    nullResponses = ("no match", "unknown", "========") # things whitikers responses will contain if no translations are found
    for index, translation in enumerate(translations):
        for nullResponse in nullResponses:
            if nullResponse in translation:
                translations[index] = None

    if all([bool(translation) for translation in translations]):
        await message.reply(
            f'No latin or english translations found for "{message.content}"'
        )
        return

    # generate a discord embed with the resulting translations
    response = discord.Embed(
        title=f"Translations for \"{message.content}\"", colour=discord.Colour.blurple(),
        description="** **"
    )

    if translations[0] is not None:
        response.add_field(
            name="Latin -> English:",
            value=translations[0],
            inline=False,
        )

    if translations[1] is not None:
        response.add_field(
            name="English -> Latin:", value=translations[1], inline=False
        )

    await message.reply(embed=response)


async def fetch(word: str) -> list:
    """
    Return whitiker words api latin and english translations for a given word

    Args:
        word (str): word to translate from latin to english/vice versa

    Returns:
        list: list in the format [latinTranslations, englishTranslations]
    """

    output = []
    endpoints = (
        f"https://archives.nd.edu/cgi-bin/wordz.pl?keyword={word}",
        f"https://archives.nd.edu/cgi-bin/wordz.pl?english={word}",
    )

    async def parse(html):
        resp = bs(html, "html.parser")
        resp = resp.find("pre").contents[0]
        return resp

    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints:
            async with session.get(endpoint) as resp:
                output.append(await parse(await resp.text()))

    return output


client.run(config["token"])