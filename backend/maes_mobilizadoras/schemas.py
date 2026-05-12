from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


STATUS_VALUES = Literal["draft", "scheduled", "active", "cancelled"]


class AcaoData(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    event_datetime: datetime
    location_name: str = Field(..., min_length=1, max_length=200)
    location_lat: Optional[Decimal] = None
    location_lng: Optional[Decimal] = None
    category_id: int
    organizer_id: str
    max_participants: Optional[int] = Field(None, gt=0)
    status: STATUS_VALUES = "draft"
    cover_image_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def data_nao_pode_ser_no_passado(self):
        dt = self.event_datetime
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt < datetime.now(tz=timezone.utc):
            raise ValueError("A data do evento não pode ser no passado")
        return self


class AcaoMetadata(BaseModel):
    id: str
    participant_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AcaoResponse(BaseModel):
    data: AcaoData
    metadata: AcaoMetadata

    model_config = ConfigDict(from_attributes=True)