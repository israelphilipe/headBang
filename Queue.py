import youtube_dl
import os
import shutil
import distutils


class Queue:
    def __init__(self, channel, guild_id: str):
        self.queue = {}
        self.guild_id = guild_id
        self.current = -1
        self.looping = False
        ytdl_format_options = {
            'format': 'bestaudio/best',
            'outtmpl': f'./Queues/{self.guild_id}/%(id)s.mp3',
            'restrictfilenames': True,
            'noplaylist': True,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'logtostderr': False,
            'quiet': True,
            'no_warnings': True,
            'default_search': 'auto',
            'source_address': '0.0.0.0'  # ipv6 addresses cause issues sometimes
        }
        # ytdl_format_options = {
        #     'format': 'bestaudio/best',
        #     'outtmpl': f'./Queues/{self.guild_id}/%(id)s.mp3',
        #     'quiet': True,
        #     'postprocessors': [{
        #         'key': 'FFmpegExtractAudio',
        #         'preferredcodec': 'mp3',
        #         'preferredquality': '192'
        #     }],
        #     'default_search': 'auto',
        # }
        self.ytdl = youtube_dl.YoutubeDL(ytdl_format_options)
        self.queue_path = os.path.abspath(os.path.realpath(f'./Queues/{self.guild_id}'))
        self.channel = channel

    def add(self, song: dict):
        if song['id'] in self.queue:
            return False
        self.queue[song['id']] = song
        return song

    def remove_from_pos(self, pos: int):

        if pos < 0 or pos >= self.size():
            return False
        song_id = list(self.queue)[pos]
        del self.queue[song_id]
        if pos <= self.current:
            self.current -= 1
        return self.current

    def size(self):
        return len(self.queue)

    def get_song(self, position: int):
        song_id = list(self.queue)[position]
        return self.queue[song_id]

    def next(self):
        if self.is_looping and self.current+1 == self.size():
            self.current = 0
        else:
            self.current += 1
        song_id = list(self.queue)[self.current]

        return self.queue[song_id]

    def current_position(self):
        return self.current

    def current_song(self):
        song_id = list(self.queue)[self.current]
        return self.queue[song_id]

    def clear(self):
        self.queue.clear()
        self.current = 0
        try:
            shutil.rmtree(self.queue_path, ignore_errors=True)
            print('removing : '+self.queue_path)
        except FileNotFoundError:
            print('error removing : '+self.queue_path)

    def toggle_loop(self):
        self.looping = not self.looping
        return self.looping

    def is_looping(self):
        return self.looping

    def get_youtube_dl(self):
        return self.ytdl

    def get_channel(self):
        return self.channel

    def set_channel(self, channel):
        self.channel = channel

    def get_path(self):
        return self.queue_path

    def jump_to(self, pos: int):
        if pos < 0 or pos >= self.size():
            return False
        self.current = pos
        return self.current_song()
