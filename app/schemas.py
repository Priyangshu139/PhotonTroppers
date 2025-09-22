from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class SensorData(BaseModel):
    factory_medicine_id: str
    timestamp: datetime
    temperature: float
    mq3_ppm: float
    as7263_r: float
    as7263_s: float
    as7263_t: float
    as7263_u: float
    as7263_v: float
    as7263_w: float
    taste_sweet: Optional[float] = None
    taste_salty: Optional[float] = None
    taste_bitter: Optional[float] = None
    taste_sour: Optional[float] = None
    taste_umami: Optional[float] = None
    quality: Optional[float] = None
    dilution: Optional[float] = None


class PicronData(BaseModel):
    taste_sweet: float
    taste_salty: float
    taste_bitter: float
    taste_sour: float
    taste_umami: float
    quality: float
    dilution: float
    status: int
    factory: Optional[str] = None


class LiveSensor(BaseModel):
    factory_medicine_id: str
    timestamp: datetime
    mq3_ppm: float
    as7263_r: float
    as7263_s: float
    as7263_t: float
    as7263_u: float
    as7263_v: float
    as7263_w: float