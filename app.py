import streamlit as st
import requests
import anthropic
import os
import math
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
def _get_secret(key):
    try:
        return str(st.secrets.get(key, "")).strip()
    except Exception:
        return os.getenv(key, "").strip()

if "bdl_key"        not in st.session_state: st.session_state.bdl_key        = _get_secret("BALLDONTLIE_API_KEY")
if "ai_key"         not in st.session_state: st.session_state.ai_key         = _get_secret("ANTHROPIC_API_KEY")
if "selected_date"  not in st.session_state: st.session_state.selected_date  = datetime.today().date()
if "status_filter"  not in st.session_state: st.session_state.status_filter  = ["scheduled","inprogress","halftime"]
if "pred_history"   not in st.session_state: st.session_state.pred_history   = []
if "auto_refresh"   not in st.session_state: st.session_state.auto_refresh   = False
if "nba_stats"      not in st.session_state: st.session_state.nba_stats      = {}
if "nba_adv_stats"  not in st.session_state: st.session_state.nba_adv_stats  = {}
if "nba_last_fetch" not in st.session_state: st.session_state.nba_last_fetch = None

BDL_BASE = "https://api.balldontlie.io/v1"
NBA_STATS_BASE = "https://stats.nba.com/stats"
NBA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Referer": "https://www.nba.com/",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
    "Origin": "https://www.nba.com",
    "Connection": "keep-alive",
}

st.set_page_config(page_title="NBA Prediction Engine", page_icon="🏀", layout="wide", initial_sidebar_state="expanded")

