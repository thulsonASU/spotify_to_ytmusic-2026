import html
import re
import string

import spotipy
from spotipy import CacheFileHandler
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth

from spotify_to_ytmusic.settings import SPOTIPY_CACHE_FILE, Settings
from spotify_to_ytmusic.utils.browser import has_browser

CYAN = '\033[0;36m'
YELLOW = '\033[1;33m'
GREEN = '\033[0;32m'
RED = '\033[0;31m'
NC = '\033[0m'

class Spotify:
    def __init__(self):
        settings = Settings()
        conf = settings["spotify"]
        client_id = conf["client_id"]

        assert set(client_id).issubset(string.hexdigits), (
            f"Spotify client_id not set or invalid: {client_id}"
        )
        client_secret = conf["client_secret"]
        assert set(client_secret).issubset(string.hexdigits), (
            f"Spotify client_secret not set or invalid: {client_secret}"
        )

        use_oauth = conf.getboolean("use_oauth")

        cache_handler = CacheFileHandler(cache_path=SPOTIPY_CACHE_FILE.as_posix())
        if use_oauth:
            # FIX: Expanded scopes to prevent 403 on profile/playlist crawls
            expanded_scopes = "user-library-read playlist-read-private playlist-read-collaborative user-read-private"
            auth = SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri="http://127.0.0.1:8888/callback",
                scope=expanded_scopes,
                cache_handler=cache_handler,
                open_browser=has_browser(),
            )
            self.api = spotipy.Spotify(auth_manager=auth)
        else:
            client_credentials_manager = SpotifyClientCredentials(
                client_id=client_id,
                client_secret=client_secret,
                cache_handler=cache_handler,
            )
            self.api = spotipy.Spotify(
                client_credentials_manager=client_credentials_manager
            )

    def getSpotifyPlaylist(self, url):
        playlistId = extract_playlist_id_from_url(url)

        print(f"Getting Spotify tracks for ID: {playlistId}...")
        results = self.api.playlist(playlistId)
        name = results.get("name", "Unknown Playlist")

        # 2026 FIX: Ensure 'total' is always defined
        tracks_data = results.get("tracks", results.get("items", {}))

        if isinstance(tracks_data, list):
            items = tracks_data
            total = len(items)
        else:
            # Check for 'total' in the object, or fallback to length of items
            items = tracks_data.get("items", [])
            total = tracks_data.get("total", len(items))

        tracks = build_results(items)
        count = len(items) # Use actual item count for the offset
        print(f"Spotify tracks: {len(tracks)}/{total}")

        # Only paginate if there are actually more tracks to get
        while count < total:
            try:
                # 2026 FIX: Spotify often returns 'items' directly now
                more_tracks = self.api.playlist_items(playlistId, offset=count, limit=100)

                # Logic to find the items list regardless of nesting
                new_items = more_tracks.get("items", []) if isinstance(more_tracks, dict) else []

                if not new_items:
                    print(f"${RED}[DEBUG] No items found in pagination at offset {count}${NC}")
                    break

                # Append the newly discovered tracks
                batch_results = build_results(new_items)
                tracks += batch_results

                # Increment by the actual API item count, not our filtered results
                count += len(new_items)
                print(f"Spotify tracks: {len(tracks)}/{total}")

            except Exception as e:
                print(f"${RED}Pagination error: {e}${NC}")
                break

        return {
            "tracks": tracks,
            "name": name,
            "description": html.unescape(results.get("description", "") or ""),
        }

    def getUserPlaylists(self, user):
        me = self.api.me()["id"]
        results = self.api.current_user_playlists(limit=50)
        pl = results["items"]

        while results["next"]:
            results = self.api.next(results)
            pl.extend(results["items"])

        # NEW 2026 LOGIC: Filter for owned playlists and check 'items'
        final_list = []
        for p in pl:
            # Check for the new 'items' key or fallback to 'tracks'
            tracks_data = p.get("items") if p.get("items") else p.get("tracks", {})

            # Use the new length check since 'total' is unreliable now
            item_count = len(tracks_data) if isinstance(tracks_data, list) else tracks_data.get("total", 0)

            if p.get("owner", {}).get("id") == me:
                final_list.append(p)
                print(f"  > Validated: {p['name']} ({item_count} items)")

        return final_list

    def getLikedPlaylist(self):
        response = self.api.current_user_saved_tracks(limit=50)
        tracks = response["items"]
        while response["next"] is not None:
            response = self.api.current_user_saved_tracks(
                limit=50, offset=response["offset"] + 50
            )
            tracks.extend(response["items"])

        return {
            "tracks": build_results(tracks),
            "name": "Liked songs (Spotify)",
            "description": "Your liked tracks from spotify",
        }

    def getSingleTrack(self, song_url):
        return self.api.track(song_url)

# ... (build_results and extract_playlist_id_from_url remain the same)

def build_results(tracks, album=None):
    results = []
    for item in tracks:
        if not isinstance(item, dict):
            continue

        # 2026 FIX: Spotify shifted the track object location.
        # It could be item['track'], item['item'], or the item itself.
        t = item.get("track") or item.get("item") or item

        if not isinstance(t, dict):
            continue

        # Hunt for the name - try every variation Spotify uses in 2026
        name = t.get("name") or t.get("title") or t.get("display_name")

        # Hunt for duration - handle the ms to seconds shift
        duration_ms = t.get("duration_ms") or t.get("duration") or t.get("length_ms") or t.get("length", 0)

        # Hunt for Artists - handle lists of dicts vs lists of strings
        raw_artists = t.get("artists", [])
        if raw_artists and isinstance(raw_artists, list):
            if isinstance(raw_artists[0], dict):
                artist_names = " ".join([a.get("name", "Unknown Artist") for a in raw_artists])
            else:
                artist_names = " ".join([str(a) for a in raw_artists])
        else:
            artist_names = "Unknown Artist"

        # If we still have no name, we likely hit a non-track item (ad, podcast, etc)
        if not name:
            # Uncomment the line below if you still get 0/X to see the raw keys
            # print(f"{RED}[DEBUG] Missing Name. Keys present: {list(t.keys())}{NC}")
            continue

        # Album handling
        album_obj = t.get("album", {})
        current_album = album if album else (album_obj.get("name") if isinstance(album_obj, dict) else "Unknown Album")

        results.append(
            {
                "artist": artist_names,
                "name": name,
                "album": current_album,
                "duration": duration_ms / 1000 if duration_ms > 500 else duration_ms,
            }
        )

    return results


def extract_playlist_id_from_url(url: str) -> str:
    if match := re.search(r"playlist\/(?P<id>\w{22})\W?", url):
        return match.group("id")
    elif match := re.search(r"playlist\/(?P<id>\w+)\W?", url):
        id = match.group("id")
        raise ValueError(
            f"Bad playlist id: {id}\nA playlist id should be 22 characters long, not {len(id)}"
        )
    else:
        raise ValueError(
            f"Couldn't understand playlist url: {url}\nA playlist url should look like this: https://open.spotify.com/playlist/37i9dQZF1DZ06evO41HwPk"
        )
