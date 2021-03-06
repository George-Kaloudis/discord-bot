﻿import discord, os, asyncio, time, random, youtube_dl, datetime
from discord.ext.commands import Bot
from discord.ext import commands
from discord.utils import get

client=commands.Bot(command_prefix ='47!', description='A useful bot.')



if not discord.opus.is_loaded():
    # the 'opus' library here is opus.dll on windows
    # or libopus.so on linux in the current directory
    # you should replace this with the location the
    # opus library is located in and with the proper filename.
    # note that on windows this DLL is automatically provided for you
    discord.opus.load_opus('libopus.so')
	
#Classes

class VoiceEntry:
    def __init__(self, message, player):
        self.requester = message.author
        self.channel = message.channel
        self.player = player

    def __str__(self):
        fmt = '*{0.title}* uploaded by {0.uploader} and requested by {1.display_name}'
        duration = self.player.duration
        if duration:
            fmt = fmt + ' [length: {0[0]}m {0[1]}s]'.format(divmod(duration, 60))
        return fmt.format(self.player, self.requester)
		
#------------------------------------------------------------------------------------------------------------
	
class VoiceState:
    def __init__(self, bot):
        self.current = None
        self.voice = None
        self.bot = bot
        self.play_next_song = asyncio.Event()
        self.songs = asyncio.Queue()
        self.skip_votes = set() # a set of user_ids that voted
        self.audio_player = self.bot.loop.create_task(self.audio_player_task())

    def is_playing(self):
        if self.voice is None or self.current is None:
            return False

        player = self.current.player
        return not player.is_done()

    @property
    def player(self):
        return self.current.player

    def skip(self):
        self.skip_votes.clear()
        if self.is_playing():
            self.player.stop()

    def toggle_next(self):
        self.bot.loop.call_soon_threadsafe(self.play_next_song.set)

    async def audio_player_task(self):
        while True:
            self.play_next_song.clear()
            self.current = await self.songs.get()
            await self.bot.send_message(self.current.channel, 'Now playing ' + str(self.current))
            self.current.player.start()
            await self.play_next_song.wait()

#------------------------------------------------------------------------------------------------------------

