#!/usr/bin/env bash
# /root/startup.sh — proot bootstrap for outage-runner
set -Eeuo pipefail
export TZ=America/Port_of_Spain

shopt -s expand_aliases
[ -f /root/.bash_aliases ] && source /root/.bash_aliases

APP_DIR="/root/projects/apps/service-outage-monitor"
VENV_ACTIVATE="$APP_DIR/.venv/bin/activate"
RUNNER="$APP_DIR/runner.py"
LOG_DIR="$APP_DIR/logs/outage-runner"
mkdir -p "$LOG_DIR"

# ---- avoid double-runs on boot thrash
LOCK="/var/run/outage-runner.lock"
mkdir -p /var/run
exec 9> "$LOCK" || { echo "[startup] cannot open lock"; exit 1; }
flock -n 9 || { echo "[startup] another instance running, exiting"; exit 0; }

# ---- central logs
mkdir -p /var/log/proot
exec >>/var/log/proot/startup.log 2>&1
echo "[startup] $(date) begin"

# ---- bridge URL/token (fallbacks)
: "${TT_BRIDGE_URL:=${BRIDGE_URL:-http://127.0.0.1:8787}}"
: "${TT_BRIDGE_TOKEN:=super-secret-change-me}"
: "${TT_BRIDGE_ENABLED:=1}"

wait_bridge() {
  local url="${TT_BRIDGE_URL}"
  for _ in $(seq 1 60); do
    curl -m 1 -s "$url/health" >/dev/null 2>&1 && return 0
    sleep 1
  done
  return 1
}

preflight() {
  echo "[startup] preflight…"
  sleep 35

  if wait_bridge; then
    curl -m 1 -sS -X POST "$TT_BRIDGE_URL/toast" \
      -H "Content-Type: application/json" \
      -d "{\"text\":\"🔌 proot startup begin @ $(date +%H:%M:%S)\"}" >/dev/null 2>&1 || true
  else
    echo "[startup] WARN: bridge not healthy after 60s; proceeding anyway"
  fi

  for _ in {1..60}; do
    [ -d "$APP_DIR" ] && [ -f "$VENV_ACTIVATE" ] && [ -f "$RUNNER" ] && break
    sleep 1
  done
  if [ ! -d "$APP_DIR" ] || [ ! -f "$VENV_ACTIVATE" ] || [ ! -f "$RUNNER" ]; then
    echo "[startup] FATAL: APP_DIR/VENV/RUNNER missing"
    exit 1
  fi

  : "${PYTHONPATH:=}"
  export PYTHONPATH="$APP_DIR:$APP_DIR/src${PYTHONPATH:+:$PYTHONPATH}"

  echo "[startup] preflight ok"
}

preflight

bash /root/start-sshd-once.sh || echo "[startup] sshd start script reported an issue (continuing)"

echo "[startup] launching runner in tmux…"
curl -m 1 -sS -X POST "$TT_BRIDGE_URL/toast" -H "Content-Type: application/json" \
  -d '{"text":"▶️ launching outage-runner (tmux)"}' >/dev/null 2>&1 || true

CHILD_SCRIPT="/tmp/outage_runner_tmux.sh"
cat > "$CHILD_SCRIPT" <<'SH'
#!/usr/bin/env bash
set -Eeuo pipefail

BOOTLOG="/root/outage_runner.bootstrap.log"
echo "[child] $(date) child starting; LOG_DIR='${LOG_DIR-}' APP_DIR='${APP_DIR-}'" >> "$BOOTLOG"

[ -z "${LOG_DIR:-}" ] && LOG_DIR="/root"
mkdir -p "$LOG_DIR"
exec >> "$LOG_DIR/runner.out" 2>&1
set -x

echo "[tmux] $(date) begin"
echo "[tmux] env check: LOG_DIR=$LOG_DIR APP_DIR=$APP_DIR VENV_ACTIVATE=$VENV_ACTIVATE RUNNER=$RUNNER"
echo "[tmux] PWD before: $(pwd)"

export TT_BRIDGE_URL TT_BRIDGE_TOKEN TT_BRIDGE_ENABLED
: "${PYTHONPATH:=}"; export PYTHONPATH="$APP_DIR:$APP_DIR/src:$PYTHONPATH"

if [ -n "${VENV_ACTIVATE:-}" ] && [ -f "$VENV_ACTIVATE" ]; then
  source "$VENV_ACTIVATE"
fi

cd "$APP_DIR" || { echo "[tmux] ERROR: cd $APP_DIR"; exec bash; }

