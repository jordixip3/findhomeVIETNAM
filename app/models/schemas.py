from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class PropertyBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=150)
    description: str
    city: str
    subdivision: str
    subdivision_code: Optional[str] = None
    address: str
    latitude: float
    longitude: float
    total_rent: float = Field(..., gt=0)
    ideal_roommates: int = Field(4, ge=2, le=6)
    bedrooms: int = Field(..., ge=1, le=10)
    bathrooms: int = Field(..., ge=1, le=6)
    surface: int = Field(..., ge=10)
    has_elevator: bool = True
    is_exterior: bool = True
    is_furnished: bool = True
    has_terrace: bool = False
    has_air_con: bool = False
    source_portal: str = Field("Direct Portal", max_length=50)
    source_url: Optional[str] = None
    property_type: str = Field("apartment")
    images: List[str] = Field(default_factory=list)
    contact_name: Optional[str] = Field("Verified Partner Host", max_length=120)
    contact_phone: Optional[str] = Field("+34 603 331 391", max_length=50)
    contact_agency: Optional[str] = Field("Verified Agency", max_length=120)

class VoiceQueryRequest(BaseModel):
    query: str
    lang: str = "vi"

class AdminLoginRequest(BaseModel):
    password: str
