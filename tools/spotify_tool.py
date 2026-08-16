"""Spotify playback & search tool for Sherlock."""

import ctypes
import os
import subprocess
import time
import urllib.parse
from utils.logger import get_logger

logger = get_logger(__name__)

# Windows Virtual Key code for Media Play/Pause
VK_RETURN = 0x0D
VK_MEDIA_PLAY_PAUSE = 0xB3
KEYEVENTF_KEYUP = 0x0002


def _send_key(vk_code: int):
    """Simulates pressing a Virtual Key on Windows."""
    if os.name == "nt":
        try:
            ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
            time.sleep(0.05)
            ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)
        except Exception as e:
            logger.error(f"Error sending key {vk_code}: {e}")


def _send_media_play_pause():
    """Simulates pressing the Windows Media Play/Pause key."""
    _send_key(VK_MEDIA_PLAY_PAUSE)


def _send_enter_key():
    """Simulates pressing the Enter key to select top search result."""
    _send_key(VK_RETURN)


def play_spotify(song_or_artist: str = "") -> str:
    """Opens Spotify and plays music or searches for a specific song, artist, or playlist.
    Use this tool whenever the user says 'play a song on spotify', 'play music', 'play [song name]', or 'resume music'.

    Args:
        song_or_artist (str, optional): The name of the song, artist, or playlist to play (e.g., 'Starboy', 'Taylor Swift', 'Bohemian Rhapsody'). Defaults to empty string.

    Returns:
        str: Confirmation message.
    """
    logger.info(f"play_spotify tool invoked with query: '{song_or_artist}'")
    query = song_or_artist.strip()

    # Clean generic search queries
    lower_q = query.lower()
    if lower_q in ["a song", "some music", "music", "song", "spotify", "on spotify", "play a song"]:
        query = ""

    try:
        if query:
            # Search and open Spotify to the target song/artist
            encoded_query = urllib.parse.quote(query)
            cmd = f"start spotify:search:{encoded_query}"
            subprocess.Popen(cmd, shell=True)
            time.sleep(1.2)
            # Send Enter key to trigger top hit playback
            _send_enter_key()
            logger.info(f"Opened Spotify search for '{query}' and triggered play.")
            return f"Searching and playing '{query}' on Spotify."
        else:
            # Resume / play current Spotify track
            subprocess.Popen("start spotify:", shell=True)
            time.sleep(0.8)
            _send_media_play_pause()
            logger.info("Triggered Spotify playback resume.")
            return "Resuming music playback on Spotify."
    except Exception as e:
        logger.error(f"Error executing play_spotify: {e}")
        return f"Failed to control Spotify playback: {e}"