echo "[tmux] exports/venv done"; python3 -V || true; which python3 || true

if [ -n "${TT_BRIDGE_URL:-}" ]; then
  curl -m 1 -sS -X POST "$TT_BRIDGE_URL/toast" \
    -H "Content-Type: application/json" \
    -d '{"text":"tmux env OK"}' >/dev/null 2>&1 || true
fi

echo "==== $(date) starting runner (tmux) ===="
export PYTHONUNBUFFERED=1
export PYTHONFAULTHANDLER=1

python3 - <<'PY'
import runpy, sys, traceback
print("PY LAUNCH: importing runner.py"); sys.stdout.flush()
try:
    runpy.run_path("/root/projects/apps/service-outage-monitor/runner.py", run_name="__main__")
except SystemExit as e:
    print(f"PY SystemExit: {e.code}"); sys.stdout.flush(); raise
except Exception:
    print("PY EXCEPTION BELOW >>>"); traceback.print_exc(); sys.stdout.flush()
    raise
PY
ec=$?

echo "PY EXIT:$ec @ $(date)"
echo "[tmux] runner exited; keeping shell open"
exec bash
SH
chmod +x "$CHILD_SCRIPT"

export TT_BRIDGE_URL TT_BRIDGE_TOKEN TT_BRIDGE_ENABLED
export APP_DIR VENV_ACTIVATE RUNNER LOG_DIR
: "${PYTHONPATH:=}"; export PYTHONPATH="$APP_DIR:$APP_DIR/src${PYTHONPATH:+:$PYTHONPATH}"

if command -v tmux >/dev/null 2>&1; then
  tmux start-server || true
  tmux set-option -g exit-empty off || true

  created=0
  for try in 1 2 3; do
    if tmux new -d -s outage-runner "bash -lc '$CHILD_SCRIPT'"; then
      created=1
      echo "[startup] tmux session created on try $try"
      break
    else
      echo "[startup] tmux launch retry $try…"
      sleep 3
    fi
  done

  if [ "$created" -eq 1 ]; then
    deadline=$(( $(date +%s) + 90 ))
    started=0
    hb="$LOG_DIR/runner.heartbeat"
    while [ "$(date +%s)" -lt "$deadline" ]; do
      if [ -f "$hb" ] && [ $(( $(date +%s) - $(stat -c %Y "$hb" 2>/dev/null || echo 0) )) -lt 30 ]; then
        started=1
        break
      fi
      sleep 3
    done

    if [ "$started" -ne 1 ]; then
      echo "[startup] watchdog: no heartbeat; relaunching tmux once"
      tmux has-session -t outage-runner 2>/dev/null && tmux kill-session -t outage-runner || true
      tmux new -d -s outage-runner "bash -lc '$CHILD_SCRIPT'" || true
    fi
  else
    echo "[startup] ERROR: failed to create tmux session after retries"
  fi

  curl -m 1 -sS -X POST "$TT_BRIDGE_URL/toast" -H "Content-Type: application/json" \
    -d '{"text":"✅ runner launch attempted (tmux)"}' >/dev/null 2>&1 || true
else
  echo "[startup] tmux not found; using setsid+nohup fallback…"
  curl -m 1 -sS -X POST "$TT_BRIDGE_URL/toast" -H "Content-Type: application/json" \
    -d '{"text":"▶️ launching outage-runner (nohup)"}' >/dev/null 2>&1 || true
  pkill -f 'python3 -u .*runner.py' || true

  source "$VENV_ACTIVATE"
  cd "$APP_DIR" || true
  echo "==== $(date) starting runner (setsid) ====" >> "$LOG_DIR/runner.out"
  setsid -f nohup bash -lc '
    set -Eeuo pipefail
    exec >> "'"$LOG_DIR"'/runner.out" 2>&1
    set -x
    export PYTHONUNBUFFERED=1
    python3 -u "'"$RUNNER"'"
    echo "PY EXIT:$? @ $(date)"
  ' >/dev/null 2>&1

  curl -m 1 -sS -X POST "$TT_BRIDGE_URL/toast" -H "Content-Type: application/json" \
    -d '{"text":"✅ runner launched (nohup)"}' >/dev/null 2>&1 || true
fi

curl -m 1 -sS -X POST "$TT_BRIDGE_URL/toast" -H "Content-Type: application/json" \
  -d "{\"text\":\"✅ proot startup done @ $(date +%H:%M:%S)\"}" >/dev/null 2>&1 || true

echo "[startup] $(date) done"
