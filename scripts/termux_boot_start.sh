#!/data/data/com.termux/files/usr/bin/bash
# start.sh — Termux boot launcher
set -Eeuo pipefail

exec 9> "$HOME/.boot.lock"; flock -n 9 || exit 0
LOG="$HOME/boot.log"
exec >>"$LOG" 2>&1

echo
 echo "==== BOOT $(date) ===="
termux-wake-lock

sleep 5

echo "[Termux] starting sshd…"
sshd || echo "[Termux] sshd already running?"

echo "[Termux] waiting for 127.0.0.1:8022 …"
for i in $(seq 1 30); do
  if nc -z 127.0.0.1 8022 2>/dev/null; then
    termux-notification --id 18022 --title "Termux SSH" --content "Now Listening (8022)"
    echo "[Termux] sshd is listening."
    break
  fi
  sleep 1
done

echo "[Ubuntu] launching startup…"

if command -v termux-wifi-connectioninfo >/dev/null 2>&1; then
  for i in $(seq 1 20); do
    LAN_IP="$(termux-wifi-connectioninfo | sed -n 's/.*"ip":"\([^"]*\)".*/\1/p')"
    termux-notification --id 130022 --title "Server IP" --content "IP Live: ${LAN_IP:-unknown}"
    [ -n "${LAN_IP:-}" ] && break
    sleep 1
  done
fi
: "${LAN_IP:=127.0.0.1}"

echo "[boot] LAN_IP=$LAN_IP"

for wait in 0 3 5 8 10; do
  sleep "$wait"
  if proot-distro login ubuntu-jammy -- bash -lc '/root/startup.sh'; then
    echo "[boot] ubuntu startup ok (wait=$wait)"
    break
  else
    echo "[boot] ubuntu startup failed (wait=$wait), retrying…"
  fi
done

for i in $(seq 1 30); do
  if nc -z 127.0.0.1 30022 2>/dev/null; then
    if nc -z "$LAN_IP" 30022 2>/dev/null; then
      termux-notification --id 130023 --title "Ubuntu" --content "SSH on $LAN_IP:30022"
    else
      termux-notification --id 130023 --title "Ubuntu" --content "SSH on 127.0.0.1:30022"
    fi
    echo "[boot] Ubuntu SSH listening"
    break
  fi
  sleep 1
done

echo "==== BOOT DONE $(date) ===="
