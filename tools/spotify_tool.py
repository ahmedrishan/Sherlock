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


def play_spotify(query: str = "") -> str:
    """Opens Spotify and searches/plays a specific song, artist, or playlist.

    Args:
        query (str): The song title, artist name, or playlist to search and play (e.g. 'Despacito', 'Starboy', 'Bohemian Rhapsody', 'Taylor Swift'). Always extract and pass the song name here.

    Returns:
        str: Confirmation message.
    """
    logger.info(f"play_spotify tool invoked with query: '{query}'")
    raw_query = query.strip()

    # Clean voice transcription noise & common prefixes/suffixes
    clean_q = raw_query.lower()
    for phrase in [
        "play a song on spotify", "play a song in spotify", "play a song",
        "play music on spotify", "play music", "play song", "on spotify", "in spotify",
        "played'ng", "played", "playing", "listen to", "play"
    ]:
        clean_q = clean_q.replace(phrase, "")

    clean_q = clean_q.strip(" '\".")

    # Phonetic corrections map for common misheard names
    corrections = {
        "nairam": "neram",
        "nayram": "neram",
        "star boy": "starboy",
    }
    clean_q = corrections.get(clean_q, clean_q)

    try:
        if clean_q:
            # Search and open Spotify to target song/artist
            encoded_query = urllib.parse.quote(clean_q)
            cmd = f"start spotify:search:{encoded_query}"
            subprocess.Popen(cmd, shell=True)

            # Wait 2 seconds for Spotify to fetch search results over network & render UI
            time.sleep(2.0)

            # Bring Spotify window to foreground and send DOWN arrow + Enter to play Top Result
            ps_code = """
            $ws = New-Object -ComObject WScript.Shell
            if ($ws.AppActivate('Spotify')) {
                Start-Sleep -Milliseconds 500
                $ws.SendKeys('{DOWN}')
                Start-Sleep -Milliseconds 300
                $ws.SendKeys('~')
            }
            """
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_code], capture_output=True, text=True)

            logger.info(f"Opened Spotify search for '{clean_q}' and triggered playback.")
            return f"Searching and playing '{clean_q}' on Spotify."
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


def pause_spotify() -> str:
    """Pauses or stops music playback on Spotify without closing the Spotify application.
    Use this tool whenever the user asks to 'pause music', 'stop music', 'stop playing music', 'pause spotify', or 'stop spotify'.

    Returns:
        str: Confirmation message.
    """
    logger.info("pause_spotify tool invoked.")
    try:
        _send_media_play_pause()
        logger.info("Sent Media Play/Pause signal to pause music.")
        return "Paused music playback on Spotify."
    except Exception as e:
        logger.error(f"Error pausing Spotify: {e}")
        return f"Failed to pause Spotify: {e}"
