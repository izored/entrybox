"""Optional token gate for the local file-read surface.

EntryBox is loopback-only and unauthenticated by default. When ENTRYBOX_TOKEN
is set (recommended if you bind to anything other than 127.0.0.1), sensitive
routes require a matching X-EntryBox-Token header. Apply via Depends().
"""
import hmac

from fastapi import Header, HTTPException

from app.config import TOKEN


def require_token(x_entrybox_token: str | None = Header(default=None)) -> None:
    if not TOKEN:
        return
    if not x_entrybox_token or not hmac.compare_digest(x_entrybox_token, TOKEN):
        raise HTTPException(status_code=401, detail="invalid or missing token")
