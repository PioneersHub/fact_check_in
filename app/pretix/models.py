"""Pretix-specific models."""

from pydantic import Field, field_validator, model_validator

from app.models.base import BaseAttendee, BaseIsAnAttendee


class PretixAttendee(BaseAttendee):
    """Pretix attendee validation model with flexible validation options."""

    order_id: str | None = Field(
        None, json_schema_extra={"example": "MH9CG", "description": "5-character order code (A-Z, 0-9, no O or 1)"}
    )
    ticket_id: str | None = Field(
        None, json_schema_extra={"example": "fw8m3gsje2ymaf83tpqc7cr2paa4n94n", "description": "32-character ticket secret"}
    )
    name: str = Field(..., json_schema_extra={"example": "Sam Smith", "description": "Attendee name (required)"})

    @field_validator("order_id")
    @classmethod
    def validate_order_id(cls, v):
        if v is None:
            return v
        v = v.strip().upper()
        if len(v) != 5:  # noqa: PLR2004
            raise ValueError("Order ID must be exactly 5 characters")
        if not v.isalnum():
            raise ValueError("Order ID must be alphanumeric")
        # Pretix order codes exclude O and 1
        if "O" in v or "1" in v:
            raise ValueError("Order ID cannot contain 'O' or '1'")
        return v

    @field_validator("ticket_id")
    @classmethod
    def validate_ticket_id(cls, v):
        if v is None:
            return v
        v = v.strip().lower()
        if len(v) != 32:  # noqa: PLR2004
            raise ValueError("Ticket ID must be exactly 32 characters")
        if not v.isalnum():
            raise ValueError("Ticket ID must be alphanumeric")
        return v

    @field_validator("name")
    @classmethod
    def valid_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Name is required")
        return v

    @model_validator(mode="after")
    def validate_combination(self):
        """Ensure at least one ID is provided."""
        if not (self.order_id or self.ticket_id):
            raise ValueError("Either order_id or ticket_id (or both) must be provided")
        return self


class PretixIsAnAttendee(PretixAttendee, BaseIsAnAttendee):
    """Pretix validation response model."""

    pass
