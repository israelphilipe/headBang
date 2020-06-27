import random
import asyncio
import json
import time
from discord.ext import commands
from discord import VoiceChannel
import shutil
import discord
from discord.errors import ClientException
from discord.ext.commands.errors import CommandNotFound
import os
from Queue import Queue
client = commands.Bot(command_prefix='$')

TOKEN = os.environ['TOKEN']

ffmpeg_options = {
    'options': '-vn',
}


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, ytdl, *, loop=None, stream=False):
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

queues = {}


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))


@client.command(pass_context=True)
async def ping(ctx):
    await ctx.send('latency : '+str(round(client.latency*1000))+'ms')


@client.command(pass_context=True)
async def join(ctx, flag=0):
    channel = ctx.message.channel
    if ctx.message.author.voice is None or ctx.message.author.voice.channel is None:
        await channel.send('You are not in a voice server')
        return
    voice_channel = ctx.author.voice.channel
    if ctx.voice_client is None:
        await voice_channel.connect()
    else:
        await ctx.voice_client.move_to(voice_channel)
    if flag == 0:
        await channel.send(enter_chat_quotes[random.randint(0, len(enter_chat_quotes))-1])
    guild_id = str(ctx.message.guild.id)
    queues[guild_id] = Queue(channel, guild_id)

    return


@client.command(pass_context=True)
async def leave(ctx):
    server = ctx.message.guild.voice_client
    if not server:
        await ctx.message.channel.send("Not in a voice channel")
    await stop(ctx)
    await server.disconnect()


async def queue(ctx, url: str):
    guild_id = str(ctx.message.guild.id)
    if queues[guild_id] is None:
        raise discord.errors.ClientException
    song = await YTDLSource.from_url(url, queues[guild_id].get_youtube_dl(), loop=client.loop)
    if queues[guild_id].size() >= 50:
        await ctx.message.channel.send('Queue is full, please remove an item')
        return
    queues[guild_id].add(song)
    await ctx.message.channel.send(f"Song {song['title']} added to the queue")


@client.command(pass_context=True, aliases=['queue'])
async def show_queue(ctx):

    guild_id = str(ctx.message.guild.id)
    if guild_id not in queues:
        return await ctx.message.channel.send(f"```CSS\n[Oops, it does not seem that you have a queue.]\n```")
    if queues[guild_id].size() == 0:
        return await ctx.message.channel.send(f"```CSS\n[Queue is empty]\n```")
    q = "```CSS\n"
    for i in range(0, queues[guild_id].size()):
        if i == queues[guild_id].current_position():
            q += '-'
        q += f"{i+1} : {queues[guild_id].get_song(i)['title']}\n"
    if queues[guild_id].is_looping():
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
    guild_id = str(ctx.message.guild.id)
    url = str(args)
    await queue(ctx, url)
    if queues[guild_id].size() == 1:
        await next(ctx)


async def next_song(ctx=None, flag=0):
    while True:
        for voice_client in client.voice_clients:
            guild_id = str(voice_client.guild.id)
            if guild_id not in queues:
                return
            q = queues[guild_id]
            if q.size() == 0:
                continue
            if ctx is not None:
                if voice_client.is_playing() and flag == 1 and voice_client == ctx.message.guild.voice_client:
                    voice_client.stop()
            if not voice_client.is_playing() and not voice_client.is_paused():
                if not q.is_looping() and q.size() == q.current_position():
                    await ctx.message.channel.send('Done playing')
                    await stop(ctx)
                else:
                    song = discord.FFmpegPCMAudio(q.next()['file_path'], **ffmpeg_options)
                    voice_client.play(song)
                    await q.get_channel().send(f'Playing {q.current_song()["title"]}')
        await asyncio.sleep(0.5)
        flag = 0


@client.command(pass_context=True)
async def next(ctx):
    await next_song(ctx, 1)


@client.command(pass_context=True)
async def loop(ctx):
    guild_id = str(ctx.message.guild.id)
    msg = "Started" if queues[guild_id].toggle_loop() else "Stopped"
    return await ctx.message.channel.send(f'```CSS\n{msg} looping queue\n```')


@client.command(pass_context=True, aliases=['current'])
async def current_in_queue(ctx):
    guild_id = ctx.message.guild.id
    if queues[guild_id] == 0:
        return await ctx.message.channel.send(f"```CSS\n[Queue is empty]\n```")
    await ctx.message.channel.send('```Current song in queue: {}```'
                                   .format(queues[guild_id].get_current_song()['title']))


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
    await ctx.message.channel.send('Done playing')
    return


@client.command(pass_context=True)
async def clear(ctx):
    guild_id = str(ctx.message.guild.id)
    if guild_id in queues:
        queues[guild_id].clear()
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
    await ctx.message.channel.send('Oops. Something went wrong')
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

client.loop.create_task(next_song())
client.run(TOKEN)

