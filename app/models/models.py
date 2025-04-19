from pydantic import BaseModel, EmailStr, Field, field_validator


class Email(BaseModel):
    email: EmailStr


class Attendee(BaseModel):
    ticket_id: str = Field(None, json_schema_extra={"example": "XRTP-3", "description": "Ticket ID is <four char alphanumeric>-<integer>."})
    name: str = Field(None, json_schema_extra={"example": "Sam Smith", "description": "Person full name as used for registration."})

    @field_validator("ticket_id")
    @classmethod
    def valid_ticket_id(cls, v):
        try:
            v = v.strip().upper()
            if not 6 <= len(v) <= 7:
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


class IsAnAttendee(Attendee):
    is_attendee: bool = Field(False, json_schema_extra={"description": "Returns 'true' if the combination of ticket ID and name is valid."})
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
