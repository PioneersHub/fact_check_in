"""Common routes shared by all ticketing backends."""

import threading
import time

from fastapi import APIRouter

from app import in_dummy_mode, interface, reset_interface
from app.models.base import TicketCount, TicketTypes
from app.ticketing.backend import get_ticketing_backend

router = APIRouter(prefix="/tickets", tags=["Common"])

# State for the singleflight refresh guard.
# _refresh_lock ensures only one thread runs force_refresh_all() at a time.
# Threads that arrive while a refresh is in progress wait for the lock,
# then find _state.last_time is recent and return without starting another refresh.
_refresh_lock = threading.Lock()
_REFRESH_TTL: float = 300.0  # seconds between full data refreshes


class _RefreshState:
    last_time: float = 0.0


_state = _RefreshState()


@router.get("/refresh_all/")
def force_refresh_all():
    if in_dummy_mode:
        reset_interface(in_dummy_mode)
        return {"message": "Refreshed from dummy (test) data."}
    backend = get_ticketing_backend()
    backend.get_all_ticket_offers()
    backend.get_all_tickets()
    backend_name = backend.__class__.__name__.replace("Backend", "")
    return {"message": f"The ticket cache was refreshed successfully from {backend_name}."}


def refresh_all():
    """Reload all ticket data at most once per TTL window.

    Wraps force_refresh_all() with a singleflight guard: the entire
    check-then-refresh-then-record sequence runs inside a threading.Lock, so
    concurrent callers (e.g. background tasks fired by simultaneous cache misses)
    queue up and only the first one actually calls the expensive Pretix API.
    Once the first thread finishes and releases the lock, the others find the
    timestamp is fresh and return immediately.

    Note: cachetools.cached(lock=...) does NOT provide this guarantee. Its lock
    only serializes cache reads and writes; the wrapped function itself is called
    outside the lock, allowing concurrent calls to bypass the cache simultaneously.
    """
    with _refresh_lock:
        if time.monotonic() - _state.last_time < _REFRESH_TTL:
            return  # another thread just refreshed; skip
        result = force_refresh_all()
        _state.last_time = time.monotonic()
        return result


@router.get("/ticket_types/", response_model=TicketTypes)
async def get_ticket_types():
    return {"ticket_types": list(interface.all_releases.values())}


@router.get("/ticket_count/", response_model=TicketCount)
async def get_ticket_count():
    return {"ticket_count": len(interface.all_sales)}
