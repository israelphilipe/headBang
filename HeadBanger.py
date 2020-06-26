import random
import asyncio
import youtube_dl
import json
import os
import time
from discord.ext import commands
from discord import VoiceChannel
import shutil
import discord
from discord.errors import ClientException
from discord.ext.commands.errors import CommandNotFound
import os



client = commands.Bot(command_prefix='$')

TOKEN = os.environ['TOKEN']

queue_path = os.path.abspath(os.path.realpath("Queues"))

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        data['file_path'] = filename
        return data


enter_chat_quotes = [
    'Ready to play some bangers',
    'Im here chief',
    'Go on, tell me what to play',
    'Lets rock',
    'I´m feeling today is a good music day',
    'Ready to play'
]

queues = {

}

is_looping = False

ffmpeg_options = {
    'options': '-vn',
}
current = 0

ytdl = None
ytdl_format_options = None


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))



@client.command(pass_context=True)
async def ping(ctx):
    await ctx.send('latency : '+str(round(client.latency*1000))+'ms')


@client.command(pass_context=True)
async def join(ctx, flag=0):
    if ctx.message.author.voice is None or ctx.message.author.voice.channel is None:
        await ctx.message.channel.send('You are not in a voice server')
        return
    channel = ctx.message.author.voice.channel
    await VoiceChannel.connect(channel)
    if flag == 0:
        await ctx.message.channel.send(enter_chat_quotes[random.randint(0, len(enter_chat_quotes))-1])
    global ytdl_format_options
    ytdl_format_options = {
        'format': 'bestaudio/best',
        'outtmpl': f'./Queues/{ctx.message.guild.id}/-%(id)s.mp3',
        'quiet': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192'
        }],
        'default_search': 'auto',
    }
    global ytdl
    ytdl = youtube_dl.YoutubeDL(ytdl_format_options)
    return


@client.command(pass_context=True)
async def leave(ctx):
    server = ctx.message.guild.voice_client
    if not server:
        await ctx.message.channel.send("Not in a voice channel")
    await stop(ctx)
    await server.disconnect()


async def queue(ctx, url: str):
    song = await YTDLSource.from_url(url, loop=client.loop)
    await ctx.message.channel.send(f"Song {song['title']} added to the queue")
    if len(queues) >= 50:
        await ctx.message.channel.send('Queue is full, please remove an item')
        return
    queues[len(queues)+1] = song


@client.command(pass_context=True, aliases=['queue'])
async def show_queue(ctx):
    global current
    global is_looping

    if len(queues) == 0:
        return await ctx.message.channel.send(f"```CSS\n[Queue is empty]\n```")
    q = "```CSS\n"
    for i in range(1, len(queues)+1):
        if i == current:
            q += '->'
        q += f"{i} : {queues[i]['title']}\n"
    if is_looping:
        q += "[Queue in Loop]"
    q += "```"
    await ctx.message.channel.send(q)


@client.command(pass_context=True)
async def play(ctx, *args):
    if len(args) == 0:
        await ctx.message.channel.send('No music given.Type $play + name of the music to play')
        return
    if not ctx.message.guild.voice_client:
        await join(ctx, 1)
    url = str(args)
    await queue(ctx, url)
    if len(queues) == 1:
        await next(ctx)


def check_current(voice_client):
    if voice_client.is_playing() or voice_client.is_paused():
        return
    global current
    if is_looping and current == len(queues):
        current = 1
        return
    else:
        current += 1
        return


async def nextSong(ctx=None, flag=0):
    context = None
    if ctx is not None:
        context = ctx
    while True:
        if len(queues) > 0 and context is not None:
            voice_client = context.message.guild.voice_client
            if voice_client.is_playing() and flag == 1:
                voice_client.stop()
            check_current(voice_client)
            if current > len(queues) and not voice_client.is_paused():
                await context.message.channel.send('Done playing')
                await stop(ctx)
            else:
                if not voice_client.is_playing() and not voice_client.is_paused():
                    if queues[current] is not None:
                        song = discord.FFmpegPCMAudio(queues[current]['file_path'], **ffmpeg_options)
                        voice_client.play(song)
                        await context.message.channel.send(f'Playing {queues[current]["title"]}')
        await asyncio.sleep(0.1)
        flag = 0


@client.command(pass_context=True)
async def next(ctx):
    await nextSong(ctx, 1)


@client.command(pass_context=True)
async def loop(ctx):
    global is_looping
    is_looping = not is_looping
    msg = "Started" if is_looping else "Stopped"
    return await ctx.message.channel.send(f'```CSS\n{msg} looping queue\n```')


@client.command(pass_context=True,aliases=['current'])
async def current_in_queue(ctx):
    if len(queues) == 0:
        return await ctx.message.channel.send(f"```CSS\n[Queue is empty]\n```")
    await ctx.message.channel.send('```Current song in queue: {}```'.format(queues[current]['title']))


@client.command(pass_context=True)
async def pause(ctx):

    voice_client = ctx.message.guild.voice_client
    if not voice_client:
        await ctx.message.channel.send("Not in a voice channel")
    if voice_client.is_playing():
        voice_client.pause()
    return


@client.command(pass_context=True)
async def stop(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client:
        voice_client.stop()
    await clear(ctx)
    return


@client.command(pass_context=True)
async def clear(ctx):
    queues.clear()
    await asyncio.sleep(1)
    try:
        shutil.rmtree(queue_path+"/"+str(ctx.guild.id), ignore_errors=True)
        print('Cleared folder')
    except:
        print(queue_path)
    global current
    current = 0
    return


@client.command(pass_context=True)
async def resume(ctx):
    voice_client = ctx.message.guild.voice_client
    if not voice_client:
        await ctx.message.channel.send("Not in a voice channel")
    if voice_client.is_paused():
        voice_client.resume()
    else:
        await ctx.message.channel.send("Nothing playing now")
    return


@client.event
async def on_command_error(ctx, error):
    if isinstance(error, CommandNotFound):
        await ctx.message.channel.send('Sorry, this command does not exist.')
        return
    await stop(ctx)
    raise error

@client.command(pass_context=True)
async def commands(ctx):
    file = open("commands.json")
    commands_json = json.load(file)
    commands = "```css\n"
    for c in commands_json:
        commands += f'-{c["name"]} : {c["description"]} \n\n'
        if 'args' in c:
            commands += "\t\t"+"-arguments : "+c["args"]+"\n\n"
    commands += "```"
    await ctx.message.channel.send(commands)
    return

client.loop.create_task(nextSong())
client.run(TOKEN)

