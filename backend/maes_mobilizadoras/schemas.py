from datetime import datetime, timezone
from uuid import UUID
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


STATUS_VALUES = Literal["draft", "scheduled", "active", "cancelled"]

ROLE_VALUES = Literal["participante", "organizadora", "coordenadora"]

CAMPOS_BLOQUEADOS_PATCH = frozenset({"organizer_id", "participant_count"})


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


class AcaoPatchRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    event_datetime: Optional[datetime] = None
    location_name: Optional[str] = Field(None, min_length=1, max_length=200)
    location_lat: Optional[Decimal] = None
    location_lng: Optional[Decimal] = None
    category_id: Optional[int] = None
    max_participants: Optional[int] = Field(None, gt=0)
    status: Optional[STATUS_VALUES] = None
    cover_image_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def data_nao_pode_ser_no_passado(self):
        if self.event_datetime is None:
            return self
        dt = self.event_datetime
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt < datetime.now(tz=timezone.utc):
            raise ValueError("A data do evento não pode ser no passado")
        return self


class AcaoMetadata(BaseModel):
    id: str | UUID
    participant_count: int = Field(default=0)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AcaoResponse(BaseModel):
    data: AcaoData
    metadata: AcaoMetadata

    model_config = ConfigDict(from_attributes=True)


CAMPOS_IMUTAVEIS = {"role", "id"}


class AcaoListItem(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    event_datetime: datetime
    location_name: str
    category_id: int
    category_name: Optional[str] = None
    organizer_id: str
    organizer_name: Optional[str] = None
    status: str
    participant_count: int = Field(default=0)
    cover_image_url: Optional[str] = None
    is_participating: bool = False

    model_config = ConfigDict(from_attributes=False)


class ActiveFilters(BaseModel):
    q: Optional[str] = None
    categoria: Optional[int] = None
    de: Optional[str] = None
    ate: Optional[str] = None
    responsavel: Optional[str] = None


class AcaoListResponse(BaseModel):
    data: list[AcaoListItem]
    total: int
    page: int
    per_page: int
    filters: ActiveFilters

    model_config = ConfigDict(from_attributes=False)


class CategoryListItem(BaseModel):
    id: int
    name: str
    icon: Optional[str] = None
    color: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CategoryListResponse(BaseModel):
    data: list[CategoryListItem]


class UserResponse(BaseModel):
    id: str | UUID
    phone: Optional[str] = None   # nullable: usuários Google completam depois
    email: Optional[str] = None   # nullable: usuários OTP completam depois
    full_name: str
    neighborhood: Optional[str] = None
    role: str
    avatar_url: Optional[str] = None
    created_events_count: int = 0
    participated_events_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=150)
    avatar_url: Optional[str] = Field(None, max_length=500)
    phone: Optional[str] = Field(None, min_length=8, max_length=20)
    email: Optional[str] = Field(None, max_length=254)
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


class NotificationListItem(BaseModel):
    id: str | UUID
    event_id: Optional[str | UUID] = None
    sender_id: Optional[str | UUID] = None
    type: str
    title: str
    message: str
    sent_at: Optional[datetime] = None
    is_read: bool = False
    cover_image_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    data: list[NotificationListItem]


class RoleUpdateRequest(BaseModel):
    role: ROLE_VALUES


class UserAdminResponse(BaseModel):
    id: str
    full_name: str
    phone: Optional[str] = None   # nullable: usuários Google completam depois
    email: Optional[str] = None   # nullable: usuários OTP completam depois
    neighborhood: Optional[str] = None
    role: str
    is_active: bool
    avatar_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)