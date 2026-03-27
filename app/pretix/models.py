"""Pretix-specific models."""

import re

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.models.base import BaseAttendee, BaseIsAnAttendee


class PretixAttendee(BaseAttendee):
    """Pretix attendee validation model with flexible validation options."""

    order_id: str | None = Field(
        None,
        description="5-character order code (A-Z, 0-9, no O or 1)",
        json_schema_extra={"example": "MH9CG"},
    )
    ticket_id: str | None = Field(
        None,
        description="Order code with position ID (ORDER-POSITION format)",
        json_schema_extra={"example": "MH9CG-2"},
    )
    name: str = Field(
        ...,
        description="Attendee name (required)",
        json_schema_extra={"example": "Sam Smith"},
    )

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
        return v

    @field_validator("ticket_id")
    @classmethod
    def validate_ticket_id(cls, v):
        if v is None:
            return v
        v = v.strip().upper()
        if not re.fullmatch(r"[A-Z0-9]{5}-\d+", v):
            raise ValueError("ticket_id must be in ORDER-POSITION format (e.g. MH9CG-2)")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
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

    email: EmailStr | None = Field(
        None,
        description="Attendee email address",
        json_schema_extra={"example": "guido@example.com"},
    )


class TShirtVariantCount(BaseModel):
    """Count of a specific T-shirt variant."""

    variant_name: str = Field(json_schema_extra={"example": "M", "description": "T-shirt size variant name"})
    count: int = Field(json_schema_extra={"example": 42, "description": "Number of this variant purchased"})


class AddonStatistics(BaseModel):
    """Add-on product statistics for on-site attendees."""

    onsite_tickets_sold: int = Field(json_schema_extra={"example": 200, "description": "Total on-site tickets sold in category"})
    tshirt_purchased: int = Field(json_schema_extra={"example": 150, "description": "On-site tickets with T-shirt add-on"})
    tshirt_not_purchased: int = Field(json_schema_extra={"example": 50, "description": "On-site tickets without T-shirt add-on"})
    tshirt_variants: list[TShirtVariantCount] = Field(json_schema_extra={"description": "Breakdown of purchased T-shirt variants"})
