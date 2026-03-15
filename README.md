# 🏀 NBA Prediction Engine

A highly sensitive, real-time NBA prediction model built with Streamlit, SportRadar, and Claude AI.

## Features

- **Live NBA data** via SportRadar API (scores, stats, schedules)
- **Quarter-by-quarter win probabilities** — Q1, 1st Half, Q3, Q4
- **Points-per-quarter projections** — calibrated from offensive ratings & O/U lines
- **Over/Under analysis** — projected totals vs the line
- **First-to-reach milestones** — which team hits 10/15/20/25/30 pts first
- **Overtime probability** — tighter matchups get higher OT risk
- **Injury warnings** — flags missing players that affect predictions
- **Form analysis** — last 5 games with visual dots
- **Stat comparison** — FG%, 3PT%, OffRtg, DefRtg, Bench Pts, Paint Pts, Pace
- **AI Deep Analysis** — 6-8 sentence expert breakdown powered by Claude Sonnet

## Setup

### 1. Clone & install

```bash
git clone <your-repo>
cd nba_predictor
pip install -r requirements.txt
```

### 2. Get API Keys

**SportRadar** (free trial):
1. Go to https://developer.sportradar.com
2. Create an account → My Account → Register a new app
3. Select NBA Official API → Trial
4. Your trial key allows 1,000 calls/day

**Anthropic** (Claude AI):
1. Go to https://console.anthropic.com
2. Create account → API Keys → Create Key

### 3. Set environment variables

```bash
cp .env.example .env
# Edit .env and add your keys
```

### 4. Run locally

```bash
streamlit run app.py
```

App opens at http://localhost:8501

---

## Deploy to Streamlit Community Cloud (Free)

1. Push this folder to a GitHub repository
2. Go to https://share.streamlit.io
3. Click **New app** → select your repo + `app.py`
4. Go to **Settings → Secrets** and add:

```toml
SPORTRADAR_API_KEY = "your_key_here"
ANTHROPIC_API_KEY  = "your_key_here"
```

5. Click **Deploy** — done!

---

## How Predictions Work

### Win Probability
- Pulled directly from SportRadar's ML model (live games)
- For scheduled games: based on team ratings, H2H, injuries, rest

### Quarter Win Probabilities
Regressed toward 50% — earlier quarters have more variance:
- Q1: 52% blend toward 50 (most random)
- 1st Half: 65% blend
- Q3: 56% blend
- Q4: 68% blend (most predictive)

### Points Per Quarter
`q_base = ou_line / 8`  
`team_qpts = q_base × (0.5 + (ortg - 110) / 220)`  
Teams with higher offensive ratings score above the base pace.

### Over/Under
`over_pct = 50 + (projected_total - ou_line) × 3`  
Capped at 80% / floored at 20%.

### OT Probability
`ot_prob = (1 - spread × 3.2) × 14`  
Tight games (small spread) have higher OT risk.

### First to Reach
Based on Q1 offensive pace with small game-win probability adjustment.

---

## File Structure

```
nba_predictor/
├── app.py              ← Main Streamlit application
├── requirements.txt    ← Python dependencies
├── .env.example        ← Environment variable template
├── .streamlit/
│   └── secrets.toml    ← Streamlit Cloud secrets template
└── README.md
```

---

## Notes

- The app runs in **demo mode** if no SportRadar key is set — uses Mar 15, 2026 sample data
- SportRadar trial keys are rate-limited to 1 req/sec — the app uses `@st.cache_data` to stay within limits
- All predictions are for **entertainment purposes only**

---

*Built with Streamlit · SportRadar NBA API · Anthropic Claude*
