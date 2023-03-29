from fastapi import APIRouter

from app.tito.tito_api import get_all_tickets

router = APIRouter(prefix="/tickets", tags=["bem", "pa"])


@router.get("/refresh_all")
async def refresh_all():
    get_all_tickets(from_cache=False)
    return 200


@router.get("/ticket/{tito_id}")
async def get_ticket_by_id():
    get_all_tickets(from_cache=False)
    return 200
