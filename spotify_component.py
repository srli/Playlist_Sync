from os import listdir

import sys
import spotipy
import spotipy.util as util

import unicodedata

class SpotifyExporter:
    def __init__(self):
        scope = 'user-library-read playlist-modify-public'
        self.username = "12159015810"
        self.token = util.prompt_for_user_token(self.username, scope, client_id='b21f7cde44fb4641956099b290972ab4', client_secret='b196b0b207144a88afd2388cca2670b9' , redirect_uri='http://www.example.com/callback')
        self.sp = spotipy.Spotify(auth=self.token)

        self.path = "/Users/sophie/Scripts/playlist_sync/playlists/"
        self.raw_itunes_playlists = listdir(self.path)

    def format_itunes_playlists(self):
        itunes_playlists = {}
        for pl in self.raw_itunes_playlists:
            if pl.startswith("."):
                continue
            if not pl.endswith(".xml"):
                continue

            this_pl_songs = []
            with open(self.path+pl, 'r') as f:
                songs = f.read().split("+++")
                for song in songs:
                    if "??" in song:
                        continue
                    else:
                        try:
                            if "(" in song:
                                s1 = song.split("(")[0]
                                s2 = song.split(")")[1]
                                song = s1 + s2
                            if "[" in song:
                                s1 = song.split("[")[0]
                                s2 = song.split("]")[1]
                                song = s1 + s2
                        except IndexError:
                            pass
                        this_pl_songs.append(song)

            if len(this_pl_songs) > 70:
                print "playlist " + pl + " has too many songs"
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

            song = song_name + " " + artist
            try:
                if "(" in song:
                    s1 = song.split("(")[0]
                    s2 = song.split(")")[1]
                    song = s1 + s2
                if "[" in song:
                    s1 = song.split("[")[0]
                    s2 = song.split("]")[1]
                    song = s1 + s2
            except IndexError:
                pass

            all_tracks.append(song)

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
                playlist_tracks.append(playlist['id'])
                all_spotify_playlists[playlist_name] = playlist_tracks

        return all_spotify_playlists


    def diff_playlists(self, itunes, spotify):
        diff_dict = {}
        for pl_name in itunes.keys():
            itunes_songs = itunes.get(pl_name)
            spotify_songs = spotify.get(pl_name, None)

            if not spotify_songs:
                diff_dict[pl_name + "__NEW__"] = itunes_songs
            else:
                spotify_songs_stripped = [s.replace(" ", "").lower() for s in spotify_songs]
                songs_to_add = []
                for i, song in enumerate(itunes_songs):
                    if song.replace(" ", "").lower() not in spotify_songs_stripped:
                        songs_to_add.append(song)

                songs_to_add.append(spotify_songs[-1]) #we track pl ID by last elem of song list
                diff_dict[pl_name] = songs_to_add

        return diff_dict

    def minsec_2_millis(self, time):
        """converts string time to integer ms
        i.e 1:30 goes to 90000
        """
        try:
            minutes = int(time.split(":")[0])
            seconds = int(time.split(":")[1])
            return minutes*60 + seconds

        except ValueError:
            print "Trying to convert none time value: ", time
            return 0

    def update_spotify(self, playlists):
        missed_songs = []

        for pl_name in playlists.keys():
            print "updating playlist " + pl_name

            if "__NEW__" in pl_name:
                playlist = self.sp.user_playlist_create(self.username, pl_name.replace("__NEW__", ""))
                pl_id = playlist['id']
                songs = playlists[pl_name]
            else:
                songs = playlists[pl_name][:-1]
                pl_id = playlists[pl_name][-1]
            song_ids = []

            for song in songs:
                song_name = song.split(":::")[0]
                song_duration = self.minsec_2_millis(song.split(":::")[1])
                print "SONG NAME: ", song_name
                print "SONG DUR: ", song_duration
                results = self.sp.search(song_name, limit=10, type="track")
                track = results['tracks']['items']
                print "GOT TRACKS #: ", len(track)

                if len(track) == 0: #song not found
                    missed_songs.append(song)
                else:
                    # most_popular = max(t['popularity'] for t in tracks[track[]])
                    matched_track = next((t for t in track if int(t['duration_ms'])/1000 == song_duration), None)
                    if matched_track == None:
                        missed_songs.append(song)
                    else:
                        song_ids.append(matched_track['id'])

            print "adding songs to playlist..."
            print "PL ID: ", pl_id
            self.sp.user_playlist_add_tracks(self.username, pl_id, song_ids)

        return missed_songs

    def test_search(self, song):
        results = self.sp.search(song, limit=10, type="track")
        track = results['tracks']['items']
        print "GOT TRACKS: ", len(track)
        # print "T1: ", track[0]
        # print "DUR: ", track[0]["duration_ms"]
        matched_track = next(t for t in track if int(t['duration_ms']) == 117054)
        print "MATCHED_TRACK: ", matched_track['id']


    def run(self):
        print "unpacked itunes..."
        itunes_playlists = self.format_itunes_playlists()
        print "retriving spotify..."
        spotify_playlists = self.get_spotify_playlists()
        print "calculating diff dict..."
        diff_dict = self.diff_playlists(itunes_playlists, spotify_playlists)
        missed_songs = self.update_spotify(diff_dict)

if __name__ == '__main__':
    se = SpotifyExporter()
    # se.test_search("i hate u, i love u")
    # print se.minsec_2_millis("3:53")
    se.run()