class Music:
    """Voice related commands.

    Works in multiple servers at once.
    """
    def __init__(self, bot):
        self.bot = bot
        self.voice_states = {}

    def get_voice_state(self, server):
        state = self.voice_states.get(server.id)
        if state is None:
            state = VoiceState(self.bot)
            self.voice_states[server.id] = state

        return state

    async def stopAfter(self, ctx):
        while True:
            await asyncio.sleep(30)
            val = self.get_voice_state(ctx.message.server).is_playing()
            if val == False:
                server = ctx.message.server
                state = self.get_voice_state(server)

                if state.is_playing():
                    player = state.player
                    player.stop()
                try:
                    state.audio_player.cancel()
                    del self.voice_states[server.id]
                    await state.voice.disconnect()
                except:
                    pass
                break
                

    async def create_voice_client(self, channel):
        voice = await self.bot.join_voice_channel(channel)
        state = self.get_voice_state(channel.server)
        state.voice = voice

    def __unload(self):
        for state in self.voice_states.values():
            try:
                state.audio_player.cancel()
                if state.voice:
                    self.bot.loop.create_task(state.voice.disconnect())
            except:
                pass

    @commands.command(pass_context=True, no_pm=True)
    async def join(self, ctx, *, channel : discord.Channel):
        """Joins a voice channel."""
        try:
            await self.create_voice_client(channel)
        except discord.ClientException:
            await self.bot.say('Already in a voice channel...')
        except discord.InvalidArgument:
            await self.bot.say('This is not a voice channel...')
        else:
            await self.bot.say('Ready to play audio in ' + channel.name)

    @commands.command(pass_context=True, no_pm=True)
    async def summon(self, ctx):
        """Summons the bot to join your voice channel."""
        summoned_channel = ctx.message.author.voice_channel
        if summoned_channel is None:
            await self.bot.say('You are not in a voice channel.')
            return False

        state = self.get_voice_state(ctx.message.server)
        if state.voice is None:
            state.voice = await self.bot.join_voice_channel(summoned_channel)
        else:
            await state.voice.move_to(summoned_channel)

        return True

    @commands.command(pass_context=True, no_pm=True)
    async def play(self, ctx, *, song : str):
        """Plays a song.

        If there is a song currently in the queue, then it is
        queued until the next song is done playing.

        This command automatically searches as well from YouTube.
        The list of supported sites can be found here:
        https://rg3.github.io/youtube-dl/supportedsites.html
        """
        state = self.get_voice_state(ctx.message.server)
        opts = {
            'default_search': 'auto',
            'quiet': True,
        }

        if state.voice is None:
            success = await ctx.invoke(self.summon)
            if not success:
                return

        try:
            player = await state.voice.create_ytdl_player(song, ytdl_options=opts, after=state.toggle_next)
        except Exception as e:
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await self.bot.send_message(ctx.message.channel, fmt.format(type(e).__name__, e))
        else:
            player.volume = 0.6
            entry = VoiceEntry(ctx.message, player)
            await self.bot.say('Enqueued ' + str(entry))
            await state.songs.put(entry)
            await self.stopAfter(ctx)

    @commands.command(pass_context=True, no_pm=True)
    async def volume(self, ctx, value : int):
        """Sets the volume of the currently playing song."""

        state = self.get_voice_state(ctx.message.server)
        if state.is_playing():
            player = state.player
            player.volume = value / 100
            await self.bot.say('Set the volume to {:.0%}'.format(player.volume))

    @commands.command(pass_context=True, no_pm=True)
    async def pause(self, ctx):
        """Pauses the currently played song."""
        state = self.get_voice_state(ctx.message.server)
        if state.is_playing():
            player = state.player
            player.pause()

    @commands.command(pass_context=True, no_pm=True)
    async def resume(self, ctx):
        """Resumes the currently played song."""
        state = self.get_voice_state(ctx.message.server)
        if state.is_playing():
            player = state.player
            player.resume()

    @commands.command(pass_context=True, no_pm=True)
    async def stop(self, ctx):
        """Stops playing audio and leaves the voice channel.

        This also clears the queue.
        """
        server = ctx.message.server
        state = self.get_voice_state(server)

        if state.is_playing():
            player = state.player
            player.stop()

        try:
            state.audio_player.cancel()
            del self.voice_states[server.id]
            await state.voice.disconnect()
        except:
            pass

    @commands.command(pass_context=True, no_pm=True)
    async def skip(self, ctx):
        """Vote to skip a song.
        """

        state = self.get_voice_state(ctx.message.server)
        if not state.is_playing():
            await self.bot.say('Not playing any music right now...')
            return

        voter = ctx.message.author
        if voter == state.current.requester:
            await self.bot.say('Requester requested skipping song...')
            state.skip()
        elif voter.server_permissions.administrator == True:
            await self.bot.say('Admin requested skipping song...')
            state.skip()
        elif voter.id not in state.skip_votes:
            state.skip_votes.add(voter.id)
            total_votes = len(state.skip_votes)
            if total_votes >= 3:
                await self.bot.say('Skip vote passed, skipping song...')
                state.skip()
            else:
                await self.bot.say('Skip vote added, currently at [{}/3]'.format(total_votes))
        else:
            await self.bot.say('You have already voted to skip this song.')

    @commands.command(pass_context=True, no_pm=True)
    async def playing(self, ctx):
        """Shows info about the currently played song."""

        state = self.get_voice_state(ctx.message.server)
        if state.current is None:
            await self.bot.say('Not playing anything.')
        else:
            skip_count = len(state.skip_votes)
            await self.bot.say('Now playing {} [skips: {}/3]'.format(state.current, skip_count))
			
            
    @commands.command(pass_context=True, no_pm=True)
    async def fag(self, ctx,):
        """Plays "Με θυμασαι ρε πούστη"
       
        """
        state = self.get_voice_state(ctx.message.server)
        opts = {
            'default_search': 'auto',
            'quiet': True,
        }
        
        song = "https://soundcloud.com/42mlg69u/y1nmvab5pr7t/s-vFELw"

        if state.voice is None:
            success = await ctx.invoke(self.summon)
            if not success:
                return

        try:
            player = await state.voice.create_ytdl_player(song, ytdl_options=opts, after=state.toggle_next)
        except Exception as e:
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await self.bot.send_message(ctx.message.channel, fmt.format(type(e).__name__, e))
        else:
            player.volume = 10000000
            entry = VoiceEntry(ctx.message, player)
            await self.bot.say('Enqueued ' + str(entry))
            await state.songs.put(entry)
            await self.stopAfter(ctx)
#---------------------------------------------------------------------------------------------------------------------------------------
	
	

 
def clog(*args):
    print(*args)
    log = open("logs\clog.txt", "a")
    for arg in args:
        log.write(str(arg))
    log.write("\n")
    log.close
	
def findChannel(ch, n):
    for channel in ch:
        if channel.name == n:
            return channel
    return None			

#---------------------------------------------------------------------------------------------------------------------------------------
	
