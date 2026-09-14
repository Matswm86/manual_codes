# mnq-oslo-tools

Two small personal scripts.

- `ny_to_oslo.py`: converts a New York clock-time session range (e.g. `1815-0400`)
  to Oslo local time, handling the overnight wrap.
- `mnq_level_watch.py`: polls the TopstepX (ProjectX) API for MNQ bars, tracks
  prior Asia/London/New York session highs and lows, and sends an ntfy.sh alert
  the first time price touches an untouched level. Needs `~/mnq.env` with
  `PROJECT_X_USERNAME` and `PROJECT_X_API_KEY`, and an `NTFY_TOPIC` env var to
  enable alerts.

Placeholder README, will be rewritten.
