import aiohttp
import asyncio
import discord
from bs4 import BeautifulSoup as bs
import os
import logging
import sys
from dotenv import load_dotenv

load_dotenv()

# set up client
client = discord.Bot()

# set up logger
logging.basicConfig(
    level=logging.WARNING,
    filename="logs.txt",
    format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("discord").setLevel(logging.CRITICAL)
logging.getLogger().addHandler(
    logging.StreamHandler(sys.stdout)
)  # log to console + file


@client.event
async def on_ready() -> None:
    """
    Set bot status + announce that bot has booted.
    """

    logging.info("LatinBot has booted")

    statuses = (
        "DM me latin!",
        "DM me a word!",
        "Cogito ergo sum!",
        "Carpe diem!",
        "Veni, vidi, vici!",
    )
    while True:
        for status in statuses:
            activity = discord.Game(name=status)
            await client.change_presence(activity=activity)
            await asyncio.sleep(6.5)


@client.event
async def on_message(message: discord.Message) -> discord.Embed:
    """
    Activate when dmed messages.
    """

    # ensure bot doesn't trigger itself
    if message.author == client.user:
        logging.debug("Message detected, but author is the bot")
        return

    # ensure it is a dm message
    if not isinstance(message.channel, discord.channel.DMChannel):
        logging.debug("Message detected, but it is not in a dm channel")
        return

    # make it look like the bot is typing while it gathers responses
    async with message.channel.typing():
        logging.info(
            f'{message.author.name}#{message.author.discriminator} [{message.author.id}] is translating "{message.content}"'
        )
        translations = [
            "\n```" + translation[1:].replace("\n\n*\n", "").replace("\n*", "") + "```"
            for translation in await translate(message.content)
        ]

    nullResponses = (
        "no match",
        "unknown",
        "========",
    )  # things whitikers responses will contain if no translations are found
    for index, translation in enumerate(translations):
        for nullResponse in nullResponses:
            if nullResponse in translation.lower():
                translations[index] = None

    logging.debug(f'Translations fetched: "{translations}"')

    # generate a discord embed with the resulting translations
    response = discord.Embed(
        title=f'Translations for "{message.content}"',
        colour=discord.Colour.dark_green(),
        description="** **",
    )

    # append the translation segments to the embed
    if translations[0] is not None:
        logging.info(f'Latin -> English translations found for "{message.content}"')
        response.add_field(
            name="Latin -> English:",
            value=translations[0].replace(";\n", ";\n\n"),
            inline=False,
        )
    if translations[1] is not None:
        logging.info(f'English -> Latin translations found for "{message.content}"')
        response.add_field(
            name="English -> Latin:", value=translations[1], inline=False
        )

    # if no translations were found add an error message
    if translations.count(None) == len(translations):
        # if non letter characters are found specify such in error
        error = "No Translations found. Ensure you are entering a singular english or latin word consisting only of letters."
        if not message.content.isalpha():
            error += "\nError: non-letter characters found"
        else:
            error += "\nError: word is either in a language other than latin/english, or is gibberish"
        logging.warning(error)

        asyncio.create_task(message.add_reaction("❌"))  # failure; react with red x
        response = discord.Embed(
            title=f'Failed to translate "{message.content}"',
            colour=discord.Colour.dark_red(),
            description=f"```{error}```",
        )
    else:
        logging.debug(
            f"Successfully translated {message.content} and replied to user ({message.author.id})"
        )
        asyncio.create_task(
            message.add_reaction("✅")
        )  # success; react with green check

    # send response
    await message.reply(embed=response)


async def fetch(endpoint: str, session: aiohttp.ClientSession) -> str:
    """
    Fetch html from an endpoint and isolate the contents of the first <pre> tag.

    Args:
        endpoint (str): endpoint to fetch data for
        session (aiohttp.ClientSession): aiohttp client session object

    Returns:
        str: contents between the first <pre> tag
    """

    logging.debug(f"Fetching data from {endpoint}")
    async with session.get(endpoint) as resp:
        resp = await resp.text()
        resp = bs(resp, "html.parser")
        resp = resp.find("pre").contents[0]
        logging.debug(f'Data found for {endpoint}: "{resp}"')
        return resp


async def translate(word: str) -> list:
    """
    Return whitiker words api latin and english translations for a given word

    Args:
        word (str): word to translate from latin to english/vice versa

    Returns:
        list: list in the format [latinTranslations, englishTranslations]
    """

    logging.debug(f'Gathering translations for: "{word}"')
    async with aiohttp.ClientSession() as session:
        output = [
            asyncio.create_task(fetch(endpoint, session))
            for endpoint in (
                f"https://archives.nd.edu/cgi-bin/wordz.pl?keyword={word}",
                f"https://archives.nd.edu/cgi-bin/wordz.pl?english={word}",
            )
        ]
        logging.debug(f'Translations found for {word}: "{output}"')
        output = await asyncio.gather(*output)

    return output


# boot the bot
logging.debug("Bot is booting")
client.run(os.environ.get("TOKEN"))
