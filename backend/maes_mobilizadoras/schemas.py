from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional
from decimal import Decimal


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
    status: str = Field("scheduled", max_length=20)
    cover_image_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AcaoMetadata(BaseModel):
    id: str
    participant_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AcaoResponse(BaseModel):
    """Composition of data and metadata for the response."""

    data: AcaoData
    metadata: AcaoMetadata

    model_config = ConfigDict(from_attributes=True)