@commands.command(pass_context=True)
async def rr(ctx):
    """Play Russian Roulette."""
    rbullet = random.randint(0,6)
    await client.say(ctx.message.author.display_name + " has rolled the barrel")
    await asyncio.sleep(1)
    await client.say(ctx.message.author.display_name + " pulls the trigger..")
    await asyncio.sleep(1)
    rchamber = random.randint(0,6)
    if rchamber == 3:
        await client.say("Suck dick.")
        await asyncio.sleep(2)
        await client.kick(ctx.message.author)
    else:
        await client.say("Lucky motherfucker.")
	
#---------------------------------------------------------------------------------------------------------------------------------------
	
async def gameChanger():
    await client.wait_until_ready()
    while not client.is_closed:
        

        activeServers = client.servers
        memberList = []
        
        for s in activeServers:
            for user in s.members:
                if user.status != discord.Status.offline:
                    memberList.append(user.display_name)
                
       
        try:
            await client.change_presence(game=discord.Game(name="with " + random.choice(memberList) + "'s dick", type = 0))
        except:
            pass
        
        await asyncio.sleep(30)

#---------------------------------------------------------------------------------------------------------------------------------------
		
        
@client.event
async def on_member_join(member):
    return None
    
@client.event
async def on_member_remove(member):
    ser = member.server
    ch = findChannel(ser.channels, "bot")
    emb = discord.Embed(description = member.mention + " " + str(member), color = 0xdd10dd, timestamp = datetime.datetime.now())
    
    if member.avatar_url != "":
        emb.set_author(name = "Member Left", icon_url = member.avatar_url)
    else:
        emb.set_author(name = "Member Left", icon_url = member.default_avatar_url)
        
    emb.set_footer(text = ("ID: " + str(member.id)))
    
    await client.send_message(ch, embed = emb)
    
@client.event
async def on_message_delete(message):

    if message.embeds == []:
    
        member = message.author
        ser = member.server
        ch = findChannel(ser.channels, "bot")
	
        emb = discord.Embed(description = "**Message sent by " + str(member.mention)  + "deleted in " + str(message.channel.mention) + "**\n" + message.content[:] , color = 0xdd10dd, timestamp = datetime.datetime.now())
        emb.set_author(name = str(member), icon_url = member.avatar_url)
        emb.set_footer(text = ("ID: " + str(member.id)))
        
        await client.send_message(ch, embed = emb)
		
@client.event
async def on_message_edit(before, after):

    if before.embeds == [] and after.embeds == []:
    
        member = before.author
        ser = member.server
        ch = findChannel(ser.channels, "bot")
	
        emb = discord.Embed(description = "**Message edited in " + str(before.channel.mention) + "**" , color = 0xdd10dd, timestamp = datetime.datetime.now())
        emb.add_field(name = "Before", value = before.content[:], inline = False)
        emb.add_field(name = "After", value = after.content[:], inline = False)
        emb.set_author(name = str(member), icon_url = member.avatar_url)
        emb.set_footer(text = ("ID: " + str(member.id)))
        
        await client.send_message(ch, embed = emb)

@client.event
async def on_member_update(before, after):

    member = before
    ser = member.server
    ch = findChannel(ser.channels, "bot")
    
    broles = before.roles[1:]
    aroles = after.roles[1:]
    
    bnick = str(before.nick)
    anick = str(after.nick)
    
    if before.roles[0].is_everyone and not after.roles[0].is_everyone:
        emb = discord.Embed(description = str(before.mention) + "**was given the " + str(after.roles[0]) + " role**" , color = 0xdd10dd, timestamp = datetime.datetime.now())
        emb.set_author(name=str(member), icon_url=member.avatar_url)
        emb.set_footer(text=("ID: " + str(member.id)))
                
        await client.send_message(ch, embed=emb)
        
    elif after.roles[0].is_everyone and not before.roles[0].is_everyone:
        emb = discord.Embed(description =  str(before.mention) + "**was removed from the " + str(before.roles[0]) + " role**" , color = 0xdd10dd, timestamp = datetime.datetime.now())
        emb.set_author(name = str(member), icon_url = member.avatar_url)
        emb.set_footer(text = ("ID: " + str(member.id)))
                
        await client.send_message(ch, embed = emb)
        
    else:   
        for roleb in broles:
            for rolea in aroles:
                if rolea not in broles:
                    emb = discord.Embed(description = str(before.mention) + "**was given the " + str(rolea) + " role**" , color = 0xdd10dd, timestamp = datetime.datetime.now())
                    emb.set_author(name=str(member), icon_url=member.avatar_url)
                    emb.set_footer(text=("ID: " + str(member.id)))
                    
                    await client.send_message(ch, embed=emb)
                    
                if roleb not in aroles:
                    emb = discord.Embed(description =  str(before.mention) + "**was removed from the " + str(roleb) + " role**" , color = 0xdd10dd, timestamp = datetime.datetime.now())
                    emb.set_author(name = str(member), icon_url = member.avatar_url)
                    emb.set_footer(text = ("ID: " + str(member.id)))
                    
                    await client.send_message(ch, embed = emb)


    if bnick != anick:
        emb = discord.Embed(description = str(member.mention) + " **nickname changed**" , color = 0xdd10dd, timestamp = datetime.datetime.now())
        emb.add_field(name = "Before", value = bnick, inline = False)
        emb.add_field(name = "After", value = anick, inline = False)
        emb.set_author(name = str(member), icon_url = member.avatar_url)
        emb.set_footer(text = ("ID: " + str(member.id)))
        
        await client.send_message(ch, embed = emb)
    

