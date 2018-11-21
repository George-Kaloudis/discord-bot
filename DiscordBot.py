import discord
from discord.ext.commands import Bot
from discord.ext import commands
import os
import asyncio
import time


Client = discord.Client()
client= commands.Bot(command_prefix = "!")
commands = ['Commands','Ping','Say','Nigger','Fuckmedaddy','Marino','Gay','Ieatass','Spoonys',  'Timeout','Mark']

def clog(*args):
    print(*args)
    log = open("clog.txt", "a")
    for arg in args:
        log.write(str(arg))
    log.write("\n")
    log.close

@client.event
async def on_ready():
    clog("Bot is ready!")
    clog('Logged in as')
    clog(client.user.name)
    clog(client.user.id)
    clog('------')
    await bot.change_presence(game=discord.Game(name="Test", type=1))

@client.event
async def on_message(message):

    userID = message.author.id
    userName =  message.author.name

    if message.author.name!="Rythm" and message.author.name!="PUBG-Tracker":
        log = open("log.txt", "a")
        log.write("#")
        log.write(message.channel.name)
        log.write(":")
        log.write(userName)
        log.write(":")
        log.write(message.content[:])
        log.write("\n")
        log.close

    if message.content[:(len('!COMMANDS')+1)].upper()=='!COMMANDS':
        for command in commands:
            await client.send_message(message.channel, command)

    if message.content[:(len('!PING')+1)].upper()=='!PING':
        await client.send_message(message.channel, "<@%s> Pong!" % (userID))

    if message.content.upper().startswith('!SAY'):
        args = message.content.split(" ")
        await client.send_message(message.channel, "%s" % (" ".join(args[1:])), tts=True)

    if message.content[:(len('!NIGGER')+1)].upper()=='!NIGGER':
        await client.send_message(message.channel, "<@%s> you are a Fucking Nigger!" % (userID), tts=True)

    if message.content[:(len('!FUCKMEDADDY')+1)].upper()=='!FUCKMEDADDY':
        await client.send_message(message.channel, "I will fuck you hard <@%s>..." % (userID), tts=True)

    if message.content[:(len('!MARINO')+1)].upper()=='!MARINO':
        await client.send_message(message.channel, "Marino the Pedo.", tts=True)

    if message.content[:(len('!GAY')+1)].upper()=='!GAY':
        await client.send_message(message.channel, "Mark is Gay.", tts=True)

    if message.content[:(len('!MARK')+1)].upper()=='!MARK':
        await client.send_message(message.channel, "Oh hey Mark.", tts=True)

    if message.content[:(len('!IEATASS')+1)].upper()=='!IEATASS':
        await client.send_message(message.channel, "Me too <@%s>!!" % (userID))

    if message.content[:(len('!SPOONYS')+1)].upper()=='!SPOONYS':
        await client.send_message(message.channel, ":salt:")

    if message.content.upper().startswith('!TIMEOUT'):
        args = message.content.split(" ")
        s = message.server
        if (message.author.name=="Deadman0FTW" or message.author.name=="spoonys") and str(args[1])!="Deadman0FTW":
            memberT = s.get_member_named(str(args[1]))
            clog(memberT, " got a timeout.")
            i=0
            t_end = time.time() + int(args[2])
            t_start = time.time()
            while time.time() < t_end:
                await client.server_voice_state(memberT, mute=True)
            await client.server_voice_state(memberT, mute=False)
            clog(memberT, " returned to the voice channel after :", time.time() - t_start,".")
        elif str(args[1])=="Deadman0FTW":
            clog("Cannot Timeout the Admin")
        else:
            clog("You dont have permission to timeout.")
token = os.environ['TOKEN']
client.run(token)
