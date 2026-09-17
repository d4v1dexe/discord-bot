import discord
import random
from joke import get_random_joke

joke = joke

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

def witz():

@client.event
async def on_ready():
    await client.user.edit(username='bottiger bot')
    print(f'logged in as{client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$michi')
        #michi ding

@client.event
async def on_message(message):
    if message.author == client.user:
        return 
    if message.content.startswith('$joke'):
        joke = get_random_joke()
        await message.channel.send(f"{joke['setup']}\n||{joke['punchline']}||")            

client.run('REDACTED_TOKEN_WAS_ROTATED') # discord token
