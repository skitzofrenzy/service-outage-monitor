# utils/env_util.py
import os

def recipients_for_provider(provider_id: str) -> list[str]:
    """
    Read recipients from env var: RECIPIENTS__<UPPER_PROVIDER_ID>
    Returns [] if not set.
    """
    key = f"RECIPIENTS__{provider_id.upper()}"
    raw = os.getenv(key, "").strip()
    # allow empty lists without breaking
    if not raw:
        return []
    return [e.strip() for e in raw.split(",") if e.strip()]
