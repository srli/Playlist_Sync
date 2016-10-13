from os import listdir

import sys
import spotipy
import spotipy.util as util

import unicodedata

class SpotifyExporter:
    def __init__(self):
        scope = 'user-library-read'
        self.username = "12159015810"
        self.token = 
        self.sp = spotipy.Spotify(auth=self.token)

        self.path = "/Users/sophie/Scripts/playlist_sync/playlists/"
        self.raw_itunes_playlists = listdir(self.path)

    def format_itunes_playlists(self):
        itunes_playlists = {}

        for pl in self.raw_itunes_playlists:
            this_pl_songs = []

            with open(self.path+pl, 'r') as f:
                songs = f.read().split("+++")
                for song in songs:
                    if "??" in song:
                        continue
                    else:
                        this_pl_songs.append(song)

            if len(this_pl_songs) > 50:
                continue
            else:
                itunes_playlists[pl.replace(".xml", "")] = this_pl_songs

        return itunes_playlists

    def return_spotify_tracks(self,tracks,all_tracks=None):
        if not all_tracks:
            all_tracks = []

        for item in tracks['items']:
            track = item['track']

            song_name = unicodedata.normalize('NFKD', track['name']).encode('ascii','ignore')

            artist = unicodedata.normalize('NFKD', track['artists'][0]['name']).encode('ascii','ignore')

            all_tracks.append(song_name + " " + artist)

        return all_tracks

    def get_spotify_playlists(self):
        playlists = self.sp.user_playlists(self.username)
        all_spotify_playlists = {}

        for playlist in playlists['items']:
            if playlist['owner']['id'] == self.username:
                results = self.sp.user_playlist(self.username, playlist['id'],
                    fields="tracks,next")
                tracks = results['tracks']
                playlist_tracks = self.return_spotify_tracks(tracks)
                while tracks['next']:
                    tracks = self.sp.next(tracks)
                    playlist_tracks = self.return_spotify_tracks(tracks, playlist_tracks)

                playlist_name = unicodedata.normalize('NFKD', playlist['name']).encode('ascii','ignore')
                all_spotify_playlists[playlist_name] = playlist_tracks

        return all_spotify_playlists


    def diff_playlists(self, itunes, spotify):
        diff_dict = {}
        for pl_name in itunes.keys():
            itunes_songs = itunes.get(pl_name)
            spotify_songs = spotify.get(pl_name, None)

            if not spotify_songs:
                diff_dict[pl_name] = itunes_songs
            else:
                spotify_songs_stripped = [s.replace(" ", "").lower() for s in spotify_songs]
                songs_to_add = []
                for i, song in enumerate(itunes_songs):
                    if song.replace(" ", "").lower() not in spotify_songs_stripped:
                        songs_to_add.append(spotify_songs[i])
                diff_dict[pl_name] = songs_to_add

        return diff_dict

    def run(self):
        itunes_playlists = self.format_itunes_playlists()
        spotify_playlists = self.get_spotify_playlists()

        diff_dict = diff_playlists(itunes_playlists, spotify_playlists)

        print spotify_playlists

se = SpotifyExporter()
se.run()
# print se.playlists
