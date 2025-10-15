#termux_bridge.py
# -*- coding: utf-8 -*-
"""
Termux bridge client (toast + notify) for proot/Ubuntu → Termux:API.
No external deps. Safe no-op on failures or when disabled.

Env:
  TT_BRIDGE_URL   default http://127.0.0.1:8787
  TT_BRIDGE_TOKEN default "super-secret-change-me"
  TT_BRIDGE_ENABLED default "1" (set "0" to disable)
"""
from __future__ import annotations
import json, os, urllib.request, urllib.error, logging, functools, time
from typing import Optional, Dict, Any, Callable

BRIDGE_URL   = os.environ.get("TT_BRIDGE_URL",   "http://127.0.0.1:8787")
BRIDGE_TOKEN = os.environ.get("TT_BRIDGE_TOKEN", "super-secret-change-me")
ENABLED      = os.environ.get("TT_BRIDGE_ENABLED", "1") not in ("0", "false", "False", "")

def _call(path: str, payload: Dict[str, Any], timeout: float = 2.0) -> bool:
    """Best-effort call to /toast or /notify. Returns True on 2xx, False otherwise."""
    if not ENABLED:
        return False
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            BRIDGE_URL.rstrip("/") + path,
            data=data,
            headers={
                "Content-Type": "application/json",
                "X-TT-Token": BRIDGE_TOKEN
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            _ = r.read()
        return True
    except Exception:
        return False  # never raise into your app

def toast(text: str) -> bool:
    """Show a quick toast."""
    return _call("/toast", {"text": text})

def notify(title: str, content: str, priority: str = "default",
           sticky: bool = False, buttons: Optional[Dict[str, str]] = None) -> bool:
    """
    Android notification via Termux:API.
    priority: 'low'|'default'|'high'|'max'
    buttons:  {"button1": "Open Log", "button1_action": "termux-open ...", ...}
    """
    payload = {"title": title, "content": content, "priority": priority, "sticky": sticky}
    if buttons:
        for k, v in buttons.items():
            payload[k] = v
    return _call("/notify", payload)

def ping(timeout: float = 1.0) -> bool:
    """Check bridge health via GET /health (non-fatal if not present)."""
    if not ENABLED:
        return False
    try:
        req = urllib.request.Request(BRIDGE_URL.rstrip("/") + "/health")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return 200 <= r.getcode() < 300
    except Exception:
        return False

def wait_until_ready(max_wait_s: float = 20.0, step_s: float = 0.5) -> bool:
    """Poll /health until ready or timeout."""
    t0 = time.time()
    while time.time() - t0 < max_wait_s:
        if ping():
            return True
        time.sleep(step_s)
    return False

# ---------- Decorator for jobs ----------

def wrap_notify(job_title: str,
                start_toast: bool = True,
                success_notify: bool = True,
                success_text: str = "✅ Done",
                error_notify: bool = True,
                error_prefix: str = "❌ Failed: ") -> Callable:
    """
    Decorate a function to auto-toast at start, notify on success, and sticky on error.
    Usage:
      @wrap_notify("Outage Monitor - T&TEC")
      def run_provider(...): ...
    """
    def deco(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if start_toast:
                toast(f"[{job_title}] started")
            try:
                rv = fn(*args, **kwargs)
                if success_notify:
                    notify(job_title, success_text, priority="high")
                return rv
            except Exception as e:
                if error_notify:
                    # keep it short to avoid truncation
                    notify(job_title, f"{error_prefix}{type(e).__name__}", priority="max", sticky=True)
                raise
        return wrapper
    return deco

# ---------- Logging handler to push ERROR+ ----------

class BridgeHandler(logging.Handler):
    """
    Attach to your logger to send ERROR+ records as notifications.
    Example:
        h = BridgeHandler(job_title="Outage Monitor")
        h.setLevel(logging.ERROR)
        logger.addHandler(h)
    """
    def __init__(self, job_title: str = "Service"):
        super().__init__()
        self.job_title = job_title

    def emit(self, record: logging.LogRecord) -> None:
        try:
            if record.levelno >= logging.ERROR:
                msg = self.format(record)
                # truncate to keep the notification readable
                if len(msg) > 400:
                    msg = msg[:397] + "…"
                notify(self.job_title, f"❌ {msg}", priority="max", sticky=True)
        except Exception:
            pass  # never break logging

# add to bottom of termux_bridge.py (optional)
if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--toast", help="Send a toast")
    g.add_argument("--notify", nargs=2, metavar=("TITLE","CONTENT"), help="Send a notification")
    p.add_argument("--priority", default="default")
    p.add_argument("--sticky", action="store_true")
    args = p.parse_args()
    if args.toast:
        toast(args.toast)
    else:
        notify(args.notify[0], args.notify[1], priority=args.priority, sticky=args.sticky)
