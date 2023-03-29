from fastapi import APIRouter

from app.tito.tito_api import get_all_tickets

router = APIRouter(prefix="/tickets", tags=["Attendees"])


@router.get("/refresh_all")
async def refresh_all():
    get_all_tickets(from_cache=False)
    # TODO save all ticket info in memory
    return 200


@router.get("/ticket/{tito_id}")
async def get_ticket_by_id():

