import streamlit as st
import requests
import anthropic
import os
from datetime import datetime, timedelta, date as date_type
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
def _get_secret(key: str) -> str:
    try:
        return str(st.secrets.get(key, "")).strip()
    except Exception:
        return os.getenv(key, "").strip()

if "bdl_key" not in st.session_state:
    st.session_state.bdl_key = _get_secret("BALLDONTLIE_API_KEY")
if "ai_key" not in st.session_state:
    st.session_state.ai_key = _get_secret("ANTHROPIC_API_KEY")
if "selected_date" not in st.session_state:
    st.session_state.selected_date = datetime.today().date()
if "status_filter" not in st.session_state:
    st.session_state.status_filter = ["scheduled", "inprogress", "halftime"]
if "pred_history" not in st.session_state:
    st.session_state.pred_history = []
if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = False

BDL_BASE = "https://api.balldontlie.io/v1"

st.set_page_config(page_title="NBA Prediction Engine", page_icon="🏀", layout="wide", initial_sidebar_state="expanded")

# ─────────────────────────────────────────────
# STYLES
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.main-header { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); border-radius: 12px; padding: 24px 28px; margin-bottom: 20px; color: white; }
.main-header h1 { font-size: 26px; font-weight: 700; margin:0; }
.main-header p  { font-size: 13px; color: #aaaacc; margin: 6px 0 0; }
.game-card { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 14px; margin-bottom: 8px; }
.game-card.live { border-left: 4px solid #e74c3c; }
.live-badge  { background:#fff0f0; color:#e74c3c; border-radius:6px; padding:2px 8px; font-size:11px; font-weight:600; }
.metric-card { background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); border-radius:10px; padding:14px 16px; text-align:center; }
.metric-value { font-size:22px; font-weight:700; color:#fff; }
.metric-label { font-size:11px; color:#888; margin-bottom:4px; text-transform:uppercase; letter-spacing:0.05em; }
.metric-sub   { font-size:11px; color:#666; margin-top:3px; }
.prob-container { margin:8px 0; }
.prob-label { font-size:13px; color:#aaa; margin-bottom:4px; }
.prob-bar { display:flex; height:26px; border-radius:6px; overflow:hidden; border:1px solid rgba(255,255,255,0.1); }
.prob-away { background:#2ecc71; display:flex; align-items:center; padding-left:8px; }
.prob-home { background:#3498db; display:flex; align-items:center; justify-content:flex-end; padding-right:8px; }
.prob-text { font-size:11px; font-weight:700; color:white; }
.qtr-card { background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); border-radius:10px; padding:12px; text-align:center; }
.qtr-title  { font-size:11px; color:#888; margin-bottom:6px; font-weight:600; text-transform:uppercase; }
.qtr-winner { font-size:14px; font-weight:700; margin-top:4px; }
.qtr-prob   { font-size:12px; color:#888; margin-top:2px; }
.ou-card { border-radius:10px; padding:14px; text-align:center; border:1px solid rgba(255,255,255,0.1); }
.ou-over  { background:rgba(46,204,113,0.1); border-color:#2ecc71; }
.ou-under { background:rgba(255,255,255,0.04); }
.ou-label { font-size:11px; font-weight:600; color:#888; text-transform:uppercase; margin-bottom:4px; }
.ou-value { font-size:24px; font-weight:700; }
.ou-over .ou-value  { color:#2ecc71; }
.ou-under .ou-value { color:#aaa; }
.ou-sub { font-size:12px; color:#666; margin-top:3px; }
.milestone-row { display:flex; justify-content:space-between; align-items:center; padding:8px 12px; border-bottom:1px solid rgba(255,255,255,0.06); font-size:13px; }
.milestone-row:last-child { border-bottom:none; }
.stat-row { display:grid; grid-template-columns:1fr auto 1fr; gap:8px; align-items:center; padding:7px 0; border-bottom:1px solid rgba(255,255,255,0.06); font-size:13px; }
.stat-row:last-child { border-bottom:none; }
.val-away { text-align:right; font-weight:600; color:#2ecc71; }
.val-home { text-align:left;  font-weight:600; color:#3498db; }
.stat-name { text-align:center; color:#666; font-size:11px; }
.form-dot { display:inline-block; width:10px; height:10px; border-radius:50%; margin:0 2px; }
.form-w { background:#2ecc71; } .form-l { background:#e74c3c; }
.injury-box { background:rgba(240,165,0,0.1); border:1px solid #f0a500; border-radius:8px; padding:10px 14px; font-size:13px; color:#f0a500; margin-bottom:12px; }
.section-header { font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:0.06em; color:#666; margin:16px 0 8px; }
.ai-box { background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); border-radius:10px; padding:16px; font-size:14px; line-height:1.7; color:#ccc; margin-top:12px; }
.divider { height:1px; background:rgba(255,255,255,0.08); margin:12px 0; }
.live-score { font-size:28px; font-weight:700; color:#fff; letter-spacing:-1px; }
.q-score-card { background:rgba(255,255,255,0.05); border-radius:8px; padding:8px 12px; text-align:center; }
.live-dash { background:rgba(231,76,60,0.08); border:1px solid rgba(231,76,60,0.3); border-radius:12px; padding:16px; margin-bottom:16px; }
.live-tscore { font-size:36px; font-weight:700; color:#fff; }
.live-tname  { font-size:13px; color:#aaa; margin-top:2px; }
.acc-card { border-radius:10px; padding:14px; text-align:center; border:1px solid rgba(255,255,255,0.1); background:rgba(255,255,255,0.04); }
.acc-val  { font-size:26px; font-weight:700; }
.acc-label { font-size:11px; color:#888; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:4px; }
.acc-sub   { font-size:11px; color:#666; margin-top:3px; }
.badge-correct { background:rgba(46,204,113,0.15); color:#2ecc71; border-radius:4px; padding:2px 8px; font-size:11px; font-weight:600; }
.badge-wrong   { background:rgba(231,76,60,0.15);  color:#e74c3c; border-radius:4px; padding:2px 8px; font-size:11px; font-weight:600; }
.badge-pending { background:rgba(240,165,0,0.15);  color:#f0a500; border-radius:4px; padding:2px 8px; font-size:11px; font-weight:600; }
.hist-row { display:flex; align-items:center; justify-content:space-between; padding:8px 12px; border-bottom:1px solid rgba(255,255,255,0.06); font-size:13px; }
.hist-row:last-child { border-bottom:none; }
.live-compare { background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08); border-radius:10px; padding:12px 16px; margin-top:10px; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# BALLDONTLIE API
# ─────────────────────────────────────────────

@st.cache_data(ttl=60)
def fetch_games_for_date(date_str: str, api_key: str):
    if not api_key:
        return None
    try:
        r = requests.get(
            f"{BDL_BASE}/games",
            headers={"Authorization": api_key},
            params={"dates[]": date_str, "per_page": 100},
            timeout=15
        )
        if r.status_code == 401:
            return {"error": "401 — Invalid API key. Sign up at balldontlie.io for a free key."}
        if r.status_code == 429:
            return {"error": "429 — Rate limited. Wait a moment and click Refresh."}
        if r.status_code != 200:
            return {"error": f"HTTP {r.status_code}: {r.text[:200]}"}
        return r.json()
    except Exception as e:
        return {"error": str(e)}


# ─────────────────────────────────────────────
# TEAM SEASON STATS FALLBACK (baked-in 2024-25)
# ─────────────────────────────────────────────

TEAM_STATS = {
    "ATL": {"fg_pct": 46.9, "fg3_pct": 36.2, "reb": 43, "to": 13, "ortg": 115, "drtg": 116, "bench_pts": 40, "paint_pts": 48, "pace": 102.1},
    "BOS": {"fg_pct": 48.1, "fg3_pct": 38.5, "reb": 46, "to": 11, "ortg": 123, "drtg": 108, "bench_pts": 45, "paint_pts": 52, "pace": 99.4},
    "BKN": {"fg_pct": 44.2, "fg3_pct": 34.8, "reb": 42, "to": 14, "ortg": 110, "drtg": 117, "bench_pts": 35, "paint_pts": 44, "pace": 98.2},
    "CHA": {"fg_pct": 44.8, "fg3_pct": 35.1, "reb": 43, "to": 14, "ortg": 111, "drtg": 118, "bench_pts": 37, "paint_pts": 46, "pace": 101.3},
    "CHI": {"fg_pct": 45.3, "fg3_pct": 36.1, "reb": 44, "to": 13, "ortg": 113, "drtg": 115, "bench_pts": 38, "paint_pts": 47, "pace": 100.8},
    "CLE": {"fg_pct": 49.2, "fg3_pct": 38.7, "reb": 48, "to": 10, "ortg": 122, "drtg": 107, "bench_pts": 48, "paint_pts": 54, "pace": 98.4},
    "DAL": {"fg_pct": 45.1, "fg3_pct": 36.2, "reb": 42, "to": 14, "ortg": 112, "drtg": 115, "bench_pts": 36, "paint_pts": 44, "pace": 98.7},
    "DEN": {"fg_pct": 50.1, "fg3_pct": 36.9, "reb": 47, "to": 11, "ortg": 120, "drtg": 110, "bench_pts": 42, "paint_pts": 56, "pace": 97.8},
    "DET": {"fg_pct": 47.1, "fg3_pct": 37.2, "reb": 45, "to": 11, "ortg": 115, "drtg": 110, "bench_pts": 42, "paint_pts": 48, "pace": 102.3},
    "GSW": {"fg_pct": 46.8, "fg3_pct": 38.2, "reb": 44, "to": 12, "ortg": 117, "drtg": 113, "bench_pts": 40, "paint_pts": 48, "pace": 101.2},
    "HOU": {"fg_pct": 46.4, "fg3_pct": 36.8, "reb": 45, "to": 12, "ortg": 116, "drtg": 112, "bench_pts": 41, "paint_pts": 50, "pace": 100.6},
    "IND": {"fg_pct": 45.1, "fg3_pct": 38.4, "reb": 42, "to": 15, "ortg": 114, "drtg": 118, "bench_pts": 41, "paint_pts": 46, "pace": 106.8},
    "LAC": {"fg_pct": 46.2, "fg3_pct": 36.5, "reb": 43, "to": 13, "ortg": 115, "drtg": 112, "bench_pts": 39, "paint_pts": 48, "pace": 99.9},
    "LAL": {"fg_pct": 47.3, "fg3_pct": 36.1, "reb": 45, "to": 13, "ortg": 117, "drtg": 112, "bench_pts": 40, "paint_pts": 50, "pace": 100.1},
    "MEM": {"fg_pct": 46.3, "fg3_pct": 36.7, "reb": 45, "to": 13, "ortg": 115, "drtg": 113, "bench_pts": 39, "paint_pts": 50, "pace": 101.4},
    "MIA": {"fg_pct": 46.1, "fg3_pct": 36.9, "reb": 44, "to": 12, "ortg": 114, "drtg": 111, "bench_pts": 38, "paint_pts": 46, "pace": 99.5},
    "MIL": {"fg_pct": 47.3, "fg3_pct": 36.9, "reb": 47, "to": 12, "ortg": 118, "drtg": 111, "bench_pts": 44, "paint_pts": 52, "pace": 103.1},
    "MIN": {"fg_pct": 47.8, "fg3_pct": 37.2, "reb": 46, "to": 13, "ortg": 116, "drtg": 109, "bench_pts": 39, "paint_pts": 50, "pace": 100.8},
    "NOP": {"fg_pct": 45.2, "fg3_pct": 35.8, "reb": 44, "to": 14, "ortg": 113, "drtg": 116, "bench_pts": 38, "paint_pts": 48, "pace": 101.0},
    "NYK": {"fg_pct": 47.8, "fg3_pct": 37.3, "reb": 46, "to": 11, "ortg": 119, "drtg": 108, "bench_pts": 46, "paint_pts": 52, "pace": 99.7},
    "OKC": {"fg_pct": 47.2, "fg3_pct": 37.8, "reb": 46, "to": 11, "ortg": 120, "drtg": 108, "bench_pts": 43, "paint_pts": 50, "pace": 100.3},
    "ORL": {"fg_pct": 46.8, "fg3_pct": 35.2, "reb": 47, "to": 12, "ortg": 113, "drtg": 109, "bench_pts": 38, "paint_pts": 50, "pace": 98.8},
    "PHI": {"fg_pct": 43.5, "fg3_pct": 34.8, "reb": 41, "to": 14, "ortg": 109, "drtg": 117, "bench_pts": 34, "paint_pts": 42, "pace": 97.8},
    "PHX": {"fg_pct": 45.9, "fg3_pct": 37.1, "reb": 43, "to": 13, "ortg": 114, "drtg": 115, "bench_pts": 38, "paint_pts": 46, "pace": 100.4},
    "POR": {"fg_pct": 46.3, "fg3_pct": 37.1, "reb": 44, "to": 12, "ortg": 116, "drtg": 109, "bench_pts": 40, "paint_pts": 50, "pace": 101.4},
    "SAC": {"fg_pct": 46.1, "fg3_pct": 36.4, "reb": 44, "to": 13, "ortg": 114, "drtg": 112, "bench_pts": 39, "paint_pts": 46, "pace": 101.8},
    "SAS": {"fg_pct": 45.8, "fg3_pct": 36.2, "reb": 44, "to": 13, "ortg": 114, "drtg": 116, "bench_pts": 40, "paint_pts": 48, "pace": 102.5},
    "TOR": {"fg_pct": 44.2, "fg3_pct": 34.1, "reb": 43, "to": 13, "ortg": 108, "drtg": 114, "bench_pts": 38, "paint_pts": 44, "pace": 99.2},
    "UTA": {"fg_pct": 44.8, "fg3_pct": 35.9, "reb": 43, "to": 14, "ortg": 111, "drtg": 114, "bench_pts": 37, "paint_pts": 44, "pace": 103.2},
    "WAS": {"fg_pct": 43.1, "fg3_pct": 33.8, "reb": 42, "to": 15, "ortg": 107, "drtg": 120, "bench_pts": 33, "paint_pts": 42, "pace": 101.6},
}

DEFAULT_STATS = {"fg_pct": 46.0, "fg3_pct": 36.5, "reb": 44, "to": 13, "ortg": 114, "drtg": 114, "bench_pts": 38, "paint_pts": 48, "pace": 100.5}

def get_team_stats(abbr: str) -> dict:
    return TEAM_STATS.get(abbr, DEFAULT_STATS)


# ─────────────────────────────────────────────
# DEMO DATA
# ─────────────────────────────────────────────
DEMO_GAMES = [
    {
        "id": "demo-1", "status": "inprogress", "quarter": 2, "clock": "HT",
        "home": {"abbr": "OKC", "name": "Oklahoma City Thunder", "id": 25},
        "away": {"abbr": "MIN", "name": "Minnesota Timberwolves", "id": 21},
        "score": {"home": 47, "away": 53},
        "q_scores": {"1": {"home": 23, "away": 22}, "2": {"home": 24, "away": 31}},
        "win_prob": {"home": 38, "away": 62}, "time": "HALFTIME",
        "stats": {"home": get_team_stats("OKC"), "away": get_team_stats("MIN")},
        "form": {"home": ["W","W","L","W","W"], "away": ["W","L","W","W","W"]},
        "injuries": {"home": [], "away": []}, "ou_line": 218.5,
        "top_players": {"home": [{"name":"SGA","pts":4},{"name":"Chet H","pts":11}], "away": [{"name":"Ant Edwards","pts":11},{"name":"J.Randle","pts":17}]}
    },
    {
        "id": "demo-2", "status": "scheduled",
        "home": {"abbr": "CLE", "name": "Cleveland Cavaliers", "id": 5},
        "away": {"abbr": "DAL", "name": "Dallas Mavericks", "id": 7},
        "score": None, "q_scores": {}, "win_prob": {"home": 91, "away": 9}, "time": "8:30 PM ET",
        "stats": {"home": get_team_stats("CLE"), "away": get_team_stats("DAL")},
        "form": {"home": ["W","W","W","W","W"], "away": ["L","L","L","W","L"]},
        "injuries": {"home": [], "away": ["Kyrie Irving (OUT)","Luka Doncic (OUT)"]},
        "ou_line": 222.5, "top_players": {"home": [], "away": []}
    },
    {
        "id": "demo-3", "status": "scheduled",
        "home": {"abbr": "MIL", "name": "Milwaukee Bucks", "id": 17},
        "away": {"abbr": "IND", "name": "Indiana Pacers", "id": 12},
        "score": None, "q_scores": {}, "win_prob": {"home": 76, "away": 24}, "time": "8:30 PM ET",
        "stats": {"home": get_team_stats("MIL"), "away": get_team_stats("IND")},
        "form": {"home": ["W","W","W","L","W"], "away": ["L","W","L","W","L"]},
        "injuries": {"home": [], "away": ["T.J. McConnell (OUT)"]},
        "ou_line": 232.5, "top_players": {"home": [], "away": []}
    },
    {
        "id": "demo-4", "status": "scheduled",
        "home": {"abbr": "PHI", "name": "Philadelphia 76ers", "id": 26},
        "away": {"abbr": "POR", "name": "Portland Trail Blazers", "id": 28},
        "score": None, "q_scores": {}, "win_prob": {"home": 25, "away": 75}, "time": "11:00 PM ET",
        "stats": {"home": get_team_stats("PHI"), "away": get_team_stats("POR")},
        "form": {"home": ["L","L","W","L","L"], "away": ["W","W","W","L","W"]},
        "injuries": {"home": ["Joel Embiid (OUT)","Paul George (OUT)"], "away": []},
        "ou_line": 224.0, "top_players": {"home": [], "away": []}
    },
    {
        "id": "demo-5", "status": "scheduled",
        "home": {"abbr": "NYK", "name": "New York Knicks", "id": 20},
        "away": {"abbr": "GSW", "name": "Golden State Warriors", "id": 10},
        "score": None, "q_scores": {}, "win_prob": {"home": 88, "away": 12}, "time": "1:00 AM ET",
        "stats": {"home": get_team_stats("NYK"), "away": get_team_stats("GSW")},
        "form": {"home": ["W","W","W","L","W"], "away": ["L","L","W","L","L"]},
        "injuries": {"home": [], "away": ["Stephen Curry (GTD)","Draymond Green (OUT)"]},
        "ou_line": 226.5, "top_players": {"home": [], "away": []}
    },
]


# ─────────────────────────────────────────────
# GAME NORMALIZER
# ─────────────────────────────────────────────

def normalize_bdl_game(g: dict) -> dict:
    home = g.get("home_team", {})
    away = g.get("visitor_team", {})
    home_abbr = home.get("abbreviation", "HME")
    away_abbr = away.get("abbreviation", "AWY")

    status_raw = g.get("status", "")
    if status_raw == "Final":
        status = "closed"
    elif "Halftime" in status_raw:
        status = "halftime"
    elif g.get("period", 0) > 0 and ":" in status_raw:
        status = "inprogress"
    elif ":" in status_raw and ("pm" in status_raw.lower() or "am" in status_raw.lower()):
        status = "scheduled"
    else:
        status = "scheduled"

    home_score = g.get("home_team_score", 0) or 0
    away_score = g.get("visitor_team_score", 0) or 0

    hs = get_team_stats(home_abbr)
    as_ = get_team_stats(away_abbr)

    if status in ("inprogress", "halftime") and (home_score + away_score) > 0:
        diff = home_score - away_score
        home_wp = max(5, min(95, round(50 + diff * 1.8)))
    else:
        net = (hs["ortg"] - hs["drtg"]) - (as_["ortg"] - as_["drtg"])
        home_wp = max(8, min(92, round(50 + net * 3.2 + 2.5)))

    avg_pace = (hs["pace"] + as_["pace"]) / 2
    ou_est = round(((hs["ortg"] + as_["ortg"]) / 2) * avg_pace / 100 * 2 / 2 * 0.985, 1)

    has_score = (home_score + away_score) > 0

    return {
        "id":       str(g.get("id", "bdl")),
        "status":   status,
        "quarter":  g.get("period", 0),
        "clock":    g.get("time", ""),
        "home":     {"abbr": home_abbr, "name": home.get("full_name", "Home"), "id": home.get("id", 0)},
        "away":     {"abbr": away_abbr, "name": away.get("full_name", "Away"), "id": away.get("id", 0)},
        "score":    {"home": home_score, "away": away_score} if has_score else None,
        "q_scores": {},
        "win_prob": {"home": home_wp, "away": 100 - home_wp},
        "time":     status_raw,
        "stats":    {"home": hs, "away": as_},
        "form":     {"home": ["W","W","L","W","W"], "away": ["W","L","W","W","W"]},
        "injuries": {"home": [], "away": []},
        "ou_line":  ou_est,
        "top_players": {"home": [], "away": []},
    }


# ─────────────────────────────────────────────
# PREDICTION ENGINE
# ─────────────────────────────────────────────

def calculate_predictions(game: dict) -> dict:
    hp = game["win_prob"]["home"] / 100
    spread = abs(hp - 0.5)

    q1hp   = hp * 0.52 + 0.5 * 0.48
    halfhp = hp * 0.65 + 0.5 * 0.35
    q3hp   = hp * 0.56 + 0.5 * 0.44
    q4hp   = hp * 0.68 + 0.5 * 0.32

    ou = game["ou_line"]
    q_base = ou / 8
    h_ortg = game["stats"]["home"].get("ortg", 113)
    a_ortg = game["stats"]["away"].get("ortg", 113)
    home_qpts = max(20, round(q_base * (0.5 + (h_ortg - 113) / 200)))
    away_qpts = max(20, round(q_base * (0.5 + (a_ortg - 113) / 200)))
    total_proj = (home_qpts + away_qpts) * 4

    diff      = total_proj - ou
    over_pct  = min(80, max(20, round(50 + diff * 3)))
    ot_prob   = max(3, round((1 - spread * 3.2) * 14))
    conf      = "high" if spread > 0.30 else ("med" if spread > 0.15 else "low")

    total_q = home_qpts + away_qpts
    home_share = home_qpts / total_q if total_q > 0 else 0.5
    milestones = {}
    for pts in [10, 15, 20, 25, 30]:
        adj = min(0.95, max(0.05, home_share + (hp - 0.5) * 0.04))
        if adj > 0.5:
            milestones[pts] = {"team": game["home"]["abbr"], "prob": round(adj * 100), "est_min": round(pts / (total_q / 12), 1)}
        else:
            milestones[pts] = {"team": game["away"]["abbr"], "prob": round((1 - adj) * 100), "est_min": round(pts / (total_q / 12), 1)}

    return {
        "game_win":   {"home": round(hp * 100), "away": round((1-hp) * 100)},
        "q1":         {"home": round(q1hp * 100),   "away": round((1 - q1hp) * 100)},
        "half":       {"home": round(halfhp * 100),  "away": round((1 - halfhp) * 100)},
        "q3":         {"home": round(q3hp * 100),   "away": round((1 - q3hp) * 100)},
        "q4":         {"home": round(q4hp * 100),   "away": round((1 - q4hp) * 100)},
        "ot_prob":    ot_prob,
        "home_qpts":  home_qpts,
        "away_qpts":  away_qpts,
        "total_proj": round(total_proj),
        "ou_line":    ou,
        "over_pct":   over_pct,
        "under_pct":  100 - over_pct,
        "confidence": conf,
        "milestones": milestones,
    }


# ─────────────────────────────────────────────
# AI ANALYSIS
# ─────────────────────────────────────────────

def get_ai_analysis(game: dict, pred: dict) -> str:
    if not st.session_state.ai_key:
        return "Add your Anthropic API key in the sidebar to enable AI analysis."
    try:
        client = anthropic.Anthropic(api_key=st.session_state.ai_key)
        inj = game["injuries"]["home"] + game["injuries"]["away"]
        status_str = (
            f"LIVE Q{game['quarter']} {game['clock']} — {game['away']['abbr']} {game['score']['away']} - {game['home']['abbr']} {game['score']['home']}"
            if game["status"] in ("inprogress", "halftime") and game["score"]
            else f"Scheduled ({game['time']})"
        )
        prompt = f"""You are an elite NBA analyst. Give a sharp 6-8 sentence analysis.

Game: {game['away']['name']} @ {game['home']['name']} | {status_str}
Win prob: {game['away']['abbr']} {pred['game_win']['away']}% | {game['home']['abbr']} {pred['game_win']['home']}%
{game['away']['abbr']}: FG {game['stats']['away']['fg_pct']}%, 3PT {game['stats']['away']['fg3_pct']}%, OffRtg {game['stats']['away']['ortg']}, DefRtg {game['stats']['away']['drtg']}, Pace {game['stats']['away']['pace']}, Form {'-'.join(game['form']['away'])}
{game['home']['abbr']}: FG {game['stats']['home']['fg_pct']}%, 3PT {game['stats']['home']['fg3_pct']}%, OffRtg {game['stats']['home']['ortg']}, DefRtg {game['stats']['home']['drtg']}, Pace {game['stats']['home']['pace']}, Form {'-'.join(game['form']['home'])}
O/U: {pred['ou_line']} | Projected: {pred['total_proj']} pts | Over {pred['over_pct']}%
Injuries: {', '.join(inj) if inj else 'None'}
Q1: {game['away']['abbr']} {pred['q1']['away']}% | Q4: {game['away']['abbr']} {pred['q4']['away']}% | OT: {pred['ot_prob']}%

Cover: key storyline, biggest win factor, Q1 momentum, O/U lean & reasoning, OT risk, injury impact. Direct and data-driven."""

        msg = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=1000,
                                     messages=[{"role": "user", "content": prompt}])
        return msg.content[0].text
    except Exception as e:
        return f"AI analysis error: {e}"


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

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
        "game_id": gid,
        "matchup": f'{game["away"]["abbr"]} @ {game["home"]["abbr"]}',
        "date": str(st.session_state.selected_date),
        "predicted_winner": fav,
        "predicted_winner_pct": max(pred["game_win"]["home"], pred["game_win"]["away"]),
        "actual_winner": None,
        "ou_line": pred["ou_line"],
        "predicted_total": pred["total_proj"],
        "predicted_over": pred["over_pct"] >= 50,
        "actual_total": None,
        "q1_pred": q1f,
        "status": "pending",
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })

def update_prediction_results(games):
    for game in games:
        if game["status"] != "closed":
            continue
        sc = game.get("score")
        if not sc:
            continue
        actual_winner = game["home"]["abbr"] if sc["home"] > sc["away"] else game["away"]["abbr"]
        actual_total = sc["home"] + sc["away"]
        for p in st.session_state.pred_history:
            if p["game_id"] == game["id"] and p["status"] == "pending":
                p["actual_winner"] = actual_winner
                p["actual_total"] = actual_total
                p["status"] = "settled"
                p["winner_correct"] = p["predicted_winner"] == actual_winner
                p["ou_correct"] = (actual_total > p["ou_line"]) == p["predicted_over"]

def get_accuracy_stats():
    settled = [p for p in st.session_state.pred_history if p["status"] == "settled"]
    pending = [p for p in st.session_state.pred_history if p["status"] == "pending"]
    if not settled:
        return {"total": len(st.session_state.pred_history), "settled": 0, "pending": len(pending),
                "winner_pct": None, "ou_pct": None, "correct_winners": 0, "correct_ou": 0}
    cw = sum(1 for p in settled if p.get("winner_correct"))
    co = sum(1 for p in settled if p.get("ou_correct"))
    return {"total": len(st.session_state.pred_history), "settled": len(settled), "pending": len(pending),
            "winner_pct": round(cw / len(settled) * 100), "ou_pct": round(co / len(settled) * 100),
            "correct_winners": cw, "correct_ou": co}

def render_accuracy_dashboard():
    acc = get_accuracy_stats()
    if acc["total"] == 0:
        st.info("No predictions tracked yet. Click **Track This Prediction** on any game to start building your record.", icon="📊")
        return
    c1, c2, c3, c4 = st.columns(4)
    for col, val, label, sub in [
        (c1, acc["total"], "Tracked", f'{acc["settled"]} settled'),
        (c2, f'{acc["winner_pct"]}%' if acc["winner_pct"] is not None else "—", "Winner Acc", f'{acc["correct_winners"]}/{acc["settled"]}'),
        (c3, f'{acc["ou_pct"]}%' if acc["ou_pct"] is not None else "—", "O/U Acc", f'{acc["correct_ou"]}/{acc["settled"]}'),
        (c4, acc["pending"], "Pending", "awaiting results"),
    ]:
        color = ""
        if isinstance(val, str) and "%" in val:
            pct = int(val.replace("%", ""))
            color = "color:#2ecc71;" if pct >= 60 else ("color:#f0a500;" if pct >= 45 else "color:#e74c3c;")
        with col:
            st.markdown(f'<div class="acc-card"><div class="acc-label">{label}</div>'
                        f'<div class="acc-val" style="{color}">{val}</div>'
                        f'<div class="acc-sub">{sub}</div></div>', unsafe_allow_html=True)

    if st.session_state.pred_history:
        st.markdown("")
        with st.expander("📋 Prediction History", expanded=False):
            rows = []
            for p in reversed(st.session_state.pred_history):
                if p["status"] == "settled":
                    wc = "✓" if p.get("winner_correct") else "✗"
                    oc = "✓" if p.get("ou_correct") else "✗"
                    result = f'{wc} {p["actual_winner"]}'
                    ou_res = f'{oc} {"Over" if p["actual_total"] > p["ou_line"] else "Under"} ({p["actual_total"]} pts)'
                else:
                    result = "Pending"
                    ou_res = f'Line: {p["ou_line"]}'
                rows.append({
                    "Date": p["date"], "Matchup": p["matchup"],
                    "Predicted": f'{p["predicted_winner"]} ({p["predicted_winner_pct"]}%)',
                    "Result": result, "O/U": ou_res,
                })
            st.dataframe(rows, use_container_width=True, hide_index=True)
        if st.button("🗑 Clear History", key="clear_hist"):
            st.session_state.pred_history = []
            st.rerun()

def render_live_game_dashboard(game, pred):
    sc = game.get("score") or {"home": 0, "away": 0}
    qtr = game.get("quarter", 0)
    clk = game.get("clock", "")
    is_ht = game["status"] == "halftime"
    clock_display = "HALFTIME" if is_ht else (f"Q{qtr}  {clk}" if clk else f"Q{qtr}")

    st.markdown(f'''<div class="live-dash">
        <div style="display:flex;align-items:center;justify-content:space-between;">
            <div style="text-align:left;">
                <div class="live-tscore">{sc["away"]}</div>
                <div class="live-tname">{game["away"]["name"]}</div>
            </div>
            <div style="text-align:center;">
                <div style="font-size:11px;color:#e74c3c;font-weight:600;margin-bottom:6px;">● LIVE</div>
                <div style="font-size:16px;color:#e74c3c;font-weight:700;">{clock_display}</div>
            </div>
            <div style="text-align:right;">
                <div class="live-tscore">{sc["home"]}</div>
                <div class="live-tname">{game["home"]["name"]}</div>
            </div>
        </div>
    </div>''', unsafe_allow_html=True)

    if game.get("q_scores"):
        st.markdown('<div class="section-header">Quarter Breakdown</div>', unsafe_allow_html=True)
        ncols = len(game["q_scores"]) + 1
        qcols = st.columns(ncols)
        for i, (qn, qs) in enumerate(sorted(game["q_scores"].items())):
            ldr = game["away"]["abbr"] if qs["away"] > qs["home"] else (game["home"]["abbr"] if qs["home"] > qs["away"] else "TIE")
            lc = "#2ecc71" if ldr == game["away"]["abbr"] else ("#3498db" if ldr == game["home"]["abbr"] else "#888")
            with qcols[i]:
                st.markdown(f'<div class="q-score-card"><div style="font-size:11px;color:#888;">Q{qn}</div>'
                            f'<div style="font-size:16px;font-weight:700;color:#fff;">{qs["away"]}–{qs["home"]}</div>'
                            f'<div style="font-size:11px;color:{lc};font-weight:600;">{ldr}</div></div>', unsafe_allow_html=True)
        with qcols[-1]:
            st.markdown(f'<div class="q-score-card" style="border:1px solid rgba(231,76,60,0.3);">'
                        f'<div style="font-size:11px;color:#e74c3c;">TOTAL</div>'
                        f'<div style="font-size:16px;font-weight:700;color:#fff;">{sc["away"]}–{sc["home"]}</div>'
                        f'<div style="font-size:11px;color:#aaa;">Live</div></div>', unsafe_allow_html=True)

    live_total = sc["home"] + sc["away"]
    live_leader = game["away"]["abbr"] if sc["away"] > sc["home"] else (game["home"]["abbr"] if sc["home"] > sc["away"] else "TIE")
    pred_winner = game["home"]["abbr"] if pred["game_win"]["home"] >= pred["game_win"]["away"] else game["away"]["abbr"]
    qtrs_played = 2 if is_ht else max(1, qtr)
    pace_mult = 4 / qtrs_played if qtrs_played > 0 else 1
    proj_final = round(live_total * min(pace_mult, 4))
    pts_needed = max(0, round(pred["ou_line"] - live_total))
    match_pred = live_leader == pred_winner

    st.markdown('<div class="section-header">Live vs Pre-Game Predictions</div>', unsafe_allow_html=True)
    st.markdown('<div class="live-compare">', unsafe_allow_html=True)
    for lbl, val, note, col in [
        ("Current leader",   live_leader,
         f'{"✓ Matches" if match_pred else "✗ Differs"} pre-game pick ({pred_winner})',
         "#2ecc71" if match_pred else "#e74c3c"),
        ("Live total",       f"{live_total} pts",
         f"Line {pred['ou_line']} · Proj finish ~{proj_final} pts",
         "#f0a500" if abs(proj_final - pred['ou_line']) < 8 else ("#2ecc71" if proj_final > pred['ou_line'] else "#aaa")),
        ("O/U pace",         f'{"Over" if proj_final > pred["ou_line"] else "Under"} pace',
         f"Need {pts_needed} more pts to hit over in {4 - qtrs_played} qtr(s)",
         "#2ecc71" if proj_final > pred["ou_line"] else "#aaa"),
        ("Pre-game pick",    f'{pred_winner} ({max(pred["game_win"]["home"],pred["game_win"]["away"])}%)',
         "Original win probability", "#3498db"),
    ]:
        st.markdown(f'<div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.05);font-size:13px;">'
                    f'<span style="color:#888;width:120px;">{lbl}</span>'
                    f'<span style="font-weight:600;color:{col};">{val}</span>'
                    f'<span style="color:#555;font-size:12px;text-align:right;max-width:200px;">{note}</span>'
                    f'</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def get_live_ai_analysis(game, pred):
    sc = game.get("score") or {"home": 0, "away": 0}
    live_total = sc["home"] + sc["away"]
    qtr = game.get("quarter", 0)
    clk = game.get("clock", "")
    is_ht = game["status"] == "halftime"
    qtrs_played = 2 if is_ht else max(1, qtr)
    proj_final = round(live_total * (4 / qtrs_played))
    live_leader = game["away"]["abbr"] if sc["away"] > sc["home"] else (game["home"]["abbr"] if sc["home"] > sc["away"] else "tied")
    pred_winner = game["home"]["abbr"] if pred["game_win"]["home"] >= pred["game_win"]["away"] else game["away"]["abbr"]
    inj = game["injuries"]["home"] + game["injuries"]["away"]

    prompt = f"""You are an elite NBA analyst giving LIVE in-game analysis.

LIVE: {game['away']['name']} {sc['away']} — {game['home']['name']} {sc['home']}  ({'Halftime' if is_ht else f'Q{qtr} {clk}'})
Current leader: {live_leader} | Total scored: {live_total} pts | Projected final: ~{proj_final} pts
O/U line: {pred['ou_line']} | Pre-game predicted winner: {pred_winner} ({max(pred['game_win']['home'],pred['game_win']['away'])}%)
{game['away']['abbr']}: OffRtg {game['stats']['away']['ortg']}, DefRtg {game['stats']['away']['drtg']}, Pace {game['stats']['away']['pace']}
{game['home']['abbr']}: OffRtg {game['stats']['home']['ortg']}, DefRtg {game['stats']['home']['drtg']}, Pace {game['stats']['home']['pace']}
Injuries: {', '.join(inj) if inj else 'None'}

Give 5-6 sharp sentences: (1) current momentum and who controls the game, (2) how the live score compares to pre-game predictions — on track or upset forming, (3) O/U trajectory, (4) key adjustments needed for trailing team, (5) revised final result outlook. Be direct, specific, no fluff."""

    try:
        client = anthropic.Anthropic(api_key=st.session_state.ai_key)
        msg = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=800,
                                     messages=[{"role": "user", "content": prompt}])
        return msg.content[0].text
    except Exception as e:
        return f"Analysis error: {e}"



def render_prob_bar(label, away_abbr, home_abbr, away_pct, home_pct):
    aw, hw = max(6, away_pct), max(6, home_pct)
    st.markdown(f"""<div class="prob-container">
        <div class="prob-label"><b>{label}</b> &nbsp;
            <span style="color:#2ecc71">{away_abbr} {away_pct}%</span> vs
            <span style="color:#3498db">{home_abbr} {home_pct}%</span>
        </div>
        <div class="prob-bar">
            <div class="prob-away" style="width:{aw}%"><span class="prob-text">{away_abbr}</span></div>
            <div class="prob-home" style="width:{hw}%"><span class="prob-text">{home_abbr}</span></div>
        </div></div>""", unsafe_allow_html=True)

def form_dots(form_list):
    return "".join(f'<span class="form-dot form-{"w" if r=="W" else "l"}"></span>' for r in form_list)

def format_game_time(time_str: str) -> str:
    """Convert BallDontLie status string like '7:30 pm ET' to clean display."""
    if not time_str:
        return ""
    t = time_str.strip()
    # Already a nice time string like "7:30 pm ET"
    if any(x in t.lower() for x in ["pm", "am"]):
        # Uppercase AM/PM and clean up
        t = t.replace(" pm", " PM").replace(" am", " AM")
        return t
    return t

def game_label(g):
    sc = g.get("score")
    score_str = f"  {sc['away']}–{sc['home']}" if sc else ""
    time_str = format_game_time(g.get("time", ""))
    time_part = f"  · {time_str}" if time_str and g["status"] == "scheduled" else ""
    if g["status"] in ("inprogress", "halftime"):
        clk = g.get("clock", "")
        qtr = g.get("quarter", 0)
        live_info = f"  Q{qtr}" if qtr and not clk else (f"  Q{qtr} {clk}" if qtr else "")
        return f"🔴  {g['away']['abbr']} @ {g['home']['abbr']}{score_str}{live_info}"
    if g["status"] == "closed":
        return f"✅  {g['away']['abbr']} @ {g['home']['abbr']}{score_str}  · Final"
    return f"🕐  {g['away']['abbr']} @ {g['home']['abbr']}{time_part}"


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("### ⚙ Configuration")

    bdl_status = "✅ Key set" if st.session_state.bdl_key else "❌ Not set"
    ai_status  = "✅ Key set" if st.session_state.ai_key  else "❌ Not set"

    bdl_input = st.text_input(f"BallDontLie API Key  {bdl_status}", value=st.session_state.bdl_key, type="password",
                               help="Free key from balldontlie.io — no credit card")
    st.session_state.bdl_key = bdl_input.strip()
    st.markdown("<div style='font-size:12px;color:#888;margin:-8px 0 10px;'>Get a free key → <a href='https://www.balldontlie.io' target='_blank'>balldontlie.io</a></div>", unsafe_allow_html=True)

    ai_input = st.text_input(f"Anthropic API Key  {ai_status}", value=st.session_state.ai_key, type="password",
                              help="Required for AI deep analysis")
    st.session_state.ai_key = ai_input.strip()

    st.markdown("---")
    st.markdown("### 📅 Date")
    new_date = st.date_input("Select date", value=st.session_state.selected_date)
    if new_date != st.session_state.selected_date:
        st.session_state.selected_date = new_date
        st.cache_data.clear()   # clear cache so new date fetches fresh data
        st.rerun()

    # Quick date jump buttons
    col_d1, col_d2, col_d3 = st.columns(3)
    with col_d1:
        if st.button("Yesterday", use_container_width=True):
            st.session_state.selected_date = (datetime.today() - timedelta(days=1)).date()
            st.cache_data.clear()
            st.rerun()
    with col_d2:
        if st.button("Today", use_container_width=True):
            st.session_state.selected_date = datetime.today().date()
            st.cache_data.clear()
            st.rerun()
    with col_d3:
        if st.button("Tomorrow", use_container_width=True):
            st.session_state.selected_date = (datetime.today() + timedelta(days=1)).date()
            st.cache_data.clear()
            st.rerun()

    st.markdown("---")
    st.markdown("### 🔍 Filters")
    new_filter = st.multiselect(
        "Game status",
        ["scheduled", "inprogress", "halftime", "closed"],
        default=st.session_state.status_filter,
        key="filter_widget"
    )
    if new_filter != st.session_state.status_filter:
        st.session_state.status_filter = new_filter
        st.rerun()
    status_filter = st.session_state.status_filter

    st.markdown("---")
    if st.session_state.bdl_key:
        if st.button("🔌 Test Connection", use_container_width=True):
            with st.spinner("Testing..."):
                _date = datetime.today().strftime("%Y-%m-%d")
                _r = fetch_games_for_date(_date, st.session_state.bdl_key)
                if _r is None:
                    st.error("No response")
                elif "error" in _r:
                    st.error(_r["error"])
                else:
                    st.success(f"✅ Connected! {len(_r.get('data', []))} game(s) today.")

    auto_ref = st.toggle("⚡ Auto-refresh (live games)", value=st.session_state.auto_refresh)
    if auto_ref != st.session_state.auto_refresh:
        st.session_state.auto_refresh = auto_ref

    if st.button("🔄 Refresh Now", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.markdown("### ℹ About\n**NBA Prediction Engine**\n- Free BallDontLie API\n- Live scores & schedules\n- Q-by-Q predictions\n- O/U · First-to-reach\n- Claude AI analysis\n\n*Demo mode when no key is set.*")


# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────

st.markdown("""<div class="main-header">
    <h1>🏀 NBA Prediction Engine</h1>
    <p>Live data · Quarter-by-quarter predictions · Over/Under · First-to-reach · AI-powered deep analysis</p>
</div>""", unsafe_allow_html=True)

# Auto-refresh for live games
if st.session_state.auto_refresh:
    live_games_exist = False
    if not (st.session_state.bdl_key == ""):
        _check_date = st.session_state.selected_date.strftime("%Y-%m-%d")
        _check_raw = fetch_games_for_date(_check_date, st.session_state.bdl_key)
        if _check_raw and "data" in _check_raw:
            live_games_exist = any(
                normalize_bdl_game(g_)["status"] in ("inprogress","halftime")
                for g_ in _check_raw.get("data", [])
            )
    if live_games_exist:
        import time as _time
        st.toast("⚡ Live game detected — auto-refreshing every 60s", icon="🔴")
        _time.sleep(60)
        st.cache_data.clear()
        st.rerun()


# ─────────────────────────────────────────────
# LOAD GAMES
# ─────────────────────────────────────────────

using_demo = (st.session_state.bdl_key == "")
all_games = []   # unfiltered
games = []       # filtered

if not using_demo:
    date_str = st.session_state.selected_date.strftime("%Y-%m-%d")
    raw = fetch_games_for_date(date_str, st.session_state.bdl_key)

    if raw and "error" in raw:
        st.error(f"**API Error:** {raw['error']}")
        using_demo = True
    elif raw and "data" in raw:
        for g in raw["data"]:
            all_games.append(normalize_bdl_game(g))

        # Apply filter — if nothing matches, show ALL games with a notice
        if status_filter:
            games = [g for g in all_games if g["status"] in status_filter]
        else:
            games = list(all_games)

        if not all_games:
            st.warning(f"No games found on **{date_str}**. Try a different date.")
            using_demo = True
        elif not games:
            # Filter excluded everything — show all and warn
            st.info(f"No **{', '.join(status_filter)}** games on {date_str}. "
                    f"Showing all {len(all_games)} game(s) instead.")
            games = list(all_games)
    else:
        using_demo = True

if using_demo:
    active = status_filter or ["scheduled", "inprogress", "halftime"]
    games = [g for g in DEMO_GAMES if g["status"] in active] or list(DEMO_GAMES)
    if not st.session_state.bdl_key:
        st.info(
            "**Demo mode** — Get a **free** BallDontLie API key at "
            "[balldontlie.io](https://www.balldontlie.io) (just email signup, no credit card) "
            "and enter it in the sidebar for live NBA games.",
            icon="ℹ️"
        )

if not games:
    st.warning("No games available.")
    st.stop()


# ─────────────────────────────────────────────
# MAIN LAYOUT
# ─────────────────────────────────────────────

col_left, col_right = st.columns([1, 2], gap="large")

with col_left:
    st.markdown("#### 📋 Games")
    m1, m2, m3 = st.columns(3)
    m1.metric("Total", len(games))
    m2.metric("Live",  sum(1 for g in games if g["status"] in ("inprogress","halftime")))
    m3.metric("Next",  sum(1 for g in games if g["status"] == "scheduled"))
    st.markdown("---")

    selected_idx = st.radio("Select game", range(len(games)),
                             format_func=lambda i: game_label(games[i]),
                             label_visibility="collapsed")
    selected_game = games[selected_idx]

    if selected_game["status"] in ("inprogress","halftime") and selected_game["score"]:
        g = selected_game
        clk = "HALFTIME" if g["status"] == "halftime" else f"Q{g['quarter']} {g['clock']}"
        st.markdown(f"""<div class="game-card live" style="margin-top:12px;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div><div style="font-size:13px;color:#aaa;">{g['away']['name']}</div>
                <div style="font-size:13px;color:#aaa;">{g['home']['name']}</div></div>
                <div style="text-align:right;"><div class="live-score">{g['score']['away']}–{g['score']['home']}</div>
                <span class="live-badge">● {clk}</span></div>
            </div></div>""", unsafe_allow_html=True)


with col_right:
    g    = selected_game
    pred = calculate_predictions(g)

    conf_label = {"high":"High Confidence","med":"Moderate","low":"Low Confidence"}[pred["confidence"]]
    conf_color = {"high":"#2ecc71","med":"#f0a500","low":"#888"}[pred["confidence"]]
    conf_bg    = {"high":"rgba(46,204,113,.15)","med":"rgba(240,165,0,.15)","low":"rgba(255,255,255,.06)"}[pred["confidence"]]

    # Build status/time line
    if g["status"] in ("inprogress", "halftime"):
        clk = g.get("clock","")
        qtr = g.get("quarter",0)
        _status_html = f'<span style="background:rgba(231,76,60,0.2);color:#e74c3c;border-radius:4px;padding:2px 8px;font-size:12px;font-weight:600;">● LIVE Q{qtr}{" "+clk if clk else ""}</span>'
    elif g["status"] == "closed":
        sc = g.get("score")
        final_score = f"{sc['away']}–{sc['home']}" if sc else ""
        _status_html = f'<span style="color:#666;font-size:12px;">Final  {final_score}</span>'
    else:
        _time = format_game_time(g.get("time",""))
        _status_html = f'<span style="color:#f0a500;font-size:13px;font-weight:500;">🕐 {_time}</span>' if _time else ""

    st.markdown(f"""<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
        <div style="font-size:20px;font-weight:700;color:#fff;">{g['away']['abbr']} @ {g['home']['abbr']}</div>
        <span style="background:{conf_bg};color:{conf_color};border-radius:6px;padding:3px 12px;font-size:12px;font-weight:600;">{conf_label}</span>
    </div>
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
        <span style="font-size:13px;color:#666;">{g['away']['name']} at {g['home']['name']}</span>
        {_status_html}
    </div>
    """, unsafe_allow_html=True)

    inj = g["injuries"]["home"] + g["injuries"]["away"]
    if inj:
        st.markdown(f'<div class="injury-box">⚠ <b>Injuries:</b> {" · ".join(inj)}</div>', unsafe_allow_html=True)

    # FORM
    st.markdown('<div class="section-header">Recent Form (Last 5)</div>', unsafe_allow_html=True)
    fc1, fc2, fc3 = st.columns([2,1,2])
    for col, abbr, form, color in [(fc1, g["away"]["abbr"], g["form"]["away"], "#2ecc71"),
                                    (fc3, g["home"]["abbr"], g["form"]["home"], "#3498db")]:
        w = form.count("W")
        with col:
            st.markdown(f'<div style="text-align:center;"><div style="font-weight:600;color:{color};">{abbr}</div>'
                        f'<div style="font-size:12px;color:#555;">{w}-{5-w} L5</div>'
                        f'<div style="margin-top:4px;">{form_dots(form)}</div></div>', unsafe_allow_html=True)
    with fc2:
        st.markdown('<div style="text-align:center;color:#333;padding-top:10px;font-size:18px;">vs</div>', unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # LIVE GAME DASHBOARD — full scoreboard + prediction comparison
    if g["status"] in ("inprogress", "halftime"):
        render_live_game_dashboard(g, pred)

    # WIN PROB
    st.markdown('<div class="section-header">Win Probability</div>', unsafe_allow_html=True)
    render_prob_bar("Full Game", g["away"]["abbr"], g["home"]["abbr"], pred["game_win"]["away"], pred["game_win"]["home"])

    # QUARTER PREDS
    st.markdown('<div class="section-header">Quarter-by-Quarter Win Chances</div>', unsafe_allow_html=True)
    q_data = [("Q1",pred["q1"]),("1st Half",pred["half"]),("Q3",pred["q3"]),("Q4",pred["q4"])]
    qcols = st.columns(4)
    for i,(lbl,qp) in enumerate(q_data):
        win = g["home"]["abbr"] if qp["home"] >= qp["away"] else g["away"]["abbr"]
        wc  = "#3498db" if win == g["home"]["abbr"] else "#2ecc71"
        with qcols[i]:
            st.markdown(f'<div class="qtr-card"><div class="qtr-title">{lbl}</div>'
                        f'<div class="qtr-winner" style="color:{wc};">{win}</div>'
                        f'<div class="qtr-prob">{max(qp["home"],qp["away"])}%</div>'
                        f'<div style="font-size:10px;color:#444;margin-top:3px;">{g["away"]["abbr"]} {qp["away"]}% / {g["home"]["abbr"]} {qp["home"]}%</div></div>', unsafe_allow_html=True)

    st.markdown("")

    # PPQ + O/U
    lc, rc = st.columns(2)
    with lc:
        st.markdown('<div class="section-header">Pts Per Quarter</div>', unsafe_allow_html=True)
        m1, m2 = st.columns(2)
        for col, abbr, qpts in [(m1, g["away"]["abbr"], pred["away_qpts"]), (m2, g["home"]["abbr"], pred["home_qpts"])]:
            with col:
                st.markdown(f'<div class="metric-card"><div class="metric-label">{abbr} / Qtr</div>'
                            f'<div class="metric-value">{qpts}</div>'
                            f'<div class="metric-sub">~{qpts*4} total</div></div>', unsafe_allow_html=True)
    with rc:
        st.markdown('<div class="section-header">Over / Under</div>', unsafe_allow_html=True)
        o1, o2 = st.columns(2)
        with o1:
            st.markdown(f'<div class="ou-card ou-over"><div class="ou-label">OVER {pred["ou_line"]}</div>'
                        f'<div class="ou-value">{pred["over_pct"]}%</div>'
                        f'<div class="ou-sub">Proj: {pred["total_proj"]} pts</div></div>', unsafe_allow_html=True)
        with o2:
            st.markdown(f'<div class="ou-card ou-under"><div class="ou-label">UNDER {pred["ou_line"]}</div>'
                        f'<div class="ou-value">{pred["under_pct"]}%</div>'
                        f'<div class="ou-sub">Line: {pred["ou_line"]}</div></div>', unsafe_allow_html=True)

    st.markdown("")

    # FIRST TO REACH
    st.markdown('<div class="section-header">First to Reach (Q1 Pace)</div>', unsafe_allow_html=True)
    st.markdown('<div style="border:1px solid rgba(255,255,255,0.1);border-radius:10px;overflow:hidden;">', unsafe_allow_html=True)
    for pts, info in pred["milestones"].items():
        tc = "#3498db" if info["team"] == g["home"]["abbr"] else "#2ecc71"
        st.markdown(f'<div class="milestone-row">'
                    f'<span style="font-weight:600;color:#fff;">{pts} pts</span>'
                    f'<span style="font-weight:600;color:{tc};">{info["team"]} ({info["prob"]}%)</span>'
                    f'<span style="color:#444;font-size:12px;">~{info["est_min"]} min</span></div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("")

    # OT
    ot_c = "#e74c3c" if pred["ot_prob"] > 12 else "#666"
    st.markdown(f'<div style="display:flex;justify-content:space-between;align-items:center;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:10px;padding:12px 16px;">'
                f'<span style="font-size:14px;color:#aaa;">⏱ Overtime probability</span>'
                f'<span style="font-size:18px;font-weight:700;color:{ot_c};">{pred["ot_prob"]}%</span></div>', unsafe_allow_html=True)

    st.markdown("")

    # STATS
    st.markdown('<div class="section-header">Key Stat Comparison</div>', unsafe_allow_html=True)
    hs, as_ = g["stats"]["home"], g["stats"]["away"]
    st.markdown(f'<div style="border:1px solid rgba(255,255,255,0.1);border-radius:10px;padding:8px 16px;">'
                f'<div style="display:flex;justify-content:space-between;font-size:11px;color:#444;margin-bottom:8px;font-weight:600;">'
                f'<span>{g["away"]["abbr"]}</span><span>STAT</span><span>{g["home"]["abbr"]}</span></div>', unsafe_allow_html=True)
    for lbl, av, hv in [("FG%",f'{as_["fg_pct"]}%',f'{hs["fg_pct"]}%'),
                         ("3PT%",f'{as_["fg3_pct"]}%',f'{hs["fg3_pct"]}%'),
                         ("Off Rtg",as_["ortg"],hs["ortg"]),("Def Rtg",as_["drtg"],hs["drtg"]),
                         ("Bench Pts",as_["bench_pts"],hs["bench_pts"]),
                         ("Paint Pts",as_["paint_pts"],hs["paint_pts"]),("Pace",as_["pace"],hs["pace"])]:
        st.markdown(f'<div class="stat-row"><div class="val-away">{av}</div><div class="stat-name">{lbl}</div><div class="val-home">{hv}</div></div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # PROB DETAIL
    st.markdown("")
    st.markdown('<div class="section-header">Win Probability Detail</div>', unsafe_allow_html=True)
    for lbl, qp in q_data:
        render_prob_bar(lbl, g["away"]["abbr"], g["home"]["abbr"], qp["away"], qp["home"])

    # AI ANALYSIS — live-aware
    st.markdown("")
    is_live = g["status"] in ("inprogress", "halftime")
    ai_section_label = "🔴 Live AI Analysis" if is_live else "🤖 AI Analysis"
    st.markdown(f'<div class="section-header">{ai_section_label}</div>', unsafe_allow_html=True)

    if not st.session_state.ai_key:
        st.caption("Add your Anthropic API key in the sidebar to enable AI analysis.")
    else:
        btn_label = "🔴 Get Live Analysis ▶" if is_live else "Generate AI Analysis ▶"
        if st.button(btn_label, type="primary", use_container_width=True, key=f"ai_btn_{g['id']}"):
            with st.spinner("Claude is analyzing..." if not is_live else "Claude is analyzing the live game..."):
                if is_live:
                    analysis = get_live_ai_analysis(g, pred)
                else:
                    analysis = get_ai_analysis(g, pred)
            st.session_state[f"ai_{g['id']}"] = analysis

        ai_cache_key = f"ai_{g['id']}"
        if ai_cache_key in st.session_state:
            cached = st.session_state[ai_cache_key]
            st.markdown(f'<div class="ai-box">{cached}</div>', unsafe_allow_html=True)

    # TRACK PREDICTION BUTTON
    st.markdown("")
    track_key = f"tracked_{g['id']}"
    already_tracked = any(p["game_id"] == g["id"] for p in st.session_state.pred_history)
    if already_tracked:
        st.success("✓ Prediction tracked — results will auto-update when game finishes.")
    elif g["status"] != "closed":
        if st.button("📊 Track This Prediction", use_container_width=True, key=track_key):
            record_prediction(g, pred)
            st.success("Prediction saved! Results will update when the game finishes.")
            st.rerun()

    # SUMMARY TABLE + ACCURACY
    st.markdown("---")

    # Auto-update settled predictions
    update_prediction_results(games)

    st.markdown("#### 📊 Prediction Accuracy Tracker")
    render_accuracy_dashboard()

    st.markdown("")
    st.markdown("#### 🗓 All Games — Prediction Summary")
    rows = []
    for gg in games:
        pp  = calculate_predictions(gg)
        fav = gg["home"]["abbr"] if pp["game_win"]["home"] >= pp["game_win"]["away"] else gg["away"]["abbr"]
        rows.append({
            "Matchup":    f'{gg["away"]["abbr"]} @ {gg["home"]["abbr"]}',
            "Status":     gg["status"].title(),
            "Favorite":   fav,
            "Win %":      f'{max(pp["game_win"]["home"],pp["game_win"]["away"])}%',
            "Q1 Win":     gg["home"]["abbr"] if pp["q1"]["home"] >= pp["q1"]["away"] else gg["away"]["abbr"],
            "Q4 Win":     gg["home"]["abbr"] if pp["q4"]["home"] >= pp["q4"]["away"] else gg["away"]["abbr"],
            "Proj Total": pp["total_proj"],
            "O/U Line":   pp["ou_line"],
            "Over %":     f'{pp["over_pct"]}%',
            "OT Risk":    f'{pp["ot_prob"]}%',
            "Confidence": pp["confidence"].title(),
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)


st.markdown("---")
st.markdown('<div style="text-align:center;color:#333;font-size:12px;padding:8px 0 16px;">NBA Prediction Engine · BallDontLie + Claude AI · For entertainment purposes only</div>', unsafe_allow_html=True)
