import pytest
from pydantic import ValidationError

from etl.model import WeatherRecord


def base_data(**overrides):
    data = dict(
        ciudad="Lima",
        pais="PE",
        temperatura=20.0,
        sensacion=19.5,
        humedad=70,
        descripcion="nublado",
        viento_kmh=10.0,
        timestamp="2026-09-10T08:00:00",
    )
    data.update(overrides)
    return data


def test_valid_record_is_accepted():
    record = WeatherRecord(**base_data())
    assert record.ciudad == "Lima"
    assert record.temperatura == 20.0


@pytest.mark.parametrize("temperatura", [-91, 61])
def test_temperatura_fuera_de_rango_es_rechazada(temperatura):
    with pytest.raises(ValidationError):
        WeatherRecord(**base_data(temperatura=temperatura))


@pytest.mark.parametrize("humedad", [-1, 101])
def test_humedad_fuera_de_rango_es_rechazada(humedad):
    with pytest.raises(ValidationError):
        WeatherRecord(**base_data(humedad=humedad))


def test_viento_negativo_es_rechazado():
    with pytest.raises(ValidationError):
        WeatherRecord(**base_data(viento_kmh=-5))


@pytest.mark.parametrize("field", ["ciudad", "pais", "descripcion"])
def test_campos_de_texto_vacios_son_rechazados(field):
    with pytest.raises(ValidationError):
        WeatherRecord(**base_data(**{field: "   "}))


def test_campos_de_texto_se_recortan():
    record = WeatherRecord(**base_data(ciudad="  Lima  ", pais=" PE "))
    assert record.ciudad == "Lima"
    assert record.pais == "PE"