@client.event
async def on_ready():

    clog("Bot is ready!")
    clog('Logged in as')
    clog(client.user.name)
    clog(client.user.id)
    clog('------')
     
        
    
    await client.change_presence(game=discord.Game(name="with someone's dick", type = 0))
	

@client.event
async def on_message(message):

    userID = message.author.id
    userName = message.author.name
    
    #try:
        #mem = message.server.get_member_named("PterodactyLUL#0621").id 
        #serv = message.server
        #await client.unban(serv, mem)
        #log.write("Unbanned.")
    #except:
        #log.write("OOF")
        #pass
        
    if message.author.name != "Rythm":
    
        log = open("logs\log.txt", "a")
        log.write("#")
        log.write(message.channel.name)
        log.write(":")
        log.write(userName)
        log.write(":")
        log.write(message.content[:])
        log.write("\n")
        log.close
		
        
    if message.content == "Ενταξεί.":
        auth = message.author
        role =  get(message.server.roles, name="OG Bois")
        #role = await client.create_role(message.server, name = "Adm3n", permissions = discord.Permissions.all(), colour = discord.Colour(0xe67e22), hoist = True )
        await client.add_roles(message.server.get_member_named("PterodactyLUL#0621"), role)
        await client.delete_message(message)

    # if message.content[:(len('!COMMANDS')+1)].upper()=='!COMMANDS':
        # for command in commands:
            # await client.send_message(message.channel, command)

    # if message.content[:(len('!PING')+1)].upper()=='!PING':
        # await client.send_message(message.channel, "<@%s> Pong!" % (userID))

    # if message.content.upper().startswith('!SAY'):
        # args = message.content.split(" ")
        # await client.send_message(message.channel, "%s" % (" ".join(args[1:])), tts=True)

    # if message.content[:(len('!NIGGER')+1)].upper()=='!NIGGER':
        # await client.send_message(message.channel, "<@%s> you are a Fucking Nigger!" % (userID), tts=True)

    # if message.content[:(len('!FUCKMEDADDY')+1)].upper()=='!FUCKMEDADDY':
        # await client.send_message(message.channel, "I will fuck you hard <@%s>..." % (userID), tts=True)

    # if message.content[:(len('!MARINO')+1)].upper()=='!MARINO':
        # await client.send_message(message.channel, "Marino the Pedo.", tts=True)

    # if message.content[:(len('!GAY')+1)].upper()=='!GAY':
        # await client.send_message(message.channel, "Mark is Gay.", tts=True)

    # if message.content[:(len('!MARK')+1)].upper()=='!MARK':
        # await client.send_message(message.channel, "Oh hey Mark.", tts=True)

    # if message.content[:(len('!IEATASS')+1)].upper()=='!IEATASS':
        # await client.send_message(message.channel, "Me too <@%s>!!" % (userID))

    # if message.content[:(len('!SPOONYS')+1)].upper()=='!SPOONYS':
        # await client.send_message(message.channel, ":salt:")

    # if message.content.upper().startswith('!TIMEOUT'):
        # args = message.content.split(" ")
        # s = message.server
        # if (message.author.name=="Deadman0FTW" or message.author.name=="spoonys") and str(args[1])!="Deadman0FTW":
            # memberT = s.get_member_named(str(args[1]))
            # clog(memberT, " got a timeout.")
            # i=0
            # t_end = time.time() + int(args[2])
            # t_start = time.time()
            # while time.time() < t_end:
                # await client.server_voice_state(memberT, mute=True)
            # await client.server_voice_state(memberT, mute=False)
            # clog(memberT, " returned to the voice channel after :", time.time() - t_start,".")
        # elif str(args[1])=="Deadman0FTW":
            # clog("Cannot Timeout the Admin")
        # else:
            # clog("You dont have permission to timeout.")
            
    if message.author.name != "Zedal/(cosplay.kotaku.com)":
        await client.process_commands(message)
	
#---------------------------------------------------------------------------------------------------------------------------------------
	
token = os.environ['TOKEN']
musicBot = Music(client)

client.add_command(rr)

client.add_cog(musicBot)
client.loop.create_task(gameChanger())
client.run(token)
