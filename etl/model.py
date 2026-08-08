from pydantic import BaseModel, Field, field_validator
from datetime import datetime

class WeatherRecord(BaseModel):
    ciudad:      str
    pais:        str
    temperatura: float = Field(ge=-90, le=60)
    sensacion:   float
    humedad:     int   = Field(ge=0, le=100)
    descripcion: str
    viento_kmh:  float = Field(ge=0)
    timestamp:   str

    @field_validator("ciudad", "pais", "descripcion")
    def no_vacio(cls, v):
        if not v.strip():
            raise ValueError("No puede estar vacío")
        return v.strip()