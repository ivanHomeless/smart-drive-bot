from pydantic import BaseModel


class CustomFieldValue(BaseModel):
    field_id: int
    values: list[dict]


class AmoContactCreate(BaseModel):
    name: str
    custom_fields_values: list[CustomFieldValue] = []
    tags_to_add: list[dict] | None = None
    responsible_user_id: int | None = None


class AmoContactUpdate(BaseModel):
    id: int
    custom_fields_values: list[CustomFieldValue] = []
    tags_to_add: list[dict] | None = None


class AmoLeadCreate(BaseModel):
    name: str
    pipeline_id: int
    status_id: int
    responsible_user_id: int
    custom_fields_values: list[CustomFieldValue] = []
    _embedded: dict | None = None

    def to_request_body(self) -> dict:
        """Build request dict with _embedded handled properly."""
        data = self.model_dump(exclude={"_embedded"}, exclude_none=True)
        if self._embedded:
            data["_embedded"] = self._embedded
        return data


class AmoNoteCreate(BaseModel):
    note_type: str = "common"
    params: dict


class AmoContactResponse(BaseModel):
    id: int


class AmoLeadResponse(BaseModel):
    id: int


class AmoNoteResponse(BaseModel):
    id: int
    entity_id: int
