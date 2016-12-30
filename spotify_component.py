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
            # artist = unicodedata.normalize('NFKD', track['artists'][0]['name']).encode('ascii','ignore')

            # song = song_name + " " + artist
            song = song_name
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
                    song_name = song.split(":::")[0]
                    if song_name.replace(" ", "").lower() not in spotify_songs_stripped:
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
        searched_songs = []
        passed_songs = [] #songs that have already been previously searched

        try:
            with open(self.path + "searched_songs.txt", "r") as f:
                for line in f:
                    line = line.rstrip()
                    passed_songs.append(line.split("-- ")[1])
        except IOError:
            print "Previously searched songs list is unavailable, using blank entry"

        for pl_name in playlists.keys():
            print "***updating playlist " + pl_name

            if "__NEW__" in pl_name:
                playlist = self.sp.user_playlist_create(self.username, pl_name.replace("__NEW__", ""))
                pl_id = playlist['id']
                songs = playlists[pl_name]
            else:
                songs = playlists[pl_name][:-1]
                pl_id = playlists[pl_name][-1]
            song_ids = []

            for song in songs:
                if song in passed_songs:
                    print "PASSING OVER: ", song
                    continue
                try:
                    song_name = song.split(":::")[0]
                    song_duration = self.minsec_2_millis(song.split(":::")[1])
                    print "ADDING: ", song_name
                    results = self.sp.search(song_name, limit=10, type="track")
                    track = results['tracks']['items']

                    if len(track) == 0: #song not found
                        searched_songs.append("NOT FOUND-- " + song)
                    else:
                        matched_track = next((t for t in track if int(t['duration_ms'])/1000 == song_duration), None)
                        if matched_track == None:
                            searched_songs.append("DUR MATCH NONE-- " + song)
                            song_ids.append(track[0]['id'])
                        else:
                            song_ids.append(matched_track['id'])
                            searched_songs.append("ADDED TO " + pl_name.upper() + "-- " + song)
                except IndexError:
                    print "Song name is malformed: ", song
                    searched_songs.append("MALFORMED-- " +  song)
                    continue

            if len(song_ids) > 0:
                print "adding songs to playlist..."
                self.sp.user_playlist_add_tracks(self.username, pl_id, song_ids)
            else:
                print "no songs to update"
            print "--------------------\n"
        return searched_songs

    def test_search(self, song):
        results = self.sp.search(song, limit=10, type="track")
        track = results['tracks']['items']
        print "GOT TRACKS: ", len(track)
        matched_track = next(t for t in track if int(t['duration_ms']) == 117054)
        print "MATCHED_TRACK: ", matched_track['id']


    def run(self):
        print "unpacked itunes..."
        itunes_playlists = self.format_itunes_playlists()
        print "retriving spotify..."
        spotify_playlists = self.get_spotify_playlists()
        print "calculating diff dict..."
        diff_dict = self.diff_playlists(itunes_playlists, spotify_playlists)
        searched_songs = self.update_spotify(diff_dict)
        with open(self.path + "searched_songs.txt", 'a') as f:
            for item in searched_songs:
                f.write("%s\n" % item)
        print "done!"

if __name__ == '__main__':
    se = SpotifyExporter()
    se.run()
