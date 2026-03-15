import streamlit as st
import requests
import anthropic
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
SPORTRADAR_KEY = os.getenv("SPORTRADAR_API_KEY", "")
ANTHROPIC_KEY  = os.getenv("ANTHROPIC_API_KEY", "")

SR_BASE        = "https://api.sportradar.com/nba/trial/v8/en"
SEASON_YEAR    = 2025
SEASON_TYPE    = "REG"

st.set_page_config(
    page_title="NBA Prediction Engine",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────
# STYLES
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.main-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    border-radius: 12px;
    padding: 24px 28px;
    margin-bottom: 20px;
    color: white;
}
.main-header h1 { font-size: 26px; font-weight: 700; margin:0; letter-spacing:-0.3px; }
.main-header p  { font-size: 13px; color: #aaaacc; margin: 6px 0 0; }

.game-card {
    background: white;
    border: 1px solid #e8e8ee;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 10px;
    cursor: pointer;
    transition: all 0.2s;
}
.game-card:hover { border-color: #4f8ef7; box-shadow: 0 2px 8px rgba(79,142,247,0.15); }
.game-card.live { border-left: 4px solid #e74c3c; }
.game-card.selected { border-color: #4f8ef7; background: #f0f6ff; }

.live-badge {
    background: #fff0f0; color: #e74c3c;
    border-radius: 6px; padding: 2px 8px;
    font-size: 11px; font-weight: 600;
}
.sched-badge {
    background: #f4f4f8; color: #666;
    border-radius: 6px; padding: 2px 8px; font-size: 11px;
}

.metric-card {
    background: #f8f9ff;
    border: 1px solid #e8e8ee;
    border-radius: 10px;
    padding: 14px 16px;
    text-align: center;
}
.metric-value { font-size: 22px; font-weight: 700; color: #1a1a2e; }
.metric-label { font-size: 11px; color: #888; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.05em; }
.metric-sub   { font-size: 11px; color: #aaa; margin-top: 3px; }

.prob-container { margin: 8px 0; }
.prob-label { font-size: 13px; color: #555; margin-bottom: 4px; }
.prob-bar   {
    display: flex; height: 24px; border-radius: 6px;
    overflow: hidden; border: 1px solid #e8e8ee;
}
.prob-away { background: #2ecc71; display:flex; align-items:center; padding-left:8px; }
.prob-home { background: #3498db; display:flex; align-items:center; justify-content:flex-end; padding-right:8px; }
.prob-text { font-size: 11px; font-weight: 600; color: white; }

.qtr-card {
    background: #f8f9ff;
    border: 1px solid #e8e8ee;
    border-radius: 10px;
    padding: 12px;
    text-align: center;
}
.qtr-title   { font-size: 11px; color: #888; margin-bottom: 6px; font-weight: 600; text-transform: uppercase; }
.qtr-winner  { font-size: 13px; font-weight: 700; margin-top: 4px; }
.qtr-prob    { font-size: 12px; color: #666; margin-top: 2px; }

.ou-card {
    border-radius: 10px;
    padding: 14px;
    text-align: center;
    border: 1px solid #e8e8ee;
}
.ou-over  { background: #eef9f0; border-color: #2ecc71; }
.ou-under { background: #f8f9ff; }
.ou-label { font-size: 11px; font-weight: 600; color: #888; text-transform: uppercase; margin-bottom: 4px; }
.ou-value { font-size: 24px; font-weight: 700; }
.ou-over .ou-value  { color: #2ecc71; }
.ou-under .ou-value { color: #666; }
.ou-sub { font-size: 12px; color: #888; margin-top: 3px; }

.milestone-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 8px 12px;
    border-bottom: 1px solid #f0f0f5;
    font-size: 13px;
}
.milestone-row:last-child { border-bottom: none; }

.stat-row {
    display: grid; grid-template-columns: 1fr auto 1fr;
    gap: 8px; align-items: center; padding: 6px 0;
    border-bottom: 1px solid #f0f0f5; font-size: 13px;
}
.stat-row:last-child { border-bottom: none; }
.val-away { text-align: right; font-weight: 600; color: #2ecc71; }
.val-home { text-align: left;  font-weight: 600; color: #3498db; }
.stat-name { text-align: center; color: #999; font-size: 11px; }

.form-dot {
    display: inline-block; width: 10px; height: 10px;
    border-radius: 50%; margin: 0 2px;
}
.form-w { background: #2ecc71; }
.form-l { background: #e74c3c; }

.injury-box {
    background: #fff8e6;
    border: 1px solid #f0a500;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    color: #b07800;
    margin-bottom: 12px;
}

.conf-high { background:#eef9f0; color:#1a7a3c; border-radius:6px; padding:2px 10px; font-size:11px; font-weight:600; }
.conf-med  { background:#fff8e6; color:#b07800; border-radius:6px; padding:2px 10px; font-size:11px; font-weight:600; }
.conf-low  { background:#f4f4f8; color:#666;    border-radius:6px; padding:2px 10px; font-size:11px; font-weight:600; }

.section-header {
    font-size: 11px; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.06em; color: #888; margin: 16px 0 8px;
}
.ai-box {
    background: #f8f9ff;
    border: 1px solid #d0d8f0;
    border-radius: 10px;
    padding: 16px;
    font-size: 14px;
    line-height: 1.7;
    color: #333;
    margin-top: 12px;
}
.divider { height: 1px; background: #f0f0f5; margin: 12px 0; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SPORTRADAR DATA FETCHING
# ─────────────────────────────────────────────

@st.cache_data(ttl=60)
def fetch_daily_schedule(date_str: str):
    """Fetch games for a given date (YYYY/MM/DD)."""
    if not SPORTRADAR_KEY:
        return None
    url = f"{SR_BASE}/games/{date_str}/schedule.json?api_key={SPORTRADAR_KEY}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


@st.cache_data(ttl=30)
def fetch_live_scoreboard():
    """Fetch today's live/scheduled scoreboard."""
    if not SPORTRADAR_KEY:
        return None
    url = f"{SR_BASE}/games/today/schedule.json?api_key={SPORTRADAR_KEY}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


@st.cache_data(ttl=300)
def fetch_team_profile(team_id: str):
    if not SPORTRADAR_KEY:
        return None
    url = f"{SR_BASE}/teams/{team_id}/profile.json?api_key={SPORTRADAR_KEY}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


@st.cache_data(ttl=120)
def fetch_game_boxscore(game_id: str):
    if not SPORTRADAR_KEY:
        return None
    url = f"{SR_BASE}/games/{game_id}/boxscore.json?api_key={SPORTRADAR_KEY}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


@st.cache_data(ttl=600)
def fetch_standings():
    if not SPORTRADAR_KEY:
        return None
    url = f"{SR_BASE}/seasons/{SEASON_YEAR}/{SEASON_TYPE}/standings.json?api_key={SPORTRADAR_KEY}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


@st.cache_data(ttl=600)
def fetch_team_season_stats(team_id: str):
    if not SPORTRADAR_KEY:
        return None
    url = f"{SR_BASE}/seasons/{SEASON_YEAR}/{SEASON_TYPE}/teams/{team_id}/statistics.json?api_key={SPORTRADAR_KEY}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


@st.cache_data(ttl=600)
def fetch_h2h(team_id_home: str, team_id_away: str):
    """Head-to-head from team schedule."""
    if not SPORTRADAR_KEY:
        return None
    url = f"{SR_BASE}/teams/{team_id_home}/versus/{team_id_away}/matches.json?api_key={SPORTRADAR_KEY}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


# ─────────────────────────────────────────────
# DEMO DATA (used when no API key is set)
# ─────────────────────────────────────────────

DEMO_GAMES = [
    {
        "id": "demo-okc-min", "status": "inprogress", "quarter": 2, "clock": "HT",
        "home": {"abbr": "OKC", "name": "Oklahoma City Thunder", "id": "583ecda3-fb46-11e1-82cb-f4ce4684ea4c"},
        "away": {"abbr": "MIN", "name": "Minnesota Timberwolves", "id": "583eca88-fb46-11e1-82cb-f4ce4684ea4c"},
        "score": {"home": 47, "away": 53},
        "q_scores": {"1": {"home": 23, "away": 22}, "2": {"home": 24, "away": 31}},
        "win_prob": {"home": 38, "away": 62},
        "time": "HT",
        "stats": {
            "home": {"fg_pct": 32.1, "fg3_pct": 31.6, "reb": 27, "to": 2, "ortg": 91, "drtg": 108, "bench_pts": 25, "paint_pts": 22, "pace": 51.6},
            "away": {"fg_pct": 52.6, "fg3_pct": 47.4, "reb": 34, "to": 12, "ortg": 108, "drtg": 91, "bench_pts": 18, "paint_pts": 18, "pace": 49.1}
        },
        "form": {"home": ["W","W","L","W","W"], "away": ["W","L","W","W","W"]},
        "injuries": {"home": [], "away": []},
        "ou_line": 218.5,
        "top_players": {
            "home": [{"name":"SGA","pts":4,"reb":1,"ast":4},{"name":"Chet H","pts":11,"reb":6,"ast":1}],
            "away": [{"name":"Ant Edwards","pts":11,"reb":5,"ast":2},{"name":"J. Randle","pts":17,"reb":5,"ast":3}]
        }
    },
    {
        "id": "demo-cle-dal", "status": "scheduled",
        "home": {"abbr": "CLE", "name": "Cleveland Cavaliers", "id": "583ec825-fb46-11e1-82cb-f4ce4684ea4c"},
        "away": {"abbr": "DAL", "name": "Dallas Mavericks", "id": "583ecf50-fb46-11e1-82cb-f4ce4684ea4c"},
        "score": None, "q_scores": {},
        "win_prob": {"home": 90.7, "away": 9.3},
        "time": "8:30 PM",
        "stats": {
            "home": {"fg_pct": 49.2, "fg3_pct": 38.7, "reb": 48, "to": 10, "ortg": 122, "drtg": 107, "bench_pts": 48, "paint_pts": 54, "pace": 98.4},
            "away": {"fg_pct": 43.1, "fg3_pct": 35.2, "reb": 40, "to": 16, "ortg": 108, "drtg": 119, "bench_pts": 32, "paint_pts": 40, "pace": 97.1}
        },
        "form": {"home": ["W","W","W","W","W"], "away": ["L","L","L","W","L"]},
        "injuries": {"home": [], "away": ["Kyrie Irving (OUT)", "Luka Doncic (OUT)"]},
        "ou_line": 222.5,
        "top_players": {"home": [], "away": []}
    },
    {
        "id": "demo-mil-ind", "status": "scheduled",
        "home": {"abbr": "MIL", "name": "Milwaukee Bucks", "id": "583ecefd-fb46-11e1-82cb-f4ce4684ea4c"},
        "away": {"abbr": "IND", "name": "Indiana Pacers", "id": "583ec70e-fb46-11e1-82cb-f4ce4684ea4c"},
        "score": None, "q_scores": {},
        "win_prob": {"home": 75.7, "away": 24.3},
        "time": "8:30 PM",
        "stats": {
            "home": {"fg_pct": 47.3, "fg3_pct": 36.9, "reb": 47, "to": 12, "ortg": 118, "drtg": 111, "bench_pts": 44, "paint_pts": 52, "pace": 103.1},
            "away": {"fg_pct": 45.1, "fg3_pct": 38.4, "reb": 42, "to": 15, "ortg": 114, "drtg": 118, "bench_pts": 41, "paint_pts": 46, "pace": 106.8}
        },
        "form": {"home": ["W","W","W","L","W"], "away": ["L","W","L","W","L"]},
        "injuries": {"home": [], "away": ["T.J. McConnell (OUT)"]},
        "ou_line": 232.5,
        "top_players": {"home": [], "away": []}
    },
    {
        "id": "demo-phi-por", "status": "scheduled",
        "home": {"abbr": "PHI", "name": "Philadelphia 76ers", "id": "583ec87d-fb46-11e1-82cb-f4ce4684ea4c"},
        "away": {"abbr": "POR", "name": "Portland Trail Blazers", "id": "583ed056-fb46-11e1-82cb-f4ce4684ea4c"},
        "score": None, "q_scores": {},
        "win_prob": {"home": 25.4, "away": 74.6},
        "time": "11:00 PM",
        "stats": {
            "home": {"fg_pct": 43.5, "fg3_pct": 34.8, "reb": 41, "to": 14, "ortg": 109, "drtg": 117, "bench_pts": 34, "paint_pts": 42, "pace": 97.8},
            "away": {"fg_pct": 46.3, "fg3_pct": 37.1, "reb": 44, "to": 12, "ortg": 116, "drtg": 109, "bench_pts": 40, "paint_pts": 50, "pace": 101.4}
        },
        "form": {"home": ["L","L","W","L","L"], "away": ["W","W","W","L","W"]},
        "injuries": {"home": ["Joel Embiid (OUT)", "Paul George (OUT)"], "away": []},
        "ou_line": 224.0,
        "top_players": {"home": [], "away": []}
    },
    {
        "id": "demo-nyk-gsw", "status": "scheduled",
        "home": {"abbr": "NYK", "name": "New York Knicks", "id": "583ec70e-fb46-11e1-82cb-f4ce4684ea4c"},
        "away": {"abbr": "GSW", "name": "Golden State Warriors", "id": "583ec773-fb46-11e1-82cb-f4ce4684ea4c"},
        "score": None, "q_scores": {},
        "win_prob": {"home": 88.1, "away": 11.9},
        "time": "1:00 AM",
        "stats": {
            "home": {"fg_pct": 47.8, "fg3_pct": 37.3, "reb": 46, "to": 11, "ortg": 119, "drtg": 108, "bench_pts": 46, "paint_pts": 52, "pace": 99.7},
            "away": {"fg_pct": 43.2, "fg3_pct": 34.6, "reb": 38, "to": 15, "ortg": 108, "drtg": 116, "bench_pts": 33, "paint_pts": 42, "pace": 100.2}
        },
        "form": {"home": ["W","W","W","L","W"], "away": ["L","L","W","L","L"]},
        "injuries": {"home": [], "away": ["Stephen Curry (GTD)", "Draymond Green (OUT)"]},
        "ou_line": 226.5,
        "top_players": {"home": [], "away": []}
    },
    {
        "id": "demo-tor-det", "status": "scheduled",
        "home": {"abbr": "TOR", "name": "Toronto Raptors", "id": "583ecda3-fb46-11e1-82cb-f4ce4684ea4c"},
        "away": {"abbr": "DET", "name": "Detroit Pistons", "id": "583ec928-fb46-11e1-82cb-f4ce4684ea4c"},
        "score": None, "q_scores": {},
        "win_prob": {"home": 39.7, "away": 60.3},
        "time": "8:30 PM",
        "stats": {
            "home": {"fg_pct": 44.2, "fg3_pct": 34.1, "reb": 43, "to": 13, "ortg": 108, "drtg": 114, "bench_pts": 38, "paint_pts": 44, "pace": 99.2},
            "away": {"fg_pct": 47.1, "fg3_pct": 37.2, "reb": 45, "to": 11, "ortg": 115, "drtg": 110, "bench_pts": 42, "paint_pts": 48, "pace": 102.3}
        },
        "form": {"home": ["L","W","L","L","W"], "away": ["W","W","L","W","W"]},
        "injuries": {"home": ["Immanuel Quickley (GTD)"], "away": []},
        "ou_line": 225.5,
        "top_players": {"home": [], "away": []}
    },
]


# ─────────────────────────────────────────────
# PREDICTION ENGINE
# ─────────────────────────────────────────────

def calculate_predictions(game: dict) -> dict:
    hp = game["win_prob"]["home"] / 100
    ap = game["win_prob"]["away"] / 100
    spread = abs(hp - 0.5)

    # Quarter win probabilities (regress toward 0.5 — early qtrs more random)
    q1hp   = hp * 0.52 + 0.5 * 0.48
    halfhp = hp * 0.65 + 0.5 * 0.35
    q3hp   = hp * 0.56 + 0.5 * 0.44
    q4hp   = hp * 0.68 + 0.5 * 0.32

    # Pace average
    avg_pace = (game["stats"]["home"]["pace"] + game["stats"]["away"]["pace"]) / 2

    # Quarter point projections
    ou        = game["ou_line"]
    q_base    = ou / 8
    home_ortg = game["stats"]["home"]["ortg"]
    away_ortg = game["stats"]["away"]["ortg"]
    home_qpts = round(q_base * (0.5 + (home_ortg - 110) / 220))
    away_qpts = round(q_base * (0.5 + (away_ortg - 110) / 220))
    total_proj = (home_qpts + away_qpts) * 4

    # Over/under
    diff = total_proj - ou
    over_pct  = min(80, max(20, round(50 + diff * 3)))
    under_pct = 100 - over_pct

    # OT probability
    ot_prob = max(3, round((1 - spread * 3.2) * 14))

    # Confidence
    if spread > 0.30: conf = "high"
    elif spread > 0.15: conf = "med"
    else: conf = "low"

    # Form score
    def form_score(form_list):
        w = sum(1 for r in form_list if r == "W")
        return w / len(form_list) if form_list else 0.5

    home_form = form_score(game["form"]["home"])
    away_form = form_score(game["form"]["away"])

    # H2H adjustment (simplified: who has better form)
    h2h_note = (
        f"{game['home']['abbr']} leads L5 form ({int(home_form*5)}-{5-int(home_form*5)})"
        if home_form > away_form
        else f"{game['away']['abbr']} leads L5 form ({int(away_form*5)}-{5-int(away_form*5)})"
    )

    # First-to-reach per quarter
    total_q = home_qpts + away_qpts
    home_share = home_qpts / total_q if total_q > 0 else 0.5
    milestones = {}
    for pts in [10, 15, 20, 25, 30]:
        adj_share = home_share + (hp - 0.5) * 0.04
        if adj_share > 0.5:
            milestones[pts] = {
                "team": game["home"]["abbr"],
                "prob": round(adj_share * 100),
                "est_min": round(pts / (total_q / 12), 1)
            }
        else:
            milestones[pts] = {
                "team": game["away"]["abbr"],
                "prob": round((1 - adj_share) * 100),
                "est_min": round(pts / (total_q / 12), 1)
            }

    return {
        "game_win":  {"home": round(hp * 100), "away": round(ap * 100)},
        "q1":        {"home": round(q1hp * 100), "away": round((1-q1hp) * 100)},
        "half":      {"home": round(halfhp * 100), "away": round((1-halfhp) * 100)},
        "q3":        {"home": round(q3hp * 100), "away": round((1-q3hp) * 100)},
        "q4":        {"home": round(q4hp * 100), "away": round((1-q4hp) * 100)},
        "ot_prob":   ot_prob,
        "home_qpts": home_qpts,
        "away_qpts": away_qpts,
        "total_proj": round(total_proj),
        "ou_line":   ou,
        "over_pct":  over_pct,
        "under_pct": under_pct,
        "confidence": conf,
        "milestones": milestones,
        "h2h_note":  h2h_note,
        "avg_pace":  round(avg_pace, 1),
        "home_form": home_form,
        "away_form": away_form,
    }


# ─────────────────────────────────────────────
# AI ANALYSIS
# ─────────────────────────────────────────────

def get_ai_analysis(game: dict, pred: dict) -> str:
    if not ANTHROPIC_KEY:
        return ("⚠ No Anthropic API key set. Add ANTHROPIC_API_KEY to your .env file "
                "or Streamlit secrets to enable AI analysis.")
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

        injuries_all = game["injuries"]["home"] + game["injuries"]["away"]
        injury_str   = ", ".join(injuries_all) if injuries_all else "None reported"

        prompt = f"""You are an elite NBA analyst. Analyze this matchup in 6-8 sharp sentences.

Game: {game['away']['name']} ({game['away']['abbr']}) @ {game['home']['name']} ({game['home']['abbr']})
Status: {'LIVE Q' + str(game['quarter']) + ' ' + game['clock'] + ' — Score: ' + game['away']['abbr'] + ' ' + str(game['score']['away']) + ' - ' + game['home']['abbr'] + ' ' + str(game['score']['home']) if game['status']=='inprogress' else 'Scheduled at ' + game['time']}
Win probability: {game['away']['abbr']} {pred['game_win']['away']}% | {game['home']['abbr']} {pred['game_win']['home']}%

{game['away']['abbr']} stats: FG {game['stats']['away']['fg_pct']}%, 3PT {game['stats']['away']['fg3_pct']}%, OffRtg {game['stats']['away']['ortg']}, DefRtg {game['stats']['away']['drtg']}, Pace {game['stats']['away']['pace']}, Form: {'-'.join(game['form']['away'])}
{game['home']['abbr']} stats: FG {game['stats']['home']['fg_pct']}%, 3PT {game['stats']['home']['fg3_pct']}%, OffRtg {game['stats']['home']['ortg']}, DefRtg {game['stats']['home']['drtg']}, Pace {game['stats']['home']['pace']}, Form: {'-'.join(game['form']['home'])}

O/U Line: {pred['ou_line']} | Projected total: {pred['total_proj']} pts | Over: {pred['over_pct']}%
Injuries: {injury_str}
Q1 win prob: {game['away']['abbr']} {pred['q1']['away']}% / {game['home']['abbr']} {pred['q1']['home']}%
Q4 win prob: {game['away']['abbr']} {pred['q4']['away']}% / {game['home']['abbr']} {pred['q4']['home']}%
OT probability: {pred['ot_prob']}%

Cover: (1) key matchup storyline, (2) biggest factor driving the winner prediction, (3) Q1 momentum, (4) O/U lean and why, (5) OT risk, (6) player injury impact if any. Be direct, data-driven, analytical. No fluff."""

        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        return msg.content[0].text
    except Exception as e:
        return f"AI analysis failed: {str(e)}"


# ─────────────────────────────────────────────
# RENDERING HELPERS
# ─────────────────────────────────────────────

def render_prob_bar(label: str, away_abbr: str, home_abbr: str, away_pct: int, home_pct: int):
    aw = max(6, away_pct)
    hw = max(6, home_pct)
    st.markdown(f"""
    <div class="prob-container">
        <div class="prob-label"><b>{label}</b> &nbsp;
            <span style="color:#2ecc71">{away_abbr} {away_pct}%</span> vs
            <span style="color:#3498db">{home_abbr} {home_pct}%</span>
        </div>
        <div class="prob-bar">
            <div class="prob-away" style="width:{aw}%"><span class="prob-text">{away_abbr}</span></div>
            <div class="prob-home" style="width:{hw}%"><span class="prob-text">{home_abbr}</span></div>
        </div>
    </div>""", unsafe_allow_html=True)


def form_dots(form_list: list) -> str:
    dots = ""
    for r in form_list:
        cls = "form-w" if r == "W" else "form-l"
        dots += f'<span class="form-dot {cls}" title="{r}"></span>'
    return dots


def conf_badge(conf: str) -> str:
    labels = {"high": "High Confidence", "med": "Moderate", "low": "Low Confidence"}
    return f'<span class="{conf}-badge conf-{conf}">{labels.get(conf, conf)}</span>'


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("### ⚙ Configuration")

    api_key_input = st.text_input(
        "Anthropic API Key", value=ANTHROPIC_KEY, type="password",
        help="Required for AI deep analysis"
    )
    if api_key_input:
        ANTHROPIC_KEY = api_key_input

    sr_key_input = st.text_input(
        "SportRadar API Key", value=SPORTRADAR_KEY, type="password",
        help="Required for live NBA data (trial key works)"
    )
    if sr_key_input:
        SPORTRADAR_KEY = sr_key_input

    st.markdown("---")
    st.markdown("### 📅 Date")
    selected_date = st.date_input("Select date", value=datetime.today())

    st.markdown("---")
    st.markdown("### 🔍 Filters")
    status_filter = st.multiselect(
        "Game status",
        ["scheduled", "inprogress", "halftime", "closed"],
        default=["scheduled", "inprogress", "halftime"]
    )

    st.markdown("---")
    st.markdown("### ℹ About")
    st.markdown("""
**NBA Prediction Engine**
- Live SportRadar data
- Quarter-by-quarter predictions
- O/U analysis
- First-to-reach milestones
- AI deep analysis (Claude)

*Demo mode active when no API key is set.*
    """)

    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


# ─────────────────────────────────────────────
# MAIN HEADER
# ─────────────────────────────────────────────

st.markdown("""
<div class="main-header">
    <h1>🏀 NBA Prediction Engine</h1>
    <p>Live data · Quarter-by-quarter predictions · Over/Under · First-to-reach · AI-powered deep analysis</p>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# LOAD GAMES
# ─────────────────────────────────────────────

using_demo = not SPORTRADAR_KEY

if not using_demo:
    date_str   = selected_date.strftime("%Y/%m/%d")
    raw        = fetch_daily_schedule(date_str)
    live_raw   = fetch_live_scoreboard()

    games = []
    if raw and "games" in raw:
        for g in raw.get("games", []):
            status   = g.get("status", "scheduled").lower()
            if status not in status_filter:
                continue
            home_id  = g.get("home", {}).get("id", "")
            away_id  = g.get("away", {}).get("id", "")
            home_sts = fetch_team_season_stats(home_id) or {}
            away_sts = fetch_team_season_stats(away_id) or {}

            def extract_stats(d):
                own = d.get("own_record", {}).get("total", {})
                return {
                    "fg_pct":    round(own.get("field_goals_pct", 45.0), 1),
                    "fg3_pct":   round(own.get("three_points_pct", 36.0), 1),
                    "reb":       round(own.get("rebounds", 44), 1),
                    "to":        round(own.get("turnovers", 13), 1),
                    "ortg":      round(own.get("offensive_rating", 112), 1),
                    "drtg":      round(own.get("defensive_rating", 112), 1),
                    "bench_pts": round(own.get("bench_points", 36), 1),
                    "paint_pts": round(own.get("points_in_paint", 46), 1),
                    "pace":      round(own.get("pace", 100.0), 1),
                }

            q_scores = {}
            box = fetch_game_boxscore(g.get("id","")) or {}
            for period in box.get("periods", []):
                pnum = str(period.get("number",""))
                q_scores[pnum] = {
                    "home": period.get("home_points", 0),
                    "away": period.get("away_points", 0)
                }

            # Win probability
            probs = g.get("win_probability", [{}])
            home_prob = 50
            if isinstance(probs, list) and probs:
                for p in probs:
                    if p.get("home", True):
                        home_prob = round(p.get("probability", 0.5) * 100)

            score_home = g.get("home_points", 0)
            score_away = g.get("away_points", 0)

            games.append({
                "id":       g.get("id"),
                "status":   status,
                "quarter":  g.get("quarter", 1),
                "clock":    g.get("clock", ""),
                "home":     {"abbr": g.get("home",{}).get("alias","HME"), "name": g.get("home",{}).get("name","Home"), "id": home_id},
                "away":     {"abbr": g.get("away",{}).get("alias","AWY"), "name": g.get("away",{}).get("name","Away"), "id": away_id},
                "score":    {"home": score_home, "away": score_away},
                "q_scores": q_scores,
                "win_prob": {"home": home_prob, "away": 100 - home_prob},
                "time":     g.get("scheduled", "TBD"),
                "stats":    {"home": extract_stats(home_sts), "away": extract_stats(away_sts)},
                "form":     {"home": ["W","W","L","W","W"], "away": ["W","L","W","W","W"]},  # from standings
                "injuries": {"home": [], "away": []},
                "ou_line":  225.0,
                "top_players": {"home": [], "away": []},
            })
else:
    games = DEMO_GAMES
    st.info("🎮 **Demo mode** — Showing sample data. Add your SportRadar API key in the sidebar for live NBA data.", icon="ℹ")


# ─────────────────────────────────────────────
# GAME SELECTOR + PREDICTION DISPLAY
# ─────────────────────────────────────────────

if not games:
    st.warning("No games found for the selected date. Try a different date or check your API key.")
    st.stop()

# Build game options
def game_label(g):
    status_emoji = "🔴" if g["status"] in ("inprogress","halftime") else "🕐"
    score_part   = f"  {g['score']['away']}–{g['score']['home']}" if g["score"] and g["status"] in ("inprogress","halftime","closed") else ""
    return f"{status_emoji}  {g['away']['abbr']} @ {g['home']['abbr']}{score_part}"

col_left, col_right = st.columns([1, 2], gap="large")

with col_left:
    st.markdown("#### 📋 Games")

    # Summary metrics
    live_count  = sum(1 for g in games if g["status"] in ("inprogress","halftime"))
    sched_count = sum(1 for g in games if g["status"] == "scheduled")

    m1, m2, m3 = st.columns(3)
    m1.metric("Total", len(games))
    m2.metric("Live",  live_count)
    m3.metric("Up Next", sched_count)

    st.markdown("---")

    # Game selection
    selected_idx = st.radio(
        "Select game",
        range(len(games)),
        format_func=lambda i: game_label(games[i]),
        label_visibility="collapsed"
    )

    selected_game = games[selected_idx]

    # Show live score card for selected
    if selected_game["status"] in ("inprogress", "halftime"):
        g = selected_game
        status_text = f"LIVE Q{g['quarter']} {g['clock']}" if g['clock'] != 'HT' else "HALFTIME"
        st.markdown(f"""
        <div class="game-card live" style="margin-top:12px;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <div style="font-size:13px;color:#555;">{g['away']['name']}</div>
                    <div style="font-size:13px;color:#555;">{g['home']['name']}</div>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:26px;font-weight:700;color:#1a1a2e;">{g['score']['away']}–{g['score']['home']}</div>
                    <span class="live-badge">● {status_text}</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


with col_right:
    g    = selected_game
    pred = calculate_predictions(g)

    # Header
    all_injuries = g["injuries"]["home"] + g["injuries"]["away"]
    conf_label   = {"high": "High Confidence", "med": "Moderate", "low": "Low Confidence"}[pred["confidence"]]
    conf_color   = {"high": "#1a7a3c", "med": "#b07800", "low": "#888"}[pred["confidence"]]
    conf_bg      = {"high": "#eef9f0", "med": "#fff8e6", "low": "#f4f4f8"}[pred["confidence"]]

    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
        <div style="font-size:20px;font-weight:700;color:#1a1a2e;">
            {g['away']['abbr']} @ {g['home']['abbr']}
        </div>
        <span style="background:{conf_bg};color:{conf_color};border-radius:6px;padding:3px 12px;font-size:12px;font-weight:600;">
            {conf_label}
        </span>
    </div>
    """, unsafe_allow_html=True)

    # Injuries warning
    if all_injuries:
        st.markdown(f"""
        <div class="injury-box">
            ⚠ <b>Injury report:</b> {' · '.join(all_injuries)}
        </div>
        """, unsafe_allow_html=True)

    # ── WIN PROBABILITY ──
    st.markdown('<div class="section-header">Win Probability</div>', unsafe_allow_html=True)
    render_prob_bar("Full Game", g["away"]["abbr"], g["home"]["abbr"], pred["game_win"]["away"], pred["game_win"]["home"])

    # ── FORM ──
    st.markdown('<div class="section-header">Recent Form (Last 5)</div>', unsafe_allow_html=True)
    fc1, fc2, fc3 = st.columns([2, 1, 2])
    with fc1:
        w_a = g["form"]["away"].count("W")
        st.markdown(f"""
        <div style="text-align:center;">
            <div style="font-weight:600;color:#2ecc71;">{g['away']['abbr']}</div>
            <div style="font-size:13px;color:#666;">{w_a}-{5-w_a} L5</div>
            <div style="margin-top:4px;">{form_dots(g['form']['away'])}</div>
        </div>
        """, unsafe_allow_html=True)
    with fc2:
        st.markdown('<div style="text-align:center;color:#ccc;padding-top:10px;font-size:18px;">vs</div>', unsafe_allow_html=True)
    with fc3:
        w_h = g["form"]["home"].count("W")
        st.markdown(f"""
        <div style="text-align:center;">
            <div style="font-weight:600;color:#3498db;">{g['home']['abbr']}</div>
            <div style="font-size:13px;color:#666;">{w_h}-{5-w_h} L5</div>
            <div style="margin-top:4px;">{form_dots(g['form']['home'])}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # ── LIVE QUARTER SCORES ──
    if g["status"] in ("inprogress","halftime") and g["q_scores"]:
        st.markdown('<div class="section-header">Live Quarter Scores</div>', unsafe_allow_html=True)
        q_cols = st.columns(len(g["q_scores"]))
        for i, (qnum, qsc) in enumerate(sorted(g["q_scores"].items())):
            winner = g["away"]["abbr"] if qsc["away"] > qsc["home"] else (g["home"]["abbr"] if qsc["home"] > qsc["away"] else "TIE")
            w_color = "#2ecc71" if winner == g["away"]["abbr"] else ("#3498db" if winner == g["home"]["abbr"] else "#999")
            with q_cols[i]:
                st.markdown(f"""
                <div class="qtr-card">
                    <div class="qtr-title">Q{qnum}</div>
                    <div style="font-size:18px;font-weight:700;color:#1a1a2e;">{qsc['away']}–{qsc['home']}</div>
                    <div style="font-size:11px;font-weight:600;color:{w_color};margin-top:3px;">{winner}</div>
                </div>
                """, unsafe_allow_html=True)

    # ── QUARTER-BY-QUARTER PREDICTIONS ──
    st.markdown('<div class="section-header">Quarter-by-Quarter Win Chances</div>', unsafe_allow_html=True)
    q_data = [
        ("Q1",     pred["q1"]),
        ("1st Half", pred["half"]),
        ("Q3",     pred["q3"]),
        ("Q4",     pred["q4"]),
    ]
    qcols = st.columns(4)
    for i, (lbl, qp) in enumerate(q_data):
        winner     = g["home"]["abbr"] if qp["home"] >= qp["away"] else g["away"]["abbr"]
        win_color  = "#3498db" if winner == g["home"]["abbr"] else "#2ecc71"
        higher_pct = max(qp["home"], qp["away"])
        with qcols[i]:
            st.markdown(f"""
            <div class="qtr-card">
                <div class="qtr-title">{lbl}</div>
                <div class="qtr-winner" style="color:{win_color};">{winner}</div>
                <div class="qtr-prob">{higher_pct}%</div>
                <div style="font-size:10px;color:#aaa;margin-top:4px;">{g['away']['abbr']} {qp['away']}% / {g['home']['abbr']} {qp['home']}%</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("")  # spacing

    # ── POINTS PER QUARTER + O/U ──
    left_col, right_col = st.columns(2)
    with left_col:
        st.markdown('<div class="section-header">Pts Per Quarter Projection</div>', unsafe_allow_html=True)
        m1, m2 = st.columns(2)
        with m1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">{g['away']['abbr']} / qtr</div>
                <div class="metric-value">{pred['away_qpts']}</div>
                <div class="metric-sub">~{pred['away_qpts']*4} total</div>
            </div>
            """, unsafe_allow_html=True)
        with m2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">{g['home']['abbr']} / qtr</div>
                <div class="metric-value">{pred['home_qpts']}</div>
                <div class="metric-sub">~{pred['home_qpts']*4} total</div>
            </div>
            """, unsafe_allow_html=True)

    with right_col:
        st.markdown('<div class="section-header">Over / Under</div>', unsafe_allow_html=True)
        o1, o2 = st.columns(2)
        with o1:
            st.markdown(f"""
            <div class="ou-card ou-over">
                <div class="ou-label">OVER {pred['ou_line']}</div>
                <div class="ou-value">{pred['over_pct']}%</div>
                <div class="ou-sub">Proj: {pred['total_proj']} pts</div>
            </div>
            """, unsafe_allow_html=True)
        with o2:
            st.markdown(f"""
            <div class="ou-card ou-under">
                <div class="ou-label">UNDER {pred['ou_line']}</div>
                <div class="ou-value">{pred['under_pct']}%</div>
                <div class="ou-sub">Line: {pred['ou_line']}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("")

    # ── FIRST TO REACH ──
    st.markdown('<div class="section-header">First to Reach (Q1 Pace)</div>', unsafe_allow_html=True)
    st.markdown('<div style="border:1px solid #e8e8ee;border-radius:10px;overflow:hidden;">', unsafe_allow_html=True)
    for pts, info in pred["milestones"].items():
        team_color = "#3498db" if info["team"] == g["home"]["abbr"] else "#2ecc71"
        st.markdown(f"""
        <div class="milestone-row">
            <span style="font-weight:600;color:#1a1a2e;">{pts} pts</span>
            <span style="font-weight:600;color:{team_color};">{info['team']} ({info['prob']}%)</span>
            <span style="color:#aaa;font-size:12px;">~{info['est_min']} min</span>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("")

    # ── OT PROBABILITY ──
    ot_color = "#e74c3c" if pred["ot_prob"] > 12 else "#666"
    st.markdown(f"""
    <div style="display:flex;justify-content:space-between;align-items:center;
                background:#f8f9ff;border:1px solid #e8e8ee;border-radius:10px;padding:12px 16px;">
        <span style="font-size:14px;color:#555;">⏱ Overtime probability</span>
        <span style="font-size:18px;font-weight:700;color:{ot_color};">{pred['ot_prob']}%</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("")

    # ── STAT COMPARISON ──
    st.markdown('<div class="section-header">Key Stat Comparison</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div style="border:1px solid #e8e8ee;border-radius:10px;overflow:hidden;padding:8px 16px;">
        <div style="display:flex;justify-content:space-between;font-size:11px;
                    color:#999;margin-bottom:8px;font-weight:600;">
            <span>{g['away']['abbr']}</span>
            <span>STAT</span>
            <span>{g['home']['abbr']}</span>
        </div>
    """, unsafe_allow_html=True)

    stat_rows = [
        ("FG%",       f"{g['stats']['away']['fg_pct']}%",   f"{g['stats']['home']['fg_pct']}%"),
        ("3PT%",      f"{g['stats']['away']['fg3_pct']}%",  f"{g['stats']['home']['fg3_pct']}%"),
        ("Off Rtg",   g['stats']['away']['ortg'],            g['stats']['home']['ortg']),
        ("Def Rtg",   g['stats']['away']['drtg'],            g['stats']['home']['drtg']),
        ("Bench Pts", g['stats']['away']['bench_pts'],       g['stats']['home']['bench_pts']),
        ("Paint Pts", g['stats']['away']['paint_pts'],       g['stats']['home']['paint_pts']),
        ("Pace",      g['stats']['away']['pace'],            g['stats']['home']['pace']),
    ]
    for (lbl, av, hv) in stat_rows:
        st.markdown(f"""
        <div class="stat-row">
            <div class="val-away">{av}</div>
            <div class="stat-name">{lbl}</div>
            <div class="val-home">{hv}</div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ── PROB BARS FOR EACH QUARTER ──
    st.markdown("")
    st.markdown('<div class="section-header">Win Probability Detail</div>', unsafe_allow_html=True)
    for lbl, qp in q_data:
        render_prob_bar(lbl, g["away"]["abbr"], g["home"]["abbr"], qp["away"], qp["home"])

    # ── AI ANALYSIS ──
    st.markdown("")
    st.markdown('<div class="section-header">🤖 AI Deep Analysis</div>', unsafe_allow_html=True)
    if st.button("Generate AI Analysis ▶", type="primary", use_container_width=True):
        with st.spinner("Claude is analyzing the matchup..."):
            analysis = get_ai_analysis(g, pred)
        st.markdown(f'<div class="ai-box">{analysis}</div>', unsafe_allow_html=True)
        st.session_state[f"analysis_{g['id']}"] = analysis
    elif f"analysis_{g['id']}" in st.session_state:
        cached_analysis = st.session_state[f"analysis_{g['id']}"]
        st.markdown(f'<div class="ai-box">{cached_analysis}</div>', unsafe_allow_html=True)

    # ── COMPARE ALL GAMES TABLE ──
    st.markdown("---")
    st.markdown("#### 📊 All Games — Prediction Summary")
    summary_rows = []
    for gg in games:
        pp = calculate_predictions(gg)
        fav = gg["home"]["abbr"] if pp["game_win"]["home"] >= pp["game_win"]["away"] else gg["away"]["abbr"]
        summary_rows.append({
            "Matchup":    f"{gg['away']['abbr']} @ {gg['home']['abbr']}",
            "Status":     gg["status"].title(),
            "Favorite":   fav,
            "Win %":      f"{max(pp['game_win']['home'], pp['game_win']['away'])}%",
            "Q1 Winner":  gg["home"]["abbr"] if pp["q1"]["home"] >= pp["q1"]["away"] else gg["away"]["abbr"],
            "Q4 Winner":  gg["home"]["abbr"] if pp["q4"]["home"] >= pp["q4"]["away"] else gg["away"]["abbr"],
            "Proj Total": pp["total_proj"],
            "O/U Line":   pp["ou_line"],
            "Over %":     f"{pp['over_pct']}%",
            "OT Risk":    f"{pp['ot_prob']}%",
            "Confidence": pp["confidence"].title(),
        })
    st.dataframe(summary_rows, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="text-align:center;color:#aaa;font-size:12px;padding:8px 0 16px;">
    NBA Prediction Engine · Powered by SportRadar + Claude AI · For entertainment purposes only
</div>
""", unsafe_allow_html=True)