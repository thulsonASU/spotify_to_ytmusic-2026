import time
import json
from datetime import datetime
from pathlib import Path

import spotipy

from spotify_to_ytmusic.setup import setup as setup_func
from spotify_to_ytmusic.spotify import Spotify
from spotify_to_ytmusic.ytmusic import YTMusicTransfer

CACHE_FILE = Path("~/.cache/spotify_to_ytmusic/yt_cache.json").expanduser()
CYAN = '\033[0;36m'
YELLOW = '\033[1;33m'
GREEN = '\033[0;32m'
RED = '\033[0;31m'
NC = '\033[0m'

def _get_spotify_playlist(spotify, playlist):
    try:
        return spotify.getSpotifyPlaylist(playlist)
    except Exception as ex:
        print(
            "Could not get Spotify playlist. Please check the playlist link.\n Error: "
            + repr(ex)
        )
        return


def _print_success(name, playlistId):
    print(
        f"Success: created playlist '{name}' at\n"
        f"https://music.youtube.com/playlist?list={playlistId}"
    )


def _init():
    return Spotify(), YTMusicTransfer()


def all(args):
    spotify, ytmusic = _init()
    pl = spotify.getUserPlaylists(args.user)

    # 1. Skip logic (already discussed)
    yt_library = ytmusic.api.get_library_playlists(limit=None)
    existing_yt_names = {p['title'].lower() for p in yt_library}

    for p in pl:
        p_name = p["name"]
        if p_name.lower() in existing_yt_names:
            print(f"Skipping {p_name} (Exists)")
            continue

        print(f"\n--- Processing: {p_name} ---")
        spotify_data = spotify.getSpotifyPlaylist(p["external_urls"]["spotify"])

        # 2. FUZZY CACHE SEARCH
        final_video_ids = []
        tracks_to_search = []

        for track in spotify_data["tracks"]:
            cached_id = get_cached_id(track["name"], track["artist"])
            if cached_id:
                final_video_ids.append(cached_id)
            else:
                tracks_to_search.append(track)

        # 3. SEARCH ONLY WHAT WE DON'T KNOW
        if tracks_to_search:
            print(f"  Searching for {len(tracks_to_search)} new tracks...")
            new_ids = ytmusic.search_songs(tracks_to_search, use_cached=args.use_cached)

            # Save new results to cache
            for i, track in enumerate(tracks_to_search):
                if i < len(new_ids):
                    set_cached_id(track["name"], track["artist"], new_ids[i])

            final_video_ids.extend(new_ids)

        # 4. SMART CHUNKING: Create and Fill
        # Create empty playlist
        playlist_id = ytmusic.api.create_playlist(
            p_name,
            p["description"],
            privacy_status="PUBLIC" if p["public"] else "PRIVATE"
        )

        # Add in batches of 25 to stay under the radar
        batch_size = 25
        for i in range(0, len(final_video_ids), batch_size):
            batch = final_video_ids[i : i + batch_size]
            ytmusic.api.add_playlist_items(playlist_id, batch)
            print(f"  Added tracks {i} to {i+len(batch)}...")
            time.sleep(1.5) # The "I'm a human" pause

        print(f"Successfully synced: {p_name}")


def _create_ytmusic(args, playlist, ytmusic):
    date = ""
    if args.date:
        date = " " + datetime.today().strftime("%m/%d/%Y")
    name = args.name + date if args.name else playlist["name"] + date
    info = playlist["description"] if (args.info is None) else args.info
    videoIds = ytmusic.search_songs(playlist["tracks"], use_cached=args.use_cached)
    if args.like:
        for id in videoIds:
            ytmusic.rate_song(id, "LIKE")

    playlistId = ytmusic.create_playlist(
        name, info, "PUBLIC" if args.public else "PRIVATE", videoIds
    )
    _print_success(name, playlistId)


def create(args):
    spotify, ytmusic = _init()
    playlist = _get_spotify_playlist(spotify, args.playlist)
    _create_ytmusic(args, playlist, ytmusic)


def liked(args):
    spotify, ytmusic = _init()
    if not isinstance(spotify.api.auth_manager, spotipy.SpotifyOAuth):
        raise Exception("OAuth not configured, please run setup and set OAuth to 'yes'")
    playlist = spotify.getLikedPlaylist()
    _create_ytmusic(args, playlist, ytmusic)


def update(args):
    spotify, ytmusic = _init()
    playlist = _get_spotify_playlist(spotify, args.playlist)
    playlistId = ytmusic.get_playlist_id(args.name)
    videoIds = ytmusic.search_songs(playlist["tracks"], use_cached=args.use_cached)
    if not args.append:
        ytmusic.remove_songs(playlistId)
    time.sleep(2)
    ytmusic.add_playlist_items(playlistId, videoIds)


def remove(args):
    ytmusic = YTMusicTransfer()
    ytmusic.remove_playlists(args.pattern)


def search(args):
    spotify, ytmusic = _init()
    track = spotify.getSingleTrack(args.link)
    tracks = {
        "name": track["name"],
        "artist": track["artists"][0]["name"],
        "duration": track["duration_ms"] / 1000,
        "album": track["album"]["name"],
    }

    video_id = ytmusic.search_songs([tracks], use_cached=args.use_cached)

    if not video_id:
        print("Error: No Match found.")
        return
    print(f"https://music.youtube.com/watch?v={video_id[0]}")


def cache_clear(args):
    from spotify_to_ytmusic.utils.cache_manager import CacheManager

    cacheManager = CacheManager()
    cacheManager.remove_cache_file()


def setup(args):
    setup_func(args.file)

def get_cached_id(spotify_track_name, artist):
    if not CACHE_FILE.exists():
        return None
    with open(CACHE_FILE, "r") as f:
        cache = json.load(f)
    # Keying by "Artist - Title" for a simple fuzzy match
    search_key = f"{artist} - {spotify_track_name}".lower()
    return cache.get(search_key)

def set_cached_id(spotify_track_name, artist, yt_id):
    cache = {}
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "r") as f:
            cache = json.load(f)

    search_key = f"{artist} - {spotify_track_name}".lower()
    cache[search_key] = yt_id

    # Create directory if missing
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=4)
