from datetime import datetime, timezone
from uuid import UUID
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
    id: str | UUID
    participant_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AcaoResponse(BaseModel):
    data: AcaoData
    metadata: AcaoMetadata

    model_config = ConfigDict(from_attributes=True)


CAMPOS_IMUTAVEIS = {"role", "id"}


class UserResponse(BaseModel):
    id: str | UUID
    phone: str
    full_name: str
    neighborhood: Optional[str] = None
    role: str
    avatar_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=150)
    avatar_url: Optional[str] = Field(None, max_length=500)
    phone: Optional[str] = Field(None, min_length=8, max_length=20)
    neighborhood: Optional[str] = Field(None, min_length=1, max_length=100)

    @model_validator(mode="before")
    @classmethod
    def rejeitar_campos_imutaveis(cls, values: dict) -> dict:
        encontrados = CAMPOS_IMUTAVEIS & set(values.keys())
        if encontrados:
            raise ValueError(f"Campos não permitidos: {', '.join(sorted(encontrados))}")
        return values


class PhoneConfirmRequest(BaseModel):
    token: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class FCMTokenRegister(BaseModel):
    token: str
    device_type: Optional[Literal["android", "ios", "web"]] = None


class CustomNotificationRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=150)
    message: str = Field(..., min_length=1, max_length=300)