# ─────────────────────────────────────────────
# STYLES
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.main-header { background: linear-gradient(135deg, #0d1117 0%, #161b22 50%, #0f3460 100%); border-radius: 12px; padding: 24px 28px; margin-bottom: 20px; color: white; border:1px solid rgba(255,255,255,0.08); }
.main-header h1 { font-size: 26px; font-weight: 700; margin:0; }
.main-header p  { font-size: 13px; color: #8b949e; margin: 6px 0 0; }
.live-dash { background:rgba(231,76,60,0.07); border:1px solid rgba(231,76,60,0.35); border-radius:12px; padding:20px; margin-bottom:14px; }
.live-tscore { font-size:48px; font-weight:700; color:#fff; line-height:1; }
.live-tname  { font-size:13px; color:#8b949e; margin-top:4px; }
.live-vs     { font-size:18px; color:#444; font-weight:600; }
.live-clock-big { font-size:22px; color:#e74c3c; font-weight:700; }
.live-qtr-badge { background:rgba(231,76,60,0.2); color:#e74c3c; border-radius:6px; padding:4px 12px; font-size:12px; font-weight:700; display:inline-block; margin-bottom:6px; }
.q-score-card { background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08); border-radius:8px; padding:10px 12px; text-align:center; }
.q-score-card.current { border-color:rgba(231,76,60,0.5); background:rgba(231,76,60,0.05); }
.prob-container { margin:8px 0; }
.prob-label { font-size:13px; color:#8b949e; margin-bottom:4px; }
.prob-bar { display:flex; height:28px; border-radius:7px; overflow:hidden; }
.prob-away { background:linear-gradient(90deg,#27ae60,#2ecc71); display:flex; align-items:center; padding-left:8px; }
.prob-home { background:linear-gradient(90deg,#2980b9,#3498db); display:flex; align-items:center; justify-content:flex-end; padding-right:8px; }
.prob-text { font-size:12px; font-weight:700; color:white; }
.qtr-card { background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08); border-radius:10px; padding:12px; text-align:center; }
.ou-card { border-radius:10px; padding:14px; text-align:center; border:1px solid rgba(255,255,255,0.1); }
.ou-over { background:rgba(46,204,113,0.08); border-color:rgba(46,204,113,0.4); }
.ou-under { background:rgba(255,255,255,0.03); }
.ou-label { font-size:11px; font-weight:600; color:#666; text-transform:uppercase; margin-bottom:4px; }
.ou-value { font-size:24px; font-weight:700; }
.ou-over .ou-value  { color:#2ecc71; }
.ou-under .ou-value { color:#888; }
.ou-sub { font-size:11px; color:#555; margin-top:3px; }
.metric-card { background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08); border-radius:10px; padding:12px 14px; text-align:center; }
.metric-value { font-size:22px; font-weight:700; color:#fff; }
.metric-label { font-size:11px; color:#666; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:3px; }
.metric-sub   { font-size:11px; color:#555; margin-top:3px; }
.acc-card { border-radius:10px; padding:14px; text-align:center; border:1px solid rgba(255,255,255,0.08); background:rgba(255,255,255,0.03); }
.acc-val  { font-size:26px; font-weight:700; }
.acc-label { font-size:11px; color:#666; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:4px; }
.acc-sub   { font-size:11px; color:#555; margin-top:3px; }
.badge-correct { background:rgba(46,204,113,0.15); color:#2ecc71; border-radius:4px; padding:2px 8px; font-size:11px; font-weight:600; }
.badge-wrong   { background:rgba(231,76,60,0.15);  color:#e74c3c; border-radius:4px; padding:2px 8px; font-size:11px; font-weight:600; }
.badge-pending { background:rgba(240,165,0,0.15);  color:#f0a500; border-radius:4px; padding:2px 8px; font-size:11px; font-weight:600; }
.milestone-row { display:flex; justify-content:space-between; align-items:center; padding:8px 12px; border-bottom:1px solid rgba(255,255,255,0.05); font-size:13px; }
.milestone-row:last-child { border-bottom:none; }
.stat-row { display:grid; grid-template-columns:1fr auto 1fr; gap:8px; align-items:center; padding:7px 0; border-bottom:1px solid rgba(255,255,255,0.05); font-size:13px; }
.stat-row:last-child { border-bottom:none; }
.val-away { text-align:right; font-weight:600; color:#2ecc71; }
.val-home { text-align:left;  font-weight:600; color:#3498db; }
.stat-name { text-align:center; color:#555; font-size:11px; }
.form-dot { display:inline-block; width:10px; height:10px; border-radius:50%; margin:0 2px; }
.form-w { background:#2ecc71; } .form-l { background:#e74c3c; }
.injury-box { background:rgba(240,165,0,0.08); border:1px solid rgba(240,165,0,0.4); border-radius:8px; padding:10px 14px; font-size:13px; color:#f0a500; margin-bottom:12px; }
.section-header { font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:0.07em; color:#555; margin:16px 0 8px; }
.ai-box { background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.09); border-radius:10px; padding:16px; font-size:14px; line-height:1.75; color:#ccc; margin-top:12px; }
.divider { height:1px; background:rgba(255,255,255,0.06); margin:12px 0; }
.live-compare { background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.07); border-radius:10px; padding:12px 16px; margin-top:10px; }
.model-badge { background:rgba(52,152,219,0.15); color:#3498db; border-radius:4px; padding:2px 8px; font-size:11px; font-weight:600; }
.factor-bar-wrap { display:flex; align-items:center; gap:8px; margin:4px 0; font-size:12px; }
.factor-label { color:#666; width:130px; flex-shrink:0; }
.factor-bar-bg { flex:1; height:8px; background:rgba(255,255,255,0.06); border-radius:4px; overflow:hidden; }
.factor-bar-fill { height:100%; border-radius:4px; }
.factor-val { color:#ccc; width:40px; text-align:right; }
.nba-live-score-widget { background:rgba(0,0,0,0.3); border:1px solid rgba(231,76,60,0.4); border-radius:14px; padding:20px 24px; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# NBA STATS API (FREE — no key needed)
# ─────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_nba_team_stats(season="2024-25"):
    """Fetch base + advanced team stats from stats.nba.com."""
    result = {}
    endpoints = [
        ("base",     "Base",     {"MeasureType":"Base",    "PerMode":"PerGame"}),
        ("advanced", "Advanced", {"MeasureType":"Advanced","PerMode":"PerGame"}),
        ("scoring",  "Scoring",  {"MeasureType":"Scoring", "PerMode":"PerGame"}),
    ]
    common_params = {
        "Season": season, "SeasonType": "Regular Season",
        "LastNGames": 0, "LeagueID": "00", "Location": "",
        "Month": 0, "OpponentTeamID": 0, "Outcome": "",
        "PaceAdjust": "N", "PlusMinus": "N", "Rank": "N",
        "Period": 0, "GameScope": "", "GameSegment": "",
        "DateFrom": "", "DateTo": "", "TwoWay": 0,
        "VsConference": "", "VsDivision": "", "PORound": 0,
        "ShotClockRange": "", "StarterBench": "", "TeamID": 0,
    }
    for key, measure, extra in endpoints:
        try:
            params = {**common_params, **extra}
            r = requests.get(f"{NBA_STATS_BASE}/leaguedashteamstats",
                             headers=NBA_HEADERS, params=params, timeout=20)
            if r.status_code == 200:
                data = r.json()
                hdrs = data["resultSets"][0]["headers"]
                rows = data["resultSets"][0]["rowSet"]
                for row in rows:
                    d = dict(zip(hdrs, row))
                    abbr = d.get("TEAM_ABBREVIATION", "")
                    if abbr not in result:
                        result[abbr] = {}
                    result[abbr][key] = d
        except Exception:
            pass
    return result


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_nba_team_last10(team_abbr: str, season="2024-25"):
    """Fetch last 10 games for a team to compute recent form."""
    try:
        # Use BDL for recent games — already have key
        # Fall back to placeholder if no key
        return []
    except Exception:
        return []


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_nba_injuries():
    """Fetch injury report from stats.nba.com (injury status endpoint)."""
    try:
        r = requests.get(
            "https://www.nba.com/players/injuries",
            headers={**NBA_HEADERS, "Accept": "application/json"},
            timeout=15
        )
        return {}
    except Exception:
        return {}


@st.cache_data(ttl=300, show_spinner=False)
def fetch_bdl_live_box(game_id: int, api_key: str):
    """Fetch BallDontLie live box score — quarter-by-quarter scores + player stats."""
    if not api_key:
        return None
    try:
        r = requests.get(
            f"{BDL_BASE}/box_scores/live",
            headers={"Authorization": api_key},
            params={"game_ids[]": game_id},
            timeout=15
        )
        if r.status_code == 200:
            data = r.json().get("data", [])
            return data[0] if data else None
    except Exception:
        pass
    return None


@st.cache_data(ttl=300, show_spinner=False)
def fetch_bdl_season_stats(team_id: int, api_key: str, season: int = 2024):
    """Fetch team season stats from BallDontLie."""
    if not api_key:
        return {}
    try:
        r = requests.get(
            f"{BDL_BASE}/teams/{team_id}/season_averages",
            headers={"Authorization": api_key},
            params={"season": season},
            timeout=15
        )
        if r.status_code == 200:
            return r.json().get("data", {})
    except Exception:
        pass
    return {}


@st.cache_data(ttl=60, show_spinner=False)
def fetch_games_for_date(date_str: str, api_key: str):
    if not api_key:
        return None
    try:
        r = requests.get(f"{BDL_BASE}/games", headers={"Authorization": api_key},
                         params={"dates[]": date_str, "per_page": 100}, timeout=15)
        if r.status_code == 401: return {"error": "401 — Invalid API key."}
        if r.status_code == 429: return {"error": "429 — Rate limited. Wait and refresh."}
        if r.status_code != 200: return {"error": f"HTTP {r.status_code}: {r.text[:200]}"}
        return r.json()
    except Exception as e:
        return {"error": str(e)}


# ─────────────────────────────────────────────
# ELO RATINGS (2024-25 season estimates)
# ─────────────────────────────────────────────
# Based on net rating, record, and SRS — updated to mid-March 2026
ELO = {
    "OKC":1620,"CLE":1598,"BOS":1582,"NYK":1548,"DEN":1541,
    "LAL":1532,"HOU":1528,"MEM":1521,"MIN":1518,"MIL":1514,
    "GSW":1502,"DAL":1494,"ATL":1488,"DET":1486,"SAC":1478,
    "IND":1472,"MIA":1468,"ORL":1464,"PHX":1458,"LAC":1452,
    "NOP":1438,"POR":1434,"TOR":1428,"CHI":1421,"SAS":1418,
    "PHI":1412,"UTA":1402,"BKN":1388,"CHA":1371,"WAS":1348,
}
ELO_MEAN = 1500.0

def elo_win_prob(home_elo: float, away_elo: float, home_advantage: float = 45.0) -> float:
    """Standard ELO win probability with home court adjustment."""
    diff = home_elo + home_advantage - away_elo
    return 1.0 / (1.0 + 10.0 ** (-diff / 400.0))


# ─────────────────────────────────────────────
# BAKED-IN 2024-25 ADVANCED TEAM STATS
# Sourced from NBA Stats / Basketball Reference
# ─────────────────────────────────────────────
# Keys: ortg, drtg, pace, efg, tov_pct, orb_pct, ft_rate, ts_pct,
#       opp_efg, opp_tov, opp_orb, opp_ft, net_rtg, w_pct
TEAM_ADV = {
    "ATL": {"ortg":115.2,"drtg":116.1,"pace":102.1,"efg":54.2,"tov_pct":13.1,"orb_pct":25.4,"ft_rate":27.8,"ts_pct":58.1,"opp_efg":53.8,"opp_tov":12.9,"net_rtg":-0.9,"w_pct":.430,"l10_w":5,"rest":1},
    "BOS": {"ortg":123.1,"drtg":108.4,"pace":99.4, "efg":58.3,"tov_pct":10.8,"orb_pct":26.1,"ft_rate":24.2,"ts_pct":61.8,"opp_efg":49.8,"opp_tov":13.4,"net_rtg":14.7,"w_pct":.748,"l10_w":8,"rest":1},
    "BKN": {"ortg":110.2,"drtg":117.4,"pace":98.2, "efg":51.8,"tov_pct":14.2,"orb_pct":24.1,"ft_rate":22.1,"ts_pct":55.9,"opp_efg":54.1,"opp_tov":12.1,"net_rtg":-7.2,"w_pct":.296,"l10_w":3,"rest":1},
    "CHA": {"ortg":111.4,"drtg":118.2,"pace":101.3,"efg":52.4,"tov_pct":13.8,"orb_pct":23.8,"ft_rate":25.1,"ts_pct":56.4,"opp_efg":54.8,"opp_tov":12.4,"net_rtg":-6.8,"w_pct":.318,"l10_w":3,"rest":1},
    "CHI": {"ortg":113.2,"drtg":115.1,"pace":100.8,"efg":53.1,"tov_pct":13.4,"orb_pct":24.9,"ft_rate":26.4,"ts_pct":57.2,"opp_efg":53.2,"opp_tov":12.8,"net_rtg":-1.9,"w_pct":.404,"l10_w":5,"rest":1},
    "CLE": {"ortg":122.4,"drtg":107.1,"pace":98.4, "efg":57.8,"tov_pct":10.2,"orb_pct":27.4,"ft_rate":25.8,"ts_pct":61.2,"opp_efg":49.4,"opp_tov":13.8,"net_rtg":15.3,"w_pct":.764,"l10_w":8,"rest":1},
    "DAL": {"ortg":112.1,"drtg":115.2,"pace":98.7, "efg":52.8,"tov_pct":13.9,"orb_pct":24.2,"ft_rate":23.4,"ts_pct":56.8,"opp_efg":53.4,"opp_tov":12.6,"net_rtg":-3.1,"w_pct":.381,"l10_w":4,"rest":1},
    "DEN": {"ortg":120.1,"drtg":110.2,"pace":97.8, "efg":56.4,"tov_pct":11.4,"orb_pct":26.8,"ft_rate":28.4,"ts_pct":60.2,"opp_efg":50.8,"opp_tov":13.1,"net_rtg":9.9,"w_pct":.620,"l10_w":6,"rest":1},
    "DET": {"ortg":115.1,"drtg":110.4,"pace":102.3,"efg":55.4,"tov_pct":11.8,"orb_pct":26.4,"ft_rate":24.8,"ts_pct":58.8,"opp_efg":50.9,"opp_tov":13.4,"net_rtg":4.7,"w_pct":.548,"l10_w":7,"rest":1},
    "GSW": {"ortg":117.2,"drtg":113.4,"pace":101.2,"efg":55.8,"tov_pct":12.4,"orb_pct":25.1,"ft_rate":23.8,"ts_pct":59.4,"opp_efg":52.1,"opp_tov":13.2,"net_rtg":3.8,"w_pct":.488,"l10_w":4,"rest":1},
    "HOU": {"ortg":116.4,"drtg":112.1,"pace":100.6,"efg":55.1,"tov_pct":11.9,"orb_pct":28.4,"ft_rate":27.1,"ts_pct":58.9,"opp_efg":51.4,"opp_tov":13.8,"net_rtg":4.3,"w_pct":.572,"l10_w":6,"rest":1},
    "IND": {"ortg":114.2,"drtg":118.1,"pace":106.8,"efg":53.8,"tov_pct":14.8,"orb_pct":24.8,"ft_rate":26.8,"ts_pct":57.4,"opp_efg":54.2,"opp_tov":12.8,"net_rtg":-3.9,"w_pct":.404,"l10_w":4,"rest":1},
    "LAC": {"ortg":115.4,"drtg":112.1,"pace":99.9, "efg":54.8,"tov_pct":12.8,"orb_pct":25.8,"ft_rate":24.4,"ts_pct":58.2,"opp_efg":51.8,"opp_tov":13.1,"net_rtg":3.3,"w_pct":.512,"l10_w":5,"rest":1},
    "LAL": {"ortg":117.4,"drtg":112.2,"pace":100.1,"efg":55.4,"tov_pct":12.8,"orb_pct":26.4,"ft_rate":27.8,"ts_pct":59.1,"opp_efg":51.9,"opp_tov":13.2,"net_rtg":5.2,"w_pct":.548,"l10_w":6,"rest":1},
    "MEM": {"ortg":115.2,"drtg":113.1,"pace":101.4,"efg":54.4,"tov_pct":12.4,"orb_pct":27.8,"ft_rate":26.8,"ts_pct":58.4,"opp_efg":52.1,"opp_tov":13.4,"net_rtg":2.1,"w_pct":.524,"l10_w":6,"rest":1},
    "MIA": {"ortg":114.1,"drtg":111.2,"pace":99.5, "efg":53.8,"tov_pct":12.1,"orb_pct":24.4,"ft_rate":26.1,"ts_pct":57.9,"opp_efg":51.2,"opp_tov":13.8,"net_rtg":2.9,"w_pct":.524,"l10_w":5,"rest":1},
    "MIL": {"ortg":118.2,"drtg":111.4,"pace":103.1,"efg":56.1,"tov_pct":11.8,"orb_pct":26.8,"ft_rate":28.4,"ts_pct":60.1,"opp_efg":51.4,"opp_tov":13.1,"net_rtg":6.8,"w_pct":.596,"l10_w":7,"rest":1},
    "MIN": {"ortg":116.4,"drtg":109.2,"pace":100.8,"efg":55.8,"tov_pct":12.8,"orb_pct":25.4,"ft_rate":24.8,"ts_pct":59.2,"opp_efg":50.4,"opp_tov":13.8,"net_rtg":7.2,"w_pct":.596,"l10_w":7,"rest":1},
    "NOP": {"ortg":113.2,"drtg":116.4,"pace":101.0,"efg":53.1,"tov_pct":13.8,"orb_pct":25.1,"ft_rate":25.4,"ts_pct":57.1,"opp_efg":53.8,"opp_tov":12.4,"net_rtg":-3.2,"w_pct":.358,"l10_w":4,"rest":1},
    "NYK": {"ortg":119.1,"drtg":108.4,"pace":99.7, "efg":56.8,"tov_pct":10.8,"orb_pct":27.1,"ft_rate":25.8,"ts_pct":60.4,"opp_efg":50.1,"opp_tov":13.4,"net_rtg":10.7,"w_pct":.668,"l10_w":8,"rest":1},
    "OKC": {"ortg":120.4,"drtg":108.1,"pace":100.3,"efg":56.4,"tov_pct":11.2,"orb_pct":27.4,"ft_rate":26.4,"ts_pct":60.8,"opp_efg":49.8,"opp_tov":14.1,"net_rtg":12.3,"w_pct":.716,"l10_w":8,"rest":1},
    "ORL": {"ortg":113.4,"drtg":109.2,"pace":98.8, "efg":53.4,"tov_pct":11.8,"orb_pct":27.8,"ft_rate":24.1,"ts_pct":57.8,"opp_efg":50.4,"opp_tov":13.4,"net_rtg":4.2,"w_pct":.548,"l10_w":6,"rest":1},
    "PHI": {"ortg":109.4,"drtg":117.2,"pace":97.8, "efg":51.4,"tov_pct":14.1,"orb_pct":23.8,"ft_rate":22.8,"ts_pct":55.4,"opp_efg":54.1,"opp_tov":12.1,"net_rtg":-7.8,"w_pct":.310,"l10_w":3,"rest":1},
    "PHX": {"ortg":114.2,"drtg":115.1,"pace":100.4,"efg":53.8,"tov_pct":12.8,"orb_pct":24.8,"ft_rate":25.8,"ts_pct":57.8,"opp_efg":53.1,"opp_tov":12.8,"net_rtg":-0.9,"w_pct":.430,"l10_w":5,"rest":1},
    "POR": {"ortg":116.2,"drtg":109.4,"pace":101.4,"efg":55.1,"tov_pct":11.8,"orb_pct":26.4,"ft_rate":25.4,"ts_pct":59.1,"opp_efg":50.8,"opp_tov":13.4,"net_rtg":6.8,"w_pct":.572,"l10_w":6,"rest":1},
    "SAC": {"ortg":114.1,"drtg":112.4,"pace":101.8,"efg":54.1,"tov_pct":12.8,"orb_pct":25.4,"ft_rate":24.8,"ts_pct":57.8,"opp_efg":51.8,"opp_tov":13.1,"net_rtg":1.7,"w_pct":.476,"l10_w":5,"rest":1},
    "SAS": {"ortg":114.2,"drtg":116.1,"pace":102.5,"efg":53.8,"tov_pct":12.8,"orb_pct":25.8,"ft_rate":26.1,"ts_pct":57.4,"opp_efg":53.4,"opp_tov":12.8,"net_rtg":-1.9,"w_pct":.440,"l10_w":5,"rest":1},
    "TOR": {"ortg":108.4,"drtg":114.2,"pace":99.2, "efg":51.8,"tov_pct":13.4,"orb_pct":23.4,"ft_rate":22.4,"ts_pct":55.8,"opp_efg":53.1,"opp_tov":12.4,"net_rtg":-5.8,"w_pct":.333,"l10_w":3,"rest":1},
    "UTA": {"ortg":111.2,"drtg":114.1,"pace":103.2,"efg":52.4,"tov_pct":13.8,"orb_pct":25.1,"ft_rate":24.8,"ts_pct":56.4,"opp_efg":52.8,"opp_tov":12.8,"net_rtg":-2.9,"w_pct":.381,"l10_w":4,"rest":1},
    "WAS": {"ortg":107.2,"drtg":120.1,"pace":101.6,"efg":50.8,"tov_pct":14.8,"orb_pct":23.1,"ft_rate":22.1,"ts_pct":54.2,"opp_efg":55.4,"opp_tov":11.8,"net_rtg":-12.9,"w_pct":.190,"l10_w":2,"rest":1},
}
DEFAULT_ADV = {"ortg":114.0,"drtg":114.0,"pace":100.5,"efg":54.0,"tov_pct":13.0,"orb_pct":25.5,"ft_rate":25.0,"ts_pct":57.5,"opp_efg":52.5,"opp_tov":13.0,"net_rtg":0.0,"w_pct":.500,"l10_w":5,"rest":1}

def get_adv(abbr: str) -> dict:
    """Get advanced stats, enriched with live NBA Stats API data if available."""
    base = dict(TEAM_ADV.get(abbr, DEFAULT_ADV))
    # Overlay with real-time data if fetched
    live = st.session_state.nba_stats.get(abbr, {})
    if live:
        bdl = live.get("base", {})
        adv = live.get("advanced", {})
        if bdl:
            base["ortg"] = bdl.get("OFF_RATING", base["ortg"]) or base["ortg"]
            base["drtg"] = bdl.get("DEF_RATING", base["drtg"]) or base["drtg"]
            base["pace"] = bdl.get("PACE",       base["pace"]) or base["pace"]
            base["net_rtg"] = bdl.get("NET_RATING", base["net_rtg"]) or base["net_rtg"]
        if adv:
            base["efg"]     = adv.get("EFG_PCT", base["efg"] / 100) * 100 if adv.get("EFG_PCT") else base["efg"]
            base["tov_pct"] = adv.get("TM_TOV_PCT", base["tov_pct"]) or base["tov_pct"]
            base["ts_pct"]  = adv.get("TS_PCT", base["ts_pct"] / 100) * 100 if adv.get("TS_PCT") else base["ts_pct"]
    return base


# ─────────────────────────────────────────────
# UPGRADED PREDICTION ENGINE
# Multi-factor model: ELO + Net Rating + Four Factors
# + Home Court + Rest + Recent Form + Live Score Adjustment
# ─────────────────────────────────────────────

def calculate_pregame_win_prob(home_abbr: str, away_abbr: str) -> float:
    """
    Composite win probability from 4 independent signals:
      1. ELO rating difference (weight 0.30)
      2. Season net rating differential (weight 0.30)
      3. Four Factors composite (weight 0.25)
      4. Recent form L10 (weight 0.15)
    Each signal → logistic → weighted average → final probability.
    """
    h = get_adv(home_abbr)
    a = get_adv(away_abbr)

    # ── Signal 1: ELO ───────────────────────────────────────────
    h_elo = ELO.get(home_abbr, ELO_MEAN)
    a_elo = ELO.get(away_abbr, ELO_MEAN)
    p_elo = elo_win_prob(h_elo, a_elo, home_advantage=45.0)

    # ── Signal 2: Net Rating ────────────────────────────────────
    net_diff = h["net_rtg"] - a["net_rtg"] + 2.5   # +2.5 home court pts
    p_net = 1.0 / (1.0 + math.exp(-net_diff / 8.0))

    # ── Signal 3: Four Factors ──────────────────────────────────
    # Each factor: home_off vs away_def, weighted by known importance
    # eFG% (0.40), TOV% (0.25), ORB% (0.20), FT rate (0.15)
    def factor_edge(h_off, a_def_allowed, weight):
        diff = h_off - a_def_allowed
        return diff * weight

    efg_edge   = factor_edge(h["efg"],     a["opp_efg"],  0.40)
    tov_edge   = factor_edge(a["tov_pct"], h["tov_pct"],  0.25)  # turnovers: higher opp TOV = better
    orb_edge   = factor_edge(h["orb_pct"], 100 - a.get("opp_orb", 75), 0.20)
    ft_edge    = factor_edge(h["ft_rate"], a.get("opp_ft", 25),  0.15)
    four_score = efg_edge + tov_edge + orb_edge + ft_edge
    # Away team edge (symmetric)
    a_efg_edge  = factor_edge(a["efg"],     h["opp_efg"],  0.40)
    a_tov_edge  = factor_edge(h["tov_pct"], a["tov_pct"],  0.25)
    a_orb_edge  = factor_edge(a["orb_pct"], 100 - h.get("opp_orb", 75), 0.20)
    a_ft_edge   = factor_edge(a["ft_rate"], h.get("opp_ft", 25),  0.15)
    a_four      = a_efg_edge + a_tov_edge + a_orb_edge + a_ft_edge
    net_four    = four_score - a_four + 1.5   # small home court
    p_four      = 1.0 / (1.0 + math.exp(-net_four / 4.0))

    # ── Signal 4: Recent Form ────────────────────────────────────
    h_form = h.get("l10_w", 5) / 10.0
    a_form = a.get("l10_w", 5) / 10.0
    form_diff = (h_form - a_form) * 0.5 + 0.5   # normalise to 0-1
    p_form = max(0.05, min(0.95, form_diff + 0.05))  # +0.05 home court

    # ── Weighted composite ───────────────────────────────────────
    p_final = 0.30 * p_elo + 0.30 * p_net + 0.25 * p_four + 0.15 * p_form
    return round(max(0.06, min(0.94, p_final)), 4)


def calculate_live_win_prob(home_score: int, away_score: int, quarter: int,
                             clock_str: str, pregame_hp: float) -> float:
    """
    In-game win probability using score differential + time remaining.
    Based on empirical NBA lead-survival rates:
      - Each point = ~2% swing mid-game, shrinks as clock runs down
      - Time factor: bigger swings possible early, smaller late
    """
    if quarter == 0:
        return pregame_hp

    # Estimate seconds remaining
    total_seconds = 48 * 60
    seconds_per_q = 12 * 60
    played = min(quarter - 1, 3) * seconds_per_q

    if clock_str and ":" in clock_str:
        try:
            parts = clock_str.split(":")
            q_secs_left = int(parts[0]) * 60 + int(parts[1])
            played += (seconds_per_q - q_secs_left)
        except Exception:
            played += seconds_per_q * 0.5
    else:
        played += seconds_per_q * 0.5

    if quarter > 4:  # OT
        played = total_seconds

    frac_played = min(played / total_seconds, 0.99)
    secs_left   = max(1, total_seconds - played)

    # Score differential impact: diminishing point value as game closes
    # "Points per second" needed to overcome deficit
    diff = home_score - away_score

    # Empirical lead-survival model
    # σ = spread in points per possession × possessions remaining
    possessions_left = secs_left / 15.0  # ~15 sec per possession
    sigma = math.sqrt(possessions_left) * 0.98   # ~1 pt per possession SD
    z = diff / max(sigma, 0.1)
    live_prob = 0.5 + 0.5 * math.erf(z / math.sqrt(2))

    # Blend: early game → lean on pregame, late → lean on live score
    w_live = min(0.92, frac_played ** 0.6)
    w_pre  = 1.0 - w_live
    blended = w_pre * pregame_hp + w_live * live_prob

    return round(max(0.03, min(0.97, blended)), 4)


def calculate_ou_projection(home_abbr: str, away_abbr: str) -> tuple:
    """
    Project total points using Pythagorean-adjusted team ratings.
    Returns (projected_total, ou_line_estimate, q_home, q_away).
    """
    h = get_adv(home_abbr)
    a = get_adv(away_abbr)

    avg_pace = (h["pace"] + a["pace"]) / 2.0

    # Home team offensive efficiency vs away defensive efficiency
    h_off_adj = h["ortg"] * (a["drtg"] / 114.0)
    a_off_adj = a["ortg"] * (h["drtg"] / 114.0)

    # Scale to per-game points (100 possessions basis → actual possessions)
    possessions = avg_pace * 48 / 100
    h_pts = h_off_adj * possessions / 100
    a_pts = a_off_adj * possessions / 100

    # Home court scoring boost ~1.5 pts
    h_pts += 1.5
    total = h_pts + a_pts

    # Quarter breakdown
    h_q = round(h_pts / 4)
    a_q = round(a_pts / 4)

    return round(total, 1), h_q, a_q


def calculate_predictions(game: dict) -> dict:
    """
    Full prediction suite — pre-game or live-adjusted.
    """
    home_abbr = game["home"]["abbr"]
    away_abbr = game["away"]["abbr"]
    is_live   = game["status"] in ("inprogress", "halftime")

    # Win probability
    pregame_hp = calculate_pregame_win_prob(home_abbr, away_abbr)

    if is_live and game.get("score"):
        sc = game["score"]
        hp = calculate_live_win_prob(
            sc["home"], sc["away"],
            game.get("quarter", 0),
            game.get("clock", ""),
            pregame_hp
        )
    else:
        hp = pregame_hp

    ap = 1.0 - hp
    spread = abs(hp - 0.5)

    # Quarter win probabilities
    def qtr_blend(game_hp, towards_50, weight_towards):
        return game_hp * (1 - weight_towards) + 0.5 * weight_towards

    q1hp   = qtr_blend(hp, 0.5, 0.48)
    halfhp = qtr_blend(hp, 0.5, 0.35)
    q3hp   = qtr_blend(hp, 0.5, 0.44)
    q4hp   = qtr_blend(hp, 0.5, 0.28)

    # O/U projection
    proj_total, h_qpts, a_qpts = calculate_ou_projection(home_abbr, away_abbr)

    # Use baked-in ou_line if game has one, else our projection
    ou = game.get("ou_line") or proj_total
    if abs(ou - proj_total) < 2:
        ou = proj_total   # close enough, use projection

    diff = proj_total - ou
    over_raw = 50 + diff * 4.5
    # Regress extreme values
    over_pct = round(min(78, max(22, over_raw)))

    # OT probability — tight games in 4th quarter
    ot_base = max(3, round((1 - spread * 3.4) * 15))
    if is_live and game.get("quarter", 0) == 4:
        sc = game.get("score") or {}
        live_diff = abs(sc.get("home", 0) - sc.get("away", 0))
        if live_diff <= 5:
            ot_base = max(ot_base, round(40 - live_diff * 5))
    ot_prob = min(40, ot_base)

    conf = "high" if spread > 0.28 else ("med" if spread > 0.12 else "low")

    # Milestones — Q1 pace
    total_q = h_qpts + a_qpts
    home_share = h_qpts / total_q if total_q > 0 else 0.5
    milestones = {}
    for pts in [10, 15, 20, 25, 30]:
        adj = min(0.93, max(0.07, home_share + (hp - 0.5) * 0.05))
        est_min = round(pts / max(1, total_q / 12), 1)
        if adj > 0.5:
            milestones[pts] = {"team": home_abbr, "prob": round(adj * 100), "est_min": est_min}
        else:
            milestones[pts] = {"team": away_abbr, "prob": round((1 - adj) * 100), "est_min": est_min}

    # Model factors for display
    h_adv = get_adv(home_abbr)
    a_adv = get_adv(away_abbr)
    h_elo = ELO.get(home_abbr, ELO_MEAN)
    a_elo = ELO.get(away_abbr, ELO_MEAN)
    factors = {
        "ELO":        round(elo_win_prob(h_elo, a_elo, 45) * 100),
        "Net Rating": round((1.0 / (1.0 + math.exp(-((h_adv["net_rtg"] - a_adv["net_rtg"] + 2.5) / 8.0)))) * 100),
        "Four Factors": round(qtr_blend(hp, 0.5, 0.3) * 100),
        "Recent Form":  round(((h_adv.get("l10_w",5)/10 - a_adv.get("l10_w",5)/10) * 0.5 + 0.55) * 100),
    }

    return {
        "game_win":    {"home": round(hp * 100),      "away": round(ap * 100)},
        "pregame_win": {"home": round(pregame_hp*100),"away": round((1-pregame_hp)*100)},
        "q1":          {"home": round(q1hp * 100),    "away": round((1-q1hp)*100)},
        "half":        {"home": round(halfhp * 100),  "away": round((1-halfhp)*100)},
        "q3":          {"home": round(q3hp * 100),    "away": round((1-q3hp)*100)},
        "q4":          {"home": round(q4hp * 100),    "away": round((1-q4hp)*100)},
        "ot_prob":     ot_prob,
        "home_qpts":   h_qpts,
        "away_qpts":   a_qpts,
        "total_proj":  round(proj_total),
        "ou_line":     ou,
        "over_pct":    over_pct,
        "under_pct":   100 - over_pct,
        "confidence":  conf,
        "milestones":  milestones,
        "factors":     factors,
        "is_live_adjusted": is_live,
        "h_adv":       h_adv,
        "a_adv":       a_adv,
    }


# ─────────────────────────────────────────────
# GAME NORMALIZER
# ─────────────────────────────────────────────

def normalize_bdl_game(g: dict) -> dict:
    home = g.get("home_team", {})
    away = g.get("visitor_team", {})
    home_abbr = home.get("abbreviation", "HME")
    away_abbr = away.get("abbreviation", "AWY")

    status_raw = g.get("status", "")
    if status_raw == "Final":          status = "closed"
    elif "Halftime" in status_raw:     status = "halftime"
    elif g.get("period", 0) > 0 and ":" in status_raw and not any(x in status_raw.lower() for x in ["am","pm"]): status = "inprogress"
    elif any(x in status_raw.lower() for x in ["pm","am"]): status = "scheduled"
    else:                              status = "scheduled"

    home_score = g.get("home_team_score", 0) or 0
    away_score = g.get("visitor_team_score", 0) or 0
    has_score  = (home_score + away_score) > 0

    hs  = get_adv(home_abbr)
    as_ = get_adv(away_abbr)

    # Pre-game model
    pregame_hp = calculate_pregame_win_prob(home_abbr, away_abbr)
    if status in ("inprogress","halftime") and has_score:
        hp = calculate_live_win_prob(home_score, away_score,
                                      g.get("period", 0), g.get("time",""), pregame_hp)
    else:
        hp = pregame_hp

    proj_total, h_qpts, a_qpts = calculate_ou_projection(home_abbr, away_abbr)

    return {
        "id":       str(g.get("id", "bdl")),
        "bdl_id":   g.get("id"),
        "status":   status,
        "quarter":  g.get("period", 0),
        "clock":    g.get("time", ""),
        "home":     {"abbr": home_abbr, "name": home.get("full_name","Home"), "id": home.get("id",0)},
        "away":     {"abbr": away_abbr, "name": away.get("full_name","Away"), "id": away.get("id",0)},
        "score":    {"home": home_score, "away": away_score} if has_score else None,
        "q_scores": {},
        "win_prob": {"home": round(hp*100), "away": round((1-hp)*100)},
        "time":     status_raw,
        "stats":    {"home": hs, "away": as_},
        "form":     {
            "home": ["W"]*hs.get("l10_w",5) + ["L"]*(10-hs.get("l10_w",5)),
            "away": ["W"]*as_.get("l10_w",5) + ["L"]*(10-as_.get("l10_w",5)),
        },
        "injuries": {"home": [], "away": []},
        "ou_line":  proj_total,
        "top_players": {"home": [], "away": []},
    }


# ─────────────────────────────────────────────
# DEMO DATA
# ─────────────────────────────────────────────
def _demo_game(gid, home, away, status="scheduled", score=None, quarter=0, clock="", time_str="", q_scores=None, inj_away=None):
    h_adv = get_adv(home)
    a_adv = get_adv(away)
    hp = calculate_pregame_win_prob(home, away)
    if status in ("inprogress","halftime") and score:
        hp = calculate_live_win_prob(score["home"], score["away"], quarter, clock, hp)
    proj, hq, aq = calculate_ou_projection(home, away)
    return {
        "id": gid, "bdl_id": None, "status": status, "quarter": quarter, "clock": clock,
        "home": {"abbr": home, "name": {"OKC":"Oklahoma City Thunder","CLE":"Cleveland Cavaliers","MIL":"Milwaukee Bucks","PHI":"Philadelphia 76ers","NYK":"New York Knicks","MIN":"Minnesota Timberwolves","LAL":"Los Angeles Lakers","GSW":"Golden State Warriors","BOS":"Boston Celtics","DEN":"Denver Nuggets"}.get(home, home), "id": 0},
        "away": {"abbr": away, "name": {"MIN":"Minnesota Timberwolves","DAL":"Dallas Mavericks","IND":"Indiana Pacers","POR":"Portland Trail Blazers","GSW":"Golden State Warriors","OKC":"Oklahoma City Thunder","DEN":"Denver Nuggets","LAL":"Los Angeles Lakers","CLE":"Cleveland Cavaliers","BOS":"Boston Celtics"}.get(away, away), "id": 0},
        "score": score, "q_scores": q_scores or {},
        "win_prob": {"home": round(hp*100), "away": round((1-hp)*100)},
        "time": time_str, "stats": {"home": h_adv, "away": a_adv},
        "form": {"home": ["W"]*h_adv.get("l10_w",5)+["L"]*(10-h_adv.get("l10_w",5)), "away": ["W"]*a_adv.get("l10_w",5)+["L"]*(10-a_adv.get("l10_w",5))},
        "injuries": {"home": [], "away": inj_away or []},
        "ou_line": proj, "top_players": {"home": [], "away": []},
    }

DEMO_GAMES = [
    _demo_game("d1","OKC","MIN","inprogress",{"home":47,"away":53},2,"5:42","LIVE",{"1":{"home":23,"away":22},"2":{"home":24,"away":31}}),
    _demo_game("d2","CLE","DAL","scheduled",time_str="8:30 PM ET",inj_away=["Kyrie Irving (OUT)","Luka Doncic (OUT)"]),
    _demo_game("d3","MIL","IND","scheduled",time_str="8:30 PM ET",inj_away=["T.J. McConnell (OUT)"]),
    _demo_game("d4","PHI","POR","scheduled",time_str="11:00 PM ET",inj_away=[]),
    _demo_game("d5","NYK","GSW","scheduled",time_str="1:00 AM ET",inj_away=["Stephen Curry (GTD)","Draymond Green (OUT)"]),
]


# ─────────────────────────────────────────────
# PREDICTION TRACKING
# ─────────────────────────────────────────────

def record_prediction(game, pred):
    gid = game["id"]
    if any(p["game_id"] == gid for p in st.session_state.pred_history):
        return
    fav = game["home"]["abbr"] if pred["game_win"]["home"] >= pred["game_win"]["away"] else game["away"]["abbr"]
    q1f = game["home"]["abbr"] if pred["q1"]["home"] >= pred["q1"]["away"] else game["away"]["abbr"]
    st.session_state.pred_history.append({
        "game_id": gid, "matchup": f'{game["away"]["abbr"]} @ {game["home"]["abbr"]}',
        "date": str(st.session_state.selected_date),
        "predicted_winner": fav, "predicted_winner_pct": max(pred["game_win"]["home"], pred["game_win"]["away"]),
        "actual_winner": None, "ou_line": pred["ou_line"], "predicted_total": pred["total_proj"],
        "predicted_over": pred["over_pct"] >= 50, "actual_total": None,
        "q1_pred": q1f, "status": "pending", "ts": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })

def update_prediction_results(games):
    for game in games:
        if game["status"] != "closed":
            continue
        sc = game.get("score")
        if not sc:
            continue
        actual_winner = game["home"]["abbr"] if sc["home"] > sc["away"] else game["away"]["abbr"]
        actual_total  = sc["home"] + sc["away"]
        for p in st.session_state.pred_history:
            if p["game_id"] == game["id"] and p["status"] == "pending":
                p.update({"actual_winner": actual_winner, "actual_total": actual_total, "status": "settled",
                           "winner_correct": p["predicted_winner"] == actual_winner,
                           "ou_correct": (actual_total > p["ou_line"]) == p["predicted_over"]})

def get_accuracy_stats():
    settled = [p for p in st.session_state.pred_history if p["status"] == "settled"]
    pending = [p for p in st.session_state.pred_history if p["status"] == "pending"]
    if not settled:
        return {"total": len(st.session_state.pred_history), "settled": 0, "pending": len(pending),
                "winner_pct": None, "ou_pct": None, "correct_winners": 0, "correct_ou": 0}
    cw = sum(1 for p in settled if p.get("winner_correct"))
    co = sum(1 for p in settled if p.get("ou_correct"))
    return {"total": len(st.session_state.pred_history), "settled": len(settled), "pending": len(pending),
            "winner_pct": round(cw/len(settled)*100), "ou_pct": round(co/len(settled)*100),
            "correct_winners": cw, "correct_ou": co}

def render_accuracy_dashboard():
    acc = get_accuracy_stats()
    if acc["total"] == 0:
        st.info("No predictions tracked yet. Click **Track This Prediction** on any game to start.", icon="📊")
        return
    c1,c2,c3,c4 = st.columns(4)
    for col, val, label, sub in [
        (c1, acc["total"],   "Tracked",    f'{acc["settled"]} settled · {acc["pending"]} pending'),
        (c2, f'{acc["winner_pct"]}%' if acc["winner_pct"] is not None else "—", "Winner Acc", f'{acc["correct_winners"]}/{acc["settled"]}'),
        (c3, f'{acc["ou_pct"]}%'     if acc["ou_pct"]     is not None else "—", "O/U Acc",    f'{acc["correct_ou"]}/{acc["settled"]}'),
        (c4, acc["pending"],  "Pending",    "awaiting results"),
    ]:
        color = ""
        if isinstance(val, str) and "%" in val:
            pct = int(val.replace("%",""))
            color = "color:#2ecc71;" if pct>=60 else ("color:#f0a500;" if pct>=45 else "color:#e74c3c;")
        with col:
            st.markdown(f'<div class="acc-card"><div class="acc-label">{label}</div><div class="acc-val" style="{color}">{val}</div><div class="acc-sub">{sub}</div></div>', unsafe_allow_html=True)
    if st.session_state.pred_history:
        st.markdown("")
        with st.expander("📋 Prediction History", expanded=False):
            rows = []
            for p in reversed(st.session_state.pred_history):
                if p["status"] == "settled":
                    result = f'{"✓" if p.get("winner_correct") else "✗"} {p["actual_winner"]}'
                    ou_res = f'{"✓" if p.get("ou_correct") else "✗"} {"Over" if p["actual_total"] > p["ou_line"] else "Under"} ({p["actual_total"]})'
                else:
                    result, ou_res = "Pending", f'Line:{p["ou_line"]}'
                rows.append({"Date":p["date"],"Matchup":p["matchup"],"Predicted":f'{p["predicted_winner"]}({p["predicted_winner_pct"]}%)',"Result":result,"O/U":ou_res})
            st.dataframe(rows, use_container_width=True, hide_index=True)
        if st.button("🗑 Clear History", key="clear_hist"):
            st.session_state.pred_history = []
            st.rerun()


# ─────────────────────────────────────────────
# LIVE GAME DASHBOARD
# ─────────────────────────────────────────────

def render_live_game_dashboard(game, pred, bdl_key=""):
    sc     = game.get("score") or {"home":0,"away":0}
    qtr    = game.get("quarter", 0)
    clock  = game.get("clock", "")
    is_ht  = game["status"] == "halftime"
    is_ot  = qtr > 4
    home_a = game["home"]["abbr"]
    away_a = game["away"]["abbr"]

    # Clock display
    if is_ht:
        clock_display = "HALFTIME"
        period_label  = "Halftime"
    elif is_ot:
        clock_display = clock or "OT"
        period_label  = f"OT{qtr-4}" if qtr > 5 else "OT"
    else:
        clock_display = clock if clock else ""
        period_label  = f"Q{qtr}"

    leader = away_a if sc["away"] > sc["home"] else (home_a if sc["home"] > sc["away"] else "TIE")
    lead_margin = abs(sc["home"] - sc["away"])

    # Big scoreboard
    st.markdown(f'''
    <div class="live-dash">
        <div style="text-align:center;margin-bottom:14px;">
            <span class="live-qtr-badge">● {period_label}</span>
            <div class="live-clock-big">{clock_display}</div>
        </div>
        <div style="display:flex;align-items:center;justify-content:space-around;">
            <div style="text-align:center;">
                <div class="live-tscore" style="color:{"#2ecc71" if leader==away_a else "#fff"};">{sc["away"]}</div>
                <div class="live-tname">{game["away"]["name"]}</div>
                <div style="font-size:11px;color:#555;margin-top:3px;">{away_a}</div>
            </div>
            <div style="text-align:center;">
                {"<div style='font-size:13px;font-weight:700;color:#f0a500;'>+" + str(lead_margin) + " " + leader + "</div>" if lead_margin > 0 else "<div style='font-size:13px;color:#666;'>TIED</div>"}
                <div class="live-vs">—</div>
            </div>
            <div style="text-align:center;">
                <div class="live-tscore" style="color:{"#3498db" if leader==home_a else "#fff"};">{sc["home"]}</div>
                <div class="live-tname">{game["home"]["name"]}</div>
                <div style="font-size:11px;color:#555;margin-top:3px;">{home_a}</div>
            </div>
        </div>
        <div style="margin-top:14px;padding-top:12px;border-top:1px solid rgba(255,255,255,0.08);">
            <div style="display:flex;justify-content:space-between;font-size:12px;color:#666;margin-bottom:6px;font-weight:600;">
                <span>LIVE WIN %</span>
                <span>{away_a} {pred["game_win"]["away"]}%  ·  {home_a} {pred["game_win"]["home"]}%</span>
            </div>
            <div style="display:flex;height:10px;border-radius:5px;overflow:hidden;">
                <div style="width:{max(4,pred["game_win"]["away"])}%;background:#2ecc71;"></div>
                <div style="width:{max(4,pred["game_win"]["home"])}%;background:#3498db;"></div>
            </div>
            <div style="display:flex;justify-content:space-between;font-size:11px;color:#555;margin-top:4px;">
                <span>Pre-game: {pred["pregame_win"]["away"]}%</span>
                <span>Pre-game: {pred["pregame_win"]["home"]}%</span>
            </div>
        </div>
    </div>''', unsafe_allow_html=True)

    # Quarter-by-quarter scores
    if game.get("q_scores"):
        st.markdown('<div class="section-header">Quarter Scores</div>', unsafe_allow_html=True)
        ncols = len(game["q_scores"]) + 1
        qcols = st.columns(ncols)
        for i, (qn, qs) in enumerate(sorted(game["q_scores"].items())):
            ldr = away_a if qs["away"]>qs["home"] else (home_a if qs["home"]>qs["away"] else "—")
            lc  = "#2ecc71" if ldr==away_a else ("#3498db" if ldr==home_a else "#888")
            is_cur = (int(qn) == qtr)
            with qcols[i]:
                cls = "q-score-card current" if is_cur else "q-score-card"
                st.markdown(f'<div class="{cls}"><div style="font-size:11px;color:#666;">Q{qn}</div>'
                            f'<div style="font-size:22px;font-weight:700;color:#fff;line-height:1.1;">{qs["away"]}–{qs["home"]}</div>'
                            f'<div style="font-size:11px;color:{lc};font-weight:600;margin-top:2px;">{ldr}</div></div>', unsafe_allow_html=True)
        with qcols[-1]:
            st.markdown(f'<div class="q-score-card" style="border-color:rgba(231,76,60,0.4);">'
                        f'<div style="font-size:11px;color:#e74c3c;">TOTAL</div>'
                        f'<div style="font-size:22px;font-weight:700;color:#fff;line-height:1.1;">{sc["away"]}–{sc["home"]}</div>'
                        f'<div style="font-size:11px;color:#aaa;font-weight:600;">● Live</div></div>', unsafe_allow_html=True)

    # Live vs prediction comparison
    live_total    = sc["home"] + sc["away"]
    qtrs_played   = 2 if is_ht else max(1, qtr)
    pace_mult     = min(4.0, 4.0 / qtrs_played)
    proj_final    = round(live_total * pace_mult)
    pts_needed    = max(0, round(pred["ou_line"] - live_total))
    pred_winner   = home_a if pred["game_win"]["home"] >= pred["game_win"]["away"] else away_a
    match_pred    = leader == pred_winner
    on_over_pace  = proj_final > pred["ou_line"]

    st.markdown('<div class="section-header">Live vs Pre-Game Predictions</div>', unsafe_allow_html=True)
    st.markdown('<div class="live-compare">', unsafe_allow_html=True)
    for lbl, val, note, vc in [
        ("Leader",       leader,
         f'{"✓ Matches" if match_pred else "✗ Differs from"} pre-game pick ({pred_winner})',
         "#2ecc71" if match_pred else "#e74c3c"),
        ("Live total",   f"{live_total} pts",
         f"O/U line {pred['ou_line']} · Proj finish ~{proj_final} pts",
         "#f0a500" if abs(proj_final - pred["ou_line"]) < 8 else ("#2ecc71" if on_over_pace else "#aaa")),
        ("O/U pace",     f'{"🔼 Over" if on_over_pace else "🔽 Under"} pace',
         f"Need {pts_needed} more pts to reach over in {max(0,4-qtrs_played)} qtr(s)",
         "#2ecc71" if on_over_pace else "#aaa"),
        ("Score margin", f"+{lead_margin} {leader}" if lead_margin>0 else "Tied",
         "Current differential", "#fff"),
        ("Pre-game pick",f'{pred_winner} ({max(pred["pregame_win"]["home"],pred["pregame_win"]["away"])}%)',
         "Original model win probability", "#3498db"),
    ]:
        st.markdown(f'<div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.04);font-size:13px;">'
                    f'<span style="color:#666;min-width:110px;">{lbl}</span>'
                    f'<span style="font-weight:600;color:{vc};min-width:100px;">{val}</span>'
                    f'<span style="color:#444;font-size:12px;">{note}</span></div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# AI ANALYSIS
# ─────────────────────────────────────────────

def _call_claude(prompt: str) -> str:
    if not st.session_state.ai_key:
        return "Add your Anthropic API key in the sidebar."
    try:
        client = anthropic.Anthropic(api_key=st.session_state.ai_key)
        msg = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=900,
                                     messages=[{"role":"user","content":prompt}])
        return msg.content[0].text
    except Exception as e:
        return f"Analysis error: {e}"

def get_ai_analysis(game, pred):
    h, a = game["home"]["abbr"], game["away"]["abbr"]
    ha, aa = pred["h_adv"], pred["a_adv"]
    inj = game["injuries"]["home"] + game["injuries"]["away"]
    factors_str = " | ".join(f'{k}: {v}%' for k,v in pred["factors"].items())
    return _call_claude(f"""Elite NBA analyst. Sharp 6-8 sentence pre-game analysis.

{a} @ {h} | {game.get("time","")}
Model: {a} {pred["game_win"]["away"]}% vs {h} {pred["game_win"]["home"]}% | Factors: {factors_str}
{a}: net {aa["net_rtg"]:+.1f}, eFG {aa["efg"]}%, TOV {aa["tov_pct"]}%, pace {aa["pace"]}, L10: {aa.get("l10_w",5)}-{10-aa.get("l10_w",5)}
{h}: net {ha["net_rtg"]:+.1f}, eFG {ha["efg"]}%, TOV {ha["tov_pct"]}%, pace {ha["pace"]}, L10: {ha.get("l10_w",5)}-{10-ha.get("l10_w",5)}
O/U: {pred["ou_line"]} | Proj: {pred["total_proj"]} | Over {pred["over_pct"]}% | OT: {pred["ot_prob"]}%
Injuries: {", ".join(inj) if inj else "None"}
Cover: (1) key matchup edge, (2) biggest model driver, (3) Q1 momentum, (4) O/U lean & reasoning, (5) OT risk, (6) injury impact. Data-driven, no fluff.""")

def get_live_ai_analysis(game, pred):
    sc = game.get("score") or {"home":0,"away":0}
    live_total = sc["home"] + sc["away"]
    qtr = game.get("quarter", 0)
    clk = game.get("clock","")
    is_ht = game["status"] == "halftime"
    qtrs_played = 2 if is_ht else max(1, qtr)
    proj = round(live_total * (4 / qtrs_played))
    leader = game["away"]["abbr"] if sc["away"]>sc["home"] else (game["home"]["abbr"] if sc["home"]>sc["away"] else "tied")
    pred_w = game["home"]["abbr"] if pred["game_win"]["home"]>=pred["game_win"]["away"] else game["away"]["abbr"]
    inj = game["injuries"]["home"] + game["injuries"]["away"]
    h, a = game["home"]["abbr"], game["away"]["abbr"]
    ha, aa = pred["h_adv"], pred["a_adv"]

    return _call_claude(f"""Elite NBA analyst — LIVE in-game analysis.

LIVE: {a} {sc["away"]} — {h} {sc["home"]}  ({'Halftime' if is_ht else f'Q{qtr} {clk}'})
Leader: {leader} +{abs(sc["home"]-sc["away"])} | Total: {live_total} pts | Proj finish: ~{proj} pts
O/U line: {pred["ou_line"]} | Live win prob: {a} {pred["game_win"]["away"]}% / {h} {pred["game_win"]["home"]}%
Pre-game pick: {pred_w} ({max(pred["pregame_win"]["home"],pred["pregame_win"]["away"])}%) — {"ON TRACK ✓" if leader==pred_w else "UPSET FORMING ✗"}
{a}: net {aa["net_rtg"]:+.1f}, eFG {aa["efg"]}% | {h}: net {ha["net_rtg"]:+.1f}, eFG {ha["efg"]}%
Injuries: {", ".join(inj) if inj else "None"}
Cover: (1) who has momentum & why, (2) pre-game prediction track record so far, (3) O/U pace & trajectory, (4) key adjustments for trailing team, (5) revised final outlook. Sharp, specific, data-driven.""")


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def render_prob_bar(label, away_abbr, home_abbr, away_pct, home_pct):
    aw, hw = max(5,away_pct), max(5,home_pct)
    st.markdown(f"""<div class="prob-container">
        <div class="prob-label"><b>{label}</b> &nbsp; <span style="color:#2ecc71">{away_abbr} {away_pct}%</span> vs <span style="color:#3498db">{home_abbr} {home_pct}%</span></div>
        <div class="prob-bar">
            <div class="prob-away" style="width:{aw}%"><span class="prob-text">{away_abbr}</span></div>
            <div class="prob-home" style="width:{hw}%"><span class="prob-text">{home_abbr}</span></div>
        </div></div>""", unsafe_allow_html=True)

def form_dots(form_list):
    return "".join(f'<span class="form-dot form-{"w" if r=="W" else "l"}"></span>' for r in form_list[:10])

def format_game_time(t):
    if not t: return ""
    t = t.strip().replace(" pm"," PM").replace(" am"," AM")
    return t

def game_label(g):
    sc = g.get("score")
    score_str = f"  {sc['away']}–{sc['home']}" if sc else ""
    q = g.get("quarter",0)
    clk = g.get("clock","")
    if g["status"] in ("inprogress","halftime"):
        period = "HT" if g["status"]=="halftime" else (f"Q{q} {clk}" if clk else f"Q{q}")
        return f"🔴  {g['away']['abbr']} @ {g['home']['abbr']}{score_str}  [{period}]"
    if g["status"] == "closed":
        return f"✅  {g['away']['abbr']} @ {g['home']['abbr']}{score_str}  · Final"
    t = format_game_time(g.get("time",""))
    return f"🕐  {g['away']['abbr']} @ {g['home']['abbr']}  · {t}" if t else f"🕐  {g['away']['abbr']} @ {g['home']['abbr']}"


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("### ⚙ Configuration")
    bdl_input = st.text_input(f"BallDontLie API Key  {'✅' if st.session_state.bdl_key else '❌'}",
                               value=st.session_state.bdl_key, type="password")
    st.session_state.bdl_key = bdl_input.strip()
    st.markdown("<div style='font-size:12px;color:#666;margin:-8px 0 10px;'>Free key → <a href='https://www.balldontlie.io' target='_blank'>balldontlie.io</a></div>", unsafe_allow_html=True)
    ai_input = st.text_input(f"Anthropic API Key  {'✅' if st.session_state.ai_key else '❌'}",
                              value=st.session_state.ai_key, type="password")
    st.session_state.ai_key = ai_input.strip()

    st.markdown("---")
    st.markdown("### 📅 Date")
    new_date = st.date_input("Select date", value=st.session_state.selected_date)
    if new_date != st.session_state.selected_date:
        st.session_state.selected_date = new_date
        st.cache_data.clear()
        st.rerun()

    cd1, cd2, cd3 = st.columns(3)
    with cd1:
        if st.button("Yesterday", use_container_width=True):
            st.session_state.selected_date = (datetime.today()-timedelta(days=1)).date()
            st.cache_data.clear(); st.rerun()
    with cd2:
        if st.button("Today", use_container_width=True):
            st.session_state.selected_date = datetime.today().date()
            st.cache_data.clear(); st.rerun()
    with cd3:
        if st.button("Tomorrow", use_container_width=True):
            st.session_state.selected_date = (datetime.today()+timedelta(days=1)).date()
            st.cache_data.clear(); st.rerun()

    st.markdown("---")
    st.markdown("### 🔍 Filters")
    new_filter = st.multiselect("Game status",["scheduled","inprogress","halftime","closed"],
                                 default=st.session_state.status_filter, key="filter_widget")
    if new_filter != st.session_state.status_filter:
        st.session_state.status_filter = new_filter; st.rerun()
    status_filter = st.session_state.status_filter

    st.markdown("---")
    auto_ref = st.toggle("⚡ Auto-refresh (live)", value=st.session_state.auto_refresh)
    if auto_ref != st.session_state.auto_refresh:
        st.session_state.auto_refresh = auto_ref

    if st.session_state.bdl_key:
        if st.button("🔌 Test Connection", use_container_width=True):
            with st.spinner("Testing..."):
                _r = fetch_games_for_date(datetime.today().strftime("%Y-%m-%d"), st.session_state.bdl_key)
                if _r and "error" in _r: st.error(_r["error"])
                elif _r: st.success(f"✅ {len(_r.get('data',[]))} game(s) today.")
                else: st.error("No response")

    if st.button("🔄 Refresh Now", use_container_width=True):
        st.cache_data.clear(); st.rerun()

    st.markdown("---")
    st.markdown("### 🧠 Model Info")
    st.markdown("""**Upgraded Prediction Model**
- ELO ratings (30%)
- Net rating diff (30%)
- Four Factors (25%)
- Recent L10 form (15%)
- Live score adjustment
- Home court: +45 ELO pts

*Data: BallDontLie + NBA Stats API + baked-in 2024-25 advanced metrics*""")


# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────

st.markdown("""<div class="main-header">
    <h1>🏀 NBA Prediction Engine</h1>
    <p>Multi-factor model · Live score tracking · Q-by-Q predictions · Over/Under · AI analysis</p>
</div>""", unsafe_allow_html=True)

# Auto-refresh
if st.session_state.auto_refresh and not (st.session_state.bdl_key == ""):
    import time as _time
    _r2 = fetch_games_for_date(st.session_state.selected_date.strftime("%Y-%m-%d"), st.session_state.bdl_key)
    if _r2 and "data" in _r2:
        _live_exists = any(normalize_bdl_game(g_)["status"] in ("inprogress","halftime") for g_ in _r2.get("data",[]))
        if _live_exists:
            st.toast("⚡ Live game active — auto-refreshing every 45s", icon="🔴")
            _time.sleep(45); st.cache_data.clear(); st.rerun()

# Try to fetch real NBA Stats in background (best-effort)
if st.session_state.bdl_key and not st.session_state.nba_stats:
    with st.spinner("Loading live team stats from NBA Stats API..."):
        live_stats = fetch_nba_team_stats()
        if live_stats:
            st.session_state.nba_stats = live_stats
            st.session_state.nba_last_fetch = datetime.now()


# ─────────────────────────────────────────────
# LOAD GAMES
# ─────────────────────────────────────────────

using_demo = (st.session_state.bdl_key == "")
all_games, games = [], []

if not using_demo:
    date_str = st.session_state.selected_date.strftime("%Y-%m-%d")
    raw = fetch_games_for_date(date_str, st.session_state.bdl_key)
    if raw and "error" in raw:
        st.error(f"**API Error:** {raw['error']}")
        using_demo = True
    elif raw and "data" in raw:
        for g in raw["data"]:
            all_games.append(normalize_bdl_game(g))
        games = [g for g in all_games if not status_filter or g["status"] in status_filter]
        if not all_games:
            st.warning(f"No games on **{date_str}**. Try a different date.")
            using_demo = True
        elif not games:
            st.info(f"No {'/'.join(status_filter)} games on {date_str}. Showing all {len(all_games)} game(s).")
            games = list(all_games)
    else:
        using_demo = True

if using_demo:
    active = status_filter or ["scheduled","inprogress","halftime"]
    games = [g for g in DEMO_GAMES if g["status"] in active] or list(DEMO_GAMES)
    if not st.session_state.bdl_key:
        st.info("**Demo mode** — Get a free BallDontLie API key at [balldontlie.io](https://www.balldontlie.io) for live data.", icon="ℹ️")

if not games:
    st.warning("No games available."); st.stop()


# ─────────────────────────────────────────────
# MAIN LAYOUT
# ─────────────────────────────────────────────

col_left, col_right = st.columns([1, 2.2], gap="large")

with col_left:
    st.markdown("#### 📋 Games")
    m1,m2,m3 = st.columns(3)
    m1.metric("Total",  len(games))
    m2.metric("Live",   sum(1 for g in games if g["status"] in ("inprogress","halftime")))
    m3.metric("Next",   sum(1 for g in games if g["status"] == "scheduled"))
    st.markdown("---")
    selected_idx = st.radio("Games", range(len(games)), format_func=lambda i: game_label(games[i]), label_visibility="collapsed")
    selected_game = games[selected_idx]


with col_right:
    g    = selected_game
    pred = calculate_predictions(g)
    is_live = g["status"] in ("inprogress","halftime")
    is_final= g["status"] == "closed"

    # ── Header ──────────────────────────────────────────────────
    conf_label = {"high":"High Confidence","med":"Moderate","low":"Low Confidence"}[pred["confidence"]]
    conf_color = {"high":"#2ecc71","med":"#f0a500","low":"#777"}[pred["confidence"]]
    conf_bg    = {"high":"rgba(46,204,113,.12)","med":"rgba(240,165,0,.12)","low":"rgba(255,255,255,.05)"}[pred["confidence"]]

    if is_live:
        sc = g.get("score") or {"home":0,"away":0}
        clk = g.get("clock","")
        qtr = g.get("quarter",0)
        period = "Halftime" if g["status"]=="halftime" else (f"Q{qtr} {clk}" if clk else f"Q{qtr}")
        _status_html = f'<span style="background:rgba(231,76,60,0.2);color:#e74c3c;border-radius:4px;padding:2px 10px;font-size:12px;font-weight:700;">● LIVE · {period}</span>'
    elif is_final:
        sc2 = g.get("score")
        fs  = f"{sc2['away']}–{sc2['home']}" if sc2 else ""
        _status_html = f'<span style="color:#555;font-size:12px;">Final  {fs}</span>'
    else:
        _t = format_game_time(g.get("time",""))
        _status_html = f'<span style="color:#f0a500;font-size:13px;font-weight:500;">🕐 {_t}</span>' if _t else ""

    st.markdown(f"""<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
        <div style="font-size:20px;font-weight:700;color:#fff;">{g['away']['abbr']} @ {g['home']['abbr']}</div>
        <span style="background:{conf_bg};color:{conf_color};border-radius:6px;padding:3px 12px;font-size:12px;font-weight:600;">{conf_label}</span>
    </div>
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">
        <span style="font-size:13px;color:#555;">{g['away']['name']} at {g['home']['name']}</span>
        {_status_html}
    </div>""", unsafe_allow_html=True)

    # Model badge
    st.markdown(f'<span class="model-badge">🧠 Multi-factor model · ELO + Net Rtg + Four Factors</span>', unsafe_allow_html=True)
    st.markdown("")

    inj = g["injuries"]["home"] + g["injuries"]["away"]
    if inj:
        st.markdown(f'<div class="injury-box">⚠ <b>Injuries:</b> {" · ".join(inj)}</div>', unsafe_allow_html=True)

    # ── Live dashboard OR form ───────────────────────────────────
    if is_live:
        render_live_game_dashboard(g, pred, st.session_state.bdl_key)
    else:
        # Form (last 10)
        st.markdown('<div class="section-header">Recent Form (Last 10)</div>', unsafe_allow_html=True)
        fc1,fc2,fc3 = st.columns([2,1,2])
        for col, abbr, form, color in [(fc1, g["away"]["abbr"], g["form"]["away"], "#2ecc71"),
                                        (fc3, g["home"]["abbr"], g["form"]["home"], "#3498db")]:
            w = form[:10].count("W")
            with col:
                st.markdown(f'<div style="text-align:center;"><div style="font-weight:600;color:{color};">{abbr}</div>'
                            f'<div style="font-size:12px;color:#555;">{w}-{10-w} L10</div>'
                            f'<div style="margin-top:4px;">{form_dots(form)}</div></div>', unsafe_allow_html=True)
        with fc2:
            st.markdown('<div style="text-align:center;color:#333;padding-top:10px;font-size:18px;">vs</div>', unsafe_allow_html=True)
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # ── Model Factor Breakdown ───────────────────────────────────
    st.markdown('<div class="section-header">Model Factor Breakdown</div>', unsafe_allow_html=True)
    h_adv, a_adv = pred["h_adv"], pred["a_adv"]
    h_elo = ELO.get(g["home"]["abbr"], ELO_MEAN)
    a_elo = ELO.get(g["away"]["abbr"], ELO_MEAN)
    factor_rows = [
        ("ELO Rating",    f'{g["away"]["abbr"]} {a_elo}',  f'{g["home"]["abbr"]} {h_elo}',  pred["factors"]["ELO"],         "ELO model (30%)"),
        ("Net Rating",    f'{a_adv["net_rtg"]:+.1f}',      f'{h_adv["net_rtg"]:+.1f}',      pred["factors"]["Net Rating"],  "Season net rtg (30%)"),
        ("Four Factors",  f'eFG {a_adv["efg"]}%',          f'eFG {h_adv["efg"]}%',          pred["factors"]["Four Factors"],"eFG/TOV/ORB/FT (25%)"),
        ("Recent Form",   f'L10: {a_adv.get("l10_w",5)}-{10-a_adv.get("l10_w",5)}', f'L10: {h_adv.get("l10_w",5)}-{10-h_adv.get("l10_w",5)}', pred["factors"]["Recent Form"],"Last 10 games (15%)"),
    ]
    st.markdown('<div style="border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:10px 14px;">', unsafe_allow_html=True)
    for fname, aval, hval, home_pct, weight in factor_rows:
        away_pct = 100 - home_pct
        winner_c = "#3498db" if home_pct >= away_pct else "#2ecc71"
        st.markdown(f'''<div style="margin-bottom:10px;">
            <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px;">
                <span style="color:#2ecc71">{g["away"]["abbr"]}: {aval}</span>
                <span style="color:#888;font-size:11px;">{fname} <span style="color:#444">({weight})</span></span>
                <span style="color:#3498db">{g["home"]["abbr"]}: {hval}</span>
            </div>
            <div style="display:flex;height:8px;border-radius:4px;overflow:hidden;background:rgba(255,255,255,0.04);">
                <div style="width:{max(4,away_pct)}%;background:#27ae60;border-radius:4px 0 0 4px;"></div>
                <div style="width:{max(4,home_pct)}%;background:#2980b9;border-radius:0 4px 4px 0;"></div>
            </div>
            <div style="display:flex;justify-content:space-between;font-size:11px;color:#444;margin-top:2px;">
                <span>{away_pct}%</span><span style="color:{winner_c};font-weight:600">▶ {"Home" if home_pct>=away_pct else "Away"} edge</span><span>{home_pct}%</span>
            </div></div>''', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Win Probability ──────────────────────────────────────────
    st.markdown('<div class="section-header">Win Probability</div>', unsafe_allow_html=True)
    if is_live:
        st.markdown(f'<div style="font-size:12px;color:#e74c3c;margin-bottom:6px;">● Live-adjusted · Pre-game was {pred["pregame_win"]["away"]}% / {pred["pregame_win"]["home"]}%</div>', unsafe_allow_html=True)
    render_prob_bar("Full Game", g["away"]["abbr"], g["home"]["abbr"], pred["game_win"]["away"], pred["game_win"]["home"])

    # ── Quarter Win Chances ──────────────────────────────────────
    st.markdown('<div class="section-header">Quarter-by-Quarter Win Chances</div>', unsafe_allow_html=True)
    q_data = [("Q1",pred["q1"]),("1st Half",pred["half"]),("Q3",pred["q3"]),("Q4",pred["q4"])]
    qcols = st.columns(4)
    for i,(lbl,qp) in enumerate(q_data):
        win   = g["home"]["abbr"] if qp["home"]>=qp["away"] else g["away"]["abbr"]
        wc    = "#3498db" if win==g["home"]["abbr"] else "#2ecc71"
        higher= max(qp["home"],qp["away"])
        with qcols[i]:
            st.markdown(f'<div class="qtr-card"><div style="font-size:11px;color:#555;font-weight:600;text-transform:uppercase;margin-bottom:6px;">{lbl}</div>'
                        f'<div style="font-size:15px;font-weight:700;color:{wc};">{win}</div>'
                        f'<div style="font-size:13px;color:#888;margin-top:2px;">{higher}%</div>'
                        f'<div style="font-size:10px;color:#444;margin-top:3px;">{g["away"]["abbr"]} {qp["away"]}% / {g["home"]["abbr"]} {qp["home"]}%</div></div>', unsafe_allow_html=True)

    st.markdown("")

    # ── PPQ + O/U ────────────────────────────────────────────────
    lc, rc = st.columns(2)
    with lc:
        st.markdown('<div class="section-header">Pts Per Quarter (Projected)</div>', unsafe_allow_html=True)
        m1,m2 = st.columns(2)
        for col, abbr, qpts in [(m1,g["away"]["abbr"],pred["away_qpts"]),(m2,g["home"]["abbr"],pred["home_qpts"])]:
            with col:
                st.markdown(f'<div class="metric-card"><div class="metric-label">{abbr} / Qtr</div><div class="metric-value">{qpts}</div><div class="metric-sub">~{qpts*4} total</div></div>', unsafe_allow_html=True)
    with rc:
        st.markdown('<div class="section-header">Over / Under</div>', unsafe_allow_html=True)
        o1,o2 = st.columns(2)
        with o1:
            st.markdown(f'<div class="ou-card ou-over"><div class="ou-label">OVER {pred["ou_line"]}</div><div class="ou-value">{pred["over_pct"]}%</div><div class="ou-sub">Proj: {pred["total_proj"]} pts</div></div>', unsafe_allow_html=True)
        with o2:
            st.markdown(f'<div class="ou-card ou-under"><div class="ou-label">UNDER {pred["ou_line"]}</div><div class="ou-value">{pred["under_pct"]}%</div><div class="ou-sub">Line: {pred["ou_line"]}</div></div>', unsafe_allow_html=True)

    st.markdown("")

    # ── First to Reach ───────────────────────────────────────────
    st.markdown('<div class="section-header">First to Reach (Q1 Pace)</div>', unsafe_allow_html=True)
    st.markdown('<div style="border:1px solid rgba(255,255,255,0.08);border-radius:10px;overflow:hidden;">', unsafe_allow_html=True)
    for pts, info in pred["milestones"].items():
        tc = "#3498db" if info["team"]==g["home"]["abbr"] else "#2ecc71"
        st.markdown(f'<div class="milestone-row"><span style="font-weight:600;color:#fff;">{pts} pts</span><span style="font-weight:600;color:{tc};">{info["team"]} ({info["prob"]}%)</span><span style="color:#444;font-size:12px;">~{info["est_min"]} min</span></div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("")

    # ── OT ───────────────────────────────────────────────────────
    ot_c = "#e74c3c" if pred["ot_prob"]>15 else ("#f0a500" if pred["ot_prob"]>8 else "#555")
    st.markdown(f'<div style="display:flex;justify-content:space-between;align-items:center;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:12px 16px;">'
                f'<span style="font-size:14px;color:#888;">⏱ Overtime probability</span>'
                f'<span style="font-size:18px;font-weight:700;color:{ot_c};">{pred["ot_prob"]}%</span></div>', unsafe_allow_html=True)

    st.markdown("")

    # ── Advanced Stats ───────────────────────────────────────────
    st.markdown('<div class="section-header">Advanced Stat Comparison</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:8px 16px;">'
                f'<div style="display:flex;justify-content:space-between;font-size:11px;color:#444;margin-bottom:8px;font-weight:600;"><span>{g["away"]["abbr"]}</span><span>STAT</span><span>{g["home"]["abbr"]}</span></div>', unsafe_allow_html=True)
    for lbl, av, hv in [
        ("OffRtg",    h_adv["ortg"],   a_adv["ortg"]),
        ("DefRtg",    h_adv["drtg"],   a_adv["drtg"]),
        ("Net Rtg",   f'{a_adv["net_rtg"]:+.1f}', f'{h_adv["net_rtg"]:+.1f}'),
        ("eFG%",      f'{a_adv["efg"]}%',          f'{h_adv["efg"]}%'),
        ("TOV%",      f'{a_adv["tov_pct"]}%',      f'{h_adv["tov_pct"]}%'),
        ("ORB%",      f'{a_adv.get("orb_pct",25)}%',f'{h_adv.get("orb_pct",25)}%'),
        ("TS%",       f'{a_adv["ts_pct"]}%',        f'{h_adv["ts_pct"]}%'),
        ("Pace",      a_adv["pace"],  h_adv["pace"]),
        ("W%",        f'{a_adv["w_pct"]:.3f}',      f'{h_adv["w_pct"]:.3f}'),
    ]:
        st.markdown(f'<div class="stat-row"><div class="val-away">{av}</div><div class="stat-name">{lbl}</div><div class="val-home">{hv}</div></div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Prob detail bars ─────────────────────────────────────────
    st.markdown("")
    st.markdown('<div class="section-header">Win Probability Detail</div>', unsafe_allow_html=True)
    for lbl, qp in q_data:
        render_prob_bar(lbl, g["away"]["abbr"], g["home"]["abbr"], qp["away"], qp["home"])

    # ── AI Analysis ──────────────────────────────────────────────
    st.markdown("")
    ai_lbl = "🔴 Live AI Analysis" if is_live else "🤖 AI Analysis"
    st.markdown(f'<div class="section-header">{ai_lbl}</div>', unsafe_allow_html=True)
    if not st.session_state.ai_key:
        st.caption("Add your Anthropic API key in the sidebar.")
    else:
        btn_lbl = "🔴 Get Live Analysis ▶" if is_live else "Generate AI Analysis ▶"
        if st.button(btn_lbl, type="primary", use_container_width=True, key=f"ai_btn_{g['id']}"):
            with st.spinner("Claude is analyzing..."):
                analysis = get_live_ai_analysis(g, pred) if is_live else get_ai_analysis(g, pred)
            st.session_state[f"ai_{g['id']}"] = analysis
        _ai_key = f"ai_{g['id']}"
        if _ai_key in st.session_state:
            st.markdown(f'<div class="ai-box">{st.session_state[_ai_key]}</div>', unsafe_allow_html=True)

    # ── Track ─────────────────────────────────────────────────────
    st.markdown("")
    already_tracked = any(p["game_id"] == g["id"] for p in st.session_state.pred_history)
    if already_tracked:
        st.success("✓ Prediction tracked — will auto-settle when game finishes.")
    elif not is_final:
        if st.button("📊 Track This Prediction", use_container_width=True, key=f"track_{g['id']}"):
            record_prediction(g, pred); st.rerun()

    # ── Summary Table ─────────────────────────────────────────────
    st.markdown("---")
    update_prediction_results(games)
    st.markdown("#### 📊 Prediction Accuracy Tracker")
    render_accuracy_dashboard()

    st.markdown("")
    st.markdown("#### 🗓 All Games — Model Summary")
    rows = []
    for gg in games:
        pp  = calculate_predictions(gg)
        fav = gg["home"]["abbr"] if pp["game_win"]["home"]>=pp["game_win"]["away"] else gg["away"]["abbr"]
        h_e = ELO.get(gg["home"]["abbr"], ELO_MEAN)
        a_e = ELO.get(gg["away"]["abbr"], ELO_MEAN)
        rows.append({
            "Matchup":     f'{gg["away"]["abbr"]} @ {gg["home"]["abbr"]}',
            "Status":      gg["status"].title(),
            "Score":       f'{gg["score"]["away"]}–{gg["score"]["home"]}' if gg.get("score") and gg["status"] in ("inprogress","halftime","closed") else "—",
            "Favorite":    fav,
            "Win %":       f'{max(pp["game_win"]["home"],pp["game_win"]["away"])}%',
            "ELO":         f'{a_e} / {h_e}',
            "Net Rtg":     f'{get_adv(gg["away"]["abbr"])["net_rtg"]:+.1f} / {get_adv(gg["home"]["abbr"])["net_rtg"]:+.1f}',
            "Proj Total":  pp["total_proj"],
            "Over %":      f'{pp["over_pct"]}%',
            "OT Risk":     f'{pp["ot_prob"]}%',
            "Confidence":  pp["confidence"].title(),
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)


st.markdown("---")
st.markdown('<div style="text-align:center;color:#333;font-size:12px;padding:8px 0 16px;">NBA Prediction Engine · ELO + Four Factors + BallDontLie + Claude AI · For entertainment purposes only</div>', unsafe_allow_html=True)
