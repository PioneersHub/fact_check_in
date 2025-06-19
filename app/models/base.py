"""Base models shared across all ticketing backends."""

from pydantic import BaseModel, EmailStr, Field


class Email(BaseModel):
    email: EmailStr


class BaseAttendee(BaseModel):
    """Base attendee model without validation - backends extend this."""

    pass


class BaseIsAnAttendee(BaseModel):
    """Base response model for attendee validation."""

    is_attendee: bool = Field(False, json_schema_extra={"description": "Returns 'true' if validation passes."})
    hint: str = Field(
        "",
        json_schema_extra={
            "example": "Looks like a typo",
            "description": "Hint why validation failed, eg. if the name is close but not close enough.",
        },
    )
    is_speaker: bool = Field(False, json_schema_extra={"example": False, "description": "Person has a speaker ticket."})
    is_sponsor: bool = Field(False, json_schema_extra={"example": False, "description": "Person has a sponsor ticket."})
    is_organizer: bool = Field(False, json_schema_extra={"example": False, "description": "Person is an organizer."})
    is_volunteer: bool = Field(False, json_schema_extra={"example": False, "description": "Person is a volunteer."})
    is_remote: bool = Field(False, json_schema_extra={"example": False, "description": "Person is a remote attendee."})
    is_onsite: bool = Field(False, json_schema_extra={"example": False, "description": "Person is a in-person attendee."})
    is_guest: bool = Field(False, json_schema_extra={"example": False, "description": "Person is a guest (limited access)."})
    online_access: bool = Field(False, json_schema_extra={"example": False, "description": "Person has remote access."})


class TicketType(BaseModel):
    id: int = Field(
        json_schema_extra={
            "example": 12345,
            "description": "Id of ticket.",
        }
    )
    title: str = Field(json_schema_extra={"example": "Business Late Bird (online)", "description": "Description of ticket type."})
    activities: list[str] = Field(json_schema_extra={"example": ["talks", "workshops"], "description": "List of activities included."})


class TicketTypes(BaseModel):
    ticket_types: list[TicketType] = Field(json_schema_extra={"description": "List of ticket types."})


class TicketCount(BaseModel):
    ticket_count: int = Field(json_schema_extra={"count": "Number of tickets in cache."})


class Truthy(BaseModel):
    valid: bool = Field(False, json_schema_extra={"description": "Simple true / false response"})
