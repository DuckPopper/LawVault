#!/bin/bash
# Double-click to put LawVault online from this Mac with a free Cloudflare quick tunnel.
# Keep this window open while friends are testing; close it (or press Ctrl+C) to take the app offline.
cd "$(dirname "$0")" || exit 1
PORT=8502
LOG_DIR="data/logs"
mkdir -p "$LOG_DIR"

bold() { printf "\033[1m%s\033[0m\n" "$1"; }
fail() { printf "\n\033[31m%s\033[0m\n\n" "$1"; read -r -p "Press Return to close."; exit 1; }

env_val() { grep -E "^$1=" .env 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '"' | tr -d "'"; }

bold "LawVault · Go Live"
echo

# 1) Safety checks: never expose dev mode (it shows login and reset codes on screen)
[ -f .env ] || fail "No .env file. Copy .env.example to .env and fill it in first."
[ "$(env_val DEV_MODE)" = "0" ] || fail "DEV_MODE is not 0 in .env. Dev mode shows login codes on screen, so it must be off before going public."
if [ -z "$(env_val SMTP_USER)" ] || [ -z "$(env_val SMTP_PASSWORD)" ]; then
  fail "Email isn't set up, so nobody could receive a login code.
In .env set SMTP_USER to your Gmail address and SMTP_PASSWORD to a Gmail app password
(Google Account → Security → 2-Step Verification → App passwords), then run this again."
fi
[ -x .venv/bin/streamlit ] || fail "Python environment missing. Run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"

# 2) Cloudflare Tunnel
if ! command -v cloudflared >/dev/null 2>&1; then
  echo "Installing Cloudflare Tunnel (one time)…"
  command -v brew >/dev/null 2>&1 || fail "Homebrew is needed to install cloudflared: https://brew.sh"
  brew install cloudflared || fail "Couldn't install cloudflared. Check your internet connection and try again."
fi

# 3) Start the app (unless it's already running on this port)
# Always start a fresh copy: an older one on this port may have been started in dev mode.
if lsof -nP -iTCP:$PORT -sTCP:LISTEN >/dev/null 2>&1; then
  fail "Something is already running on port $PORT. Close it first (it may be a dev-mode copy of LawVault)."
fi
echo "Starting LawVault…"
.venv/bin/streamlit run app.py --server.headless true --server.port $PORT >"$LOG_DIR/app.log" 2>&1 &
APP_PID=$!
for _ in $(seq 1 30); do
  lsof -nP -iTCP:$PORT -sTCP:LISTEN >/dev/null 2>&1 && break
  sleep 1
done
lsof -nP -iTCP:$PORT -sTCP:LISTEN >/dev/null 2>&1 || fail "The app didn't start. See $LOG_DIR/app.log"

# 4) Open the tunnel and show the public link
echo "Opening a public link…"
cloudflared tunnel --no-autoupdate --url "http://localhost:$PORT" >"$LOG_DIR/tunnel.log" 2>&1 &
TUNNEL_PID=$!

cleanup() {
  echo
  echo "Taking LawVault offline…"
  kill "$TUNNEL_PID" 2>/dev/null
  [ -n "$APP_PID" ] && kill "$APP_PID" 2>/dev/null
  exit 0
}
trap cleanup INT TERM HUP EXIT

URL=""
for _ in $(seq 1 40); do
  URL=$(grep -Eo 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOG_DIR/tunnel.log" | grep -v '://api\.' | head -1)
  [ -n "$URL" ] && break
  grep -q "failed to request quick Tunnel" "$LOG_DIR/tunnel.log" && fail "Cloudflare didn't answer. If LuLu asked about cloudflared, allow it, then run this again."
  kill -0 "$TUNNEL_PID" 2>/dev/null || fail "The tunnel stopped. See $LOG_DIR/tunnel.log"
  sleep 1
done
[ -n "$URL" ] || fail "Couldn't get a public link. See $LOG_DIR/tunnel.log"

printf "%s" "$URL" | pbcopy
echo
bold "LawVault is live:"
printf "\n    \033[1;33m%s\033[0m\n\n" "$URL"
echo "The link is copied to your clipboard. Send it to your friends."
echo "It works while this window stays open and your Mac stays awake."
echo "The link changes each time you run this."
echo
echo "Press Ctrl+C or close this window to take it offline."
caffeinate -i -w "$TUNNEL_PID"
