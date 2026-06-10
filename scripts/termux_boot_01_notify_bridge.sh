#!/data/data/com.termux/files/usr/bin/sh
# Boot script for notification bridge
export TT_BRIDGE_TOKEN="super-secret-change-me"

sleep 15
pkill -f tt_notify_bridge.py 2>/dev/null
nohup ~/.local/bin/tt_notify_bridge.py >~/logs/notify_bridge.log 2>&1 &
