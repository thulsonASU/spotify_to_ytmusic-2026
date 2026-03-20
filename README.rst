spotify_to_ytmusic
####################

.. |pypi-downloads| image:: https://img.shields.io/pypi/dm/spotify_to_ytmusic?style=flat-square
    :alt: PyPI Downloads
    :target: https://pypi.org/project/spotify_to_ytmusic/

.. |discuss| image:: https://img.shields.io/github/discussions/sigma67/spotify_to_ytmusic?style=flat-square
   :alt: Ask questions at Discussions
   :target: https://github.com/sigma67/spotify_to_ytmusic/discussions

.. |code-coverage| image:: https://img.shields.io/codecov/c/github/sigma67/spotify_to_ytmusic?style=flat-square
    :alt: Code coverage
    :target: https://codecov.io/gh/sigma67/spotify_to_ytmusic

.. |latest-release| image:: https://img.shields.io/github/v/release/sigma67/spotify_to_ytmusic?style=flat-square
    :alt: Latest release
    :target: https://github.com/sigma67/spotify_to_ytmusic/releases/latest

.. |commits-since-latest| image:: https://img.shields.io/github/commits-since/sigma67/spotify_to_ytmusic/latest?style=flat-square
    :alt: Commits since latest release
    :target: https://github.com/sigma67/spotify_to_ytmusic/commits


|pypi-downloads| |discuss| |code-coverage| |latest-release| |commits-since-latest|

A simple command line script to clone a Spotify playlist to YouTube Music. Updated for the 2026 Spotify API structure.

- Transfer a single Spotify playlist
- Like all the songs in a Spotify playlist
- Update a transferred playlist on YouTube Music
- Transfer all owned playlists for a Spotify user
- Like all songs from all playlists for a Spotify user
- Remove playlists from YouTube Music


Install
-------

- Python 3.10 or later - https://www.python.org
- pipx - https://pipx.pypa.io

.. code-block::

    pipx ensurepath

- Open a new shell. Install:

.. code-block::

    pipx install spotify_to_ytmusic


Setup
-------

1. Generate a new app at https://developer.spotify.com/dashboard
2. Generate a new app by following instructions at https://ytmusicapi.readthedocs.io/en/stable/setup/oauth.html
3. Run

.. code-block::

    spotify_to_ytmusic setup

**Note for 2026 Users:** Due to Spotify API changes, ensure your Spotify account is **Premium** and your email is added to the "User Allowlist" in your Spotify Developer App settings to avoid empty track results.

If you want to transfer private playlists from Spotify (i.e. liked songs), choose "yes" for oAuth authentication, otherwise choose "no". 
For oAuth authentication you should set ``http://127.0.0.1:8888/callback`` as the redirect URI for your app in Spotify's developer dashboard.

Usage
------

After you've completed setup, you can simply run the script from the command line using:

.. code-block::

    spotify_to_ytmusic create <spotifylink>

where ``<spotifylink>`` is a link like https://open.spotify.com/playlist/37i9dQZF1DXcBWm0lb9mgj

The script will log its progress and output songs that were not found in YouTube Music to **noresults_youtube.txt**.

Transfer all playlists of a Spotify user
----------------------------------------

For migration purposes, it is possible to transfer all playlists created by the user. 

.. code-block::

    spotify_to_ytmusic all me

*Note: This command now filters for playlists owned by you to avoid cluttering your YouTube library with followed public playlists (e.g., 'Lofi Girl').*

Transfer liked tracks of the Spotify user
-----------------------------------------

**You must use oAuth authentication for transferring liked songs.**

.. code-block::

   spotify_to_ytmusic liked

This command will open a browser where you should give access to your account. After authorization, you will be redirected to your redirect URI; copy the link (looks like ``127.0.0.1:8888/callback?code=...``) and paste it into the command line.

Command line options
---------------------

To view all options, run:

.. code::

    spotify_to_ytmusic -h


Available subcommands:

.. code-block::

    positional arguments:
      {setup,create,update,remove,all,liked}
                        Provide a subcommand
        setup           Set up credentials
        create          Create a new playlist on YouTube Music.
        update          Update an existing YouTube Music playlist with entries from Spotify.
        remove          Remove playlists with specified regex pattern.
        all             Transfer all playlists owned by the specified user.
        liked           Transfer all "Liked Songs" from Spotify.

    options:
      -h, --help            show this help message and exit
