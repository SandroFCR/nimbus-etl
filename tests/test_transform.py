from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from etl.transform import transform_weather


def make_raw(**overrides):
    raw = {
        "name": "Lima",
        "sys": {"country": "PE"},
        "main": {"temp": 22.5, "feels_like": 21.0, "humidity": 65},
        "weather": [{"description": "cielo claro"}],
        "wind": {"speed": 5.0},  # m/s
    }
    raw.update(overrides)
    return raw


def test_transform_mapea_los_campos_correctamente():
    result = transform_weather(make_raw())

    assert result["ciudad"] == "Lima"
    assert result["pais"] == "PE"
    assert result["temperatura"] == 22.5
    assert result["sensacion"] == 21.0
    assert result["humedad"] == 65
    assert result["descripcion"] == "cielo claro"


def test_transform_convierte_viento_de_ms_a_kmh():
    result = transform_weather(make_raw(wind={"speed": 10.0}))
    assert result["viento_kmh"] == 36.0  # 10 m/s * 3.6


def test_transform_genera_timestamp_iso_reciente():
    before = datetime.utcnow()
    result = transform_weather(make_raw())
    after = datetime.utcnow()

    ts = datetime.fromisoformat(result["timestamp"])
    assert before - timedelta(seconds=2) <= ts <= after + timedelta(seconds=2)


def test_transform_rechaza_temperatura_invalida():
    raw = make_raw(main={"temp": 500, "feels_like": 20, "humidity": 50})
    with pytest.raises(ValidationError):
        transform_weather(raw)


def test_transform_falla_si_falta_un_campo_de_la_api():
    raw = make_raw()
    del raw["wind"]
    with pytest.raises(KeyError):
        transform_weather(raw)
