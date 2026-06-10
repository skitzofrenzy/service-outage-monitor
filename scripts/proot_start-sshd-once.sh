#!/usr/bin/env bash
set -Eeuo pipefail
exec 9>/run/ubuntu-sshd.lock
flock -n 9 || exit 0

mkdir -p /run/sshd /var/log/proot
rm -f /run/sshd.pid || true

ssh-keygen -A >/dev/null 2>&1 || true
/usr/sbin/sshd -t -f /etc/ssh/sshd_config.min
/usr/sbin/sshd -f /etc/ssh/sshd_config.min -E /var/log/proot/sshd.log -o PidFile=/run/sshd.pid
echo "[start-sshd-once] started on 0.0.0.0:30022" >> /var/log/proot/startup.log
