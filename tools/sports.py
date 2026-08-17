"""Sports scores and league standings tool for Sherlock Voice Assistant.

Queries TheSportsDB free public API for team scores, match status, and league standings.
"""

from typing import Any, Dict, List, Optional, Tuple
import urllib.request
import urllib.parse
import urllib.error
import json
from utils.logger import get_logger

logger = get_logger(__name__)

BASE_URL = "https://www.thesportsdb.com/api/v1/json/3"

# Known popular league name map for fast lookup
KNOWN_LEAGUES: Dict[str, str] = {
    "premier league": "4328",
    "english premier league": "4328",
    "epl": "4328",
    "la liga": "4335",
    "spanish la liga": "4335",
    "bundesliga": "4331",
    "german bundesliga": "4331",
    "serie a": "4332",
    "italian serie a": "4332",
    "ligue 1": "4334",
    "french ligue 1": "4334",
    "nba": "4387",
    "nfl": "4391",
    "mlb": "4424",
    "nhl": "4380",
    "mls": "4346",
    "major league soccer": "4346",
    "ipl": "4434",
    "indian premier league": "4434",
    "champions league": "4480",
    "uefa champions league": "4480",
}


def _http_get(url: str, timeout: int = 8) -> Optional[Dict[str, Any]]:
    """Helper to perform HTTP GET requests with custom User-Agent and explicit timeout."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "SherlockVoiceAssistant/1.0 (+https://github.com/sherlock-assistant)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                payload = response.read().decode("utf-8")
                return json.loads(payload)
    except Exception as e:
        logger.error(f"HTTP GET request failed for URL '{url}': {e}")
    return None


def get_live_score(team_name: str) -> str:
    """Queries real-time or latest match scores and game status for a sports team using TheSportsDB.

    Args:
        team_name (str): Name of the sports team (e.g., 'Arsenal', 'Real Madrid', 'Lakers', 'Yankees').

    Returns:
        str: Concise, speakable natural-language summary of the latest score and match status.
    """
    logger.info(f"get_live_score tool invoked for team: '{team_name}'")
    if not team_name or not team_name.strip():
        return "Please specify a valid team name."

    clean_name = team_name.strip()
    encoded_name = urllib.parse.quote(clean_name)

    # 1. Search for Team to get idTeam
    search_url = f"{BASE_URL}/searchteams.php?t={encoded_name}"
    search_data = _http_get(search_url)

    if not search_data or not search_data.get("teams"):
        logger.warning(f"Team '{clean_name}' not found in TheSportsDB search.")
        return f"I couldn't find a team named '{clean_name}'. Please verify the team name."

    team_info = search_data["teams"][0]
    team_id = team_info.get("idTeam")
    canonical_name = team_info.get("strTeam", clean_name)
    sport = team_info.get("strSport", "Sports")

    if not team_id:
        return f"Could not retrieve team details for '{canonical_name}'."

    # 2. Fetch latest finished/current events for team
    events_url = f"{BASE_URL}/eventslast.php?id={team_id}"
    events_data = _http_get(events_url)

    results = events_data.get("results") if events_data else None

    if not results or len(results) == 0:
        # Check upcoming events if no past event recorded
        next_url = f"{BASE_URL}/eventsnext.php?id={team_id}"
        next_data = _http_get(next_url)
        next_events = next_data.get("events") if next_data else None
        if next_events and len(next_events) > 0:
            next_game = next_events[0]
            event_name = next_game.get("strEvent", f"{canonical_name} game")
            date_str = next_game.get("dateEvent", "soon")
            time_str = next_game.get("strTime", "")
            return f"There are no recent game scores for {canonical_name}. Their next scheduled match is {event_name} on {date_str} {time_str}."
        return f"No recent or upcoming match records were found for {canonical_name}."

    latest_game = results[0]
    home_team = latest_game.get("strHomeTeam", "Home Team")
    away_team = latest_game.get("strAwayTeam", "Away Team")
    home_score = latest_game.get("intHomeScore")
    away_score = latest_game.get("intAwayScore")
    status = latest_game.get("strStatus", "")
    date_event = latest_game.get("dateEvent", "")
    league = latest_game.get("strLeague", sport)

    # Status formatting (FT = Full Time, HT = Half Time, NS = Not Started, Live / In-Progress)
    status_desc = "Final"
    if status.upper() in ["FT", "AET", "PEN"]:
        status_desc = "Full Time"
    elif status.upper() in ["HT"]:
        status_desc = "Half Time"
    elif status.upper() in ["1H", "2H", "LIVE"]:
        status_desc = "Live"
    elif status:
        status_desc = status

    if home_score is not None and away_score is not None:
        score_str = f"{home_team} {home_score}, {away_team} {away_score}"
        if date_event:
            return f"In their recent {league} match on {date_event}, the score was {score_str} ({status_desc})."
        return f"In their latest {league} match, the score was {score_str} ({status_desc})."
    else:
        event_title = latest_game.get("strEvent", f"{home_team} vs {away_team}")
        return f"The latest match for {canonical_name} was {event_title} on {date_event} ({status_desc})."


def _resolve_league_id(league_name: str) -> Optional[Tuple[str, str]]:
    """Resolves a league name string to (idLeague, canonical_league_name)."""
    clean_query = league_name.lower().strip()

    # Check direct dictionary mapping
    if clean_query in KNOWN_LEAGUES:
        league_id = KNOWN_LEAGUES[clean_query]
        return league_id, league_name.title()

    # Search through all_leagues endpoint
    all_leagues_url = f"{BASE_URL}/all_leagues.php"
    data = _http_get(all_leagues_url)
    if data and data.get("leagues"):
        for item in data["leagues"]:
            str_league = item.get("strLeague", "")
            if clean_query in str_league.lower() or str_league.lower() in clean_query:
                return item.get("idLeague"), str_league

    return None


def get_standings(league_name: str) -> str:
    """Queries current league table standings for a specified sports league using TheSportsDB.

    Args:
        league_name (str): Name of the sports league (e.g., 'English Premier League', 'La Liga', 'NBA', 'NFL').

    Returns:
        str: Concise natural-language summary of the current top team standings.
    """
    logger.info(f"get_standings tool invoked for league: '{league_name}'")
    if not league_name or not league_name.strip():
        return "Please specify a valid league name."

    resolved = _resolve_league_id(league_name)
    if not resolved or not resolved[0]:
        return f"I couldn't find standings for '{league_name}'. Please specify a recognized league such as the English Premier League, La Liga, or NBA."

    league_id, canonical_league = resolved

    # Query lookup table endpoint
    table_url = f"{BASE_URL}/lookuptable.php?l={league_id}"
    table_data = _http_get(table_url)

    if not table_data or not table_data.get("table"):
        return f"Currently, no active standings table is available for {canonical_league}."

    table = table_data["table"]
    top_entries = table[:5]

    standing_snippets = []
    for entry in top_entries:
        rank = entry.get("intRank", "")
        team = entry.get("strTeam", "Unknown")
        points = entry.get("intPoints")
        played = entry.get("intPlayed")

        if points is not None:
            standing_snippets.append(f"{rank}. {team} ({points} pts)")
        elif played is not None:
            standing_snippets.append(f"{rank}. {team} ({played} games)")
        else:
            standing_snippets.append(f"{rank}. {team}")

    standings_summary = ", ".join(standing_snippets)
    return f"Current top standings for {canonical_league}: {standings_summary}."


def get_upcoming_matches(league_name: str, max_matches: int = 5) -> str:
    """Queries upcoming scheduled matches and fixtures for a sports league.

    Args:
        league_name (str): Name of the sports league (e.g., 'English Premier League', 'La Liga', 'NBA', 'NFL', 'Champions League').
        max_matches (int): Maximum number of upcoming fixtures to return (default 5).

    Returns:
        str: Short natural-language summary of upcoming matches and scheduled dates.
    """
    logger.info(f"get_upcoming_matches tool invoked for league: '{league_name}'")
    if not league_name or not league_name.strip():
        return "Please specify a valid league name."

    resolved = _resolve_league_id(league_name)
    if not resolved or not resolved[0]:
        return f"I couldn't find upcoming matches for '{league_name}'. Please specify a recognized league such as the English Premier League, La Liga, or NBA."

    league_id, canonical_league = resolved

    # Query eventsnextleague endpoint
    next_url = f"{BASE_URL}/eventsnextleague.php?id={league_id}"
    next_data = _http_get(next_url)

    if not next_data or not next_data.get("events"):
        return f"No upcoming fixtures or scheduled matches were found for {canonical_league}."

    events = next_data["events"][:max_matches]
    fixture_snippets = []
    for event in events:
        title = event.get("strEvent", "Match")
        date_str = event.get("dateEvent", "")
        time_str = event.get("strTime", "")
        time_part = f" at {time_str[:5]} UTC" if time_str and time_str != "00:00:00" else ""
        if date_str:
            fixture_snippets.append(f"{title} on {date_str}{time_part}")
        else:
            fixture_snippets.append(title)

    fixtures_summary = "; ".join(fixture_snippets)
    return f"Upcoming matches for {canonical_league}: {fixtures_summary}."

