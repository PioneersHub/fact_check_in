"""Tito-specific models."""

from pydantic import Field, field_validator

from app.models.base import BaseAttendee, BaseIsAnAttendee


class TitoAttendee(BaseAttendee):
    """Tito attendee validation model."""

    ticket_id: str = Field(None, json_schema_extra={"example": "XRTP-3", "description": "Ticket ID is <four char alphanumeric>-<integer>."})
    name: str = Field(None, json_schema_extra={"example": "Sam Smith", "description": "Person full name as used for registration."})

    @field_validator("ticket_id")
    @classmethod
    def valid_ticket_id(cls, v):
        try:
            v = v.strip().upper()
            if not 6 <= len(v) <= 7:  # noqa: PLR2004
                raise ValueError("Invalid ticket ID, must be: ^[A-Z]{4}-\\d+$ e. g. DROP-3.")
            return v
        except ValueError:
            raise
        except Exception:
            raise

    @field_validator("name")
    @classmethod
    def valid_name(cls, v):
        try:
            v = v.strip().upper()
            if not v:
                raise ValueError("Empty name, use full name e. g. Sam Smith.")
            return v
        except ValueError:
            raise
        except Exception:
            raise


class TitoIsAnAttendee(TitoAttendee, BaseIsAnAttendee):
    """Tito validation response model."""

    pass
