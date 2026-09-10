from unittest.mock import MagicMock

import pymssql
import pytest

from etl import load


def make_fake_conn():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor


def sample_data(**overrides):
    data = dict(
        ciudad="Lima",
        pais="PE",
        temperatura=20.5,
        sensacion=20.0,
        humedad=70,
        descripcion="cielo claro",
        viento_kmh=10.0,
        timestamp="2026-09-10T08:00:00.000000",
    )
    data.update(overrides)
    return data


def test_get_conn_usa_las_credenciales_configuradas(monkeypatch):
    mock_connect = MagicMock(return_value="fake-connection")
    monkeypatch.setattr(load.pymssql, "connect", mock_connect)
    monkeypatch.setattr(load, "AZURE_SQL_SERVER", "srv.database.windows.net")
    monkeypatch.setattr(load, "AZURE_SQL_USER", "admin")
    monkeypatch.setattr(load, "AZURE_SQL_PASSWORD", "pwd123")
    monkeypatch.setattr(load, "AZURE_SQL_DATABASE", "climadb")

    result = load.get_conn()

    mock_connect.assert_called_once_with(
        server="srv.database.windows.net", user="admin", password="pwd123", database="climadb"
    )
    assert result == "fake-connection"


def test_init_db_crea_tabla_con_restriccion_unique(monkeypatch):
    conn, cursor = make_fake_conn()
    monkeypatch.setattr(load, "get_conn", lambda: conn)

    load.init_db()

    executed_sql = cursor.execute.call_args[0][0]
    assert "CREATE TABLE clima" in executed_sql
    assert "UNIQUE (ciudad, fecha)" in executed_sql
    conn.commit.assert_called_once()
    conn.close.assert_called_once()


def test_load_weather_deriva_fecha_y_hace_upsert(monkeypatch):
    conn, cursor = make_fake_conn()
    monkeypatch.setattr(load, "get_conn", lambda: conn)

    load.load_weather(sample_data())

    executed_sql, executed_params = cursor.execute.call_args[0]
    assert "MERGE clima" in executed_sql
    assert executed_params["ciudad"] == "Lima"
    assert executed_params["fecha"] == "2026-09-10"
    conn.commit.assert_called_once()
    conn.close.assert_called_once()


def test_load_weather_reraise_y_cierra_conexion_si_falla(monkeypatch):
    conn, cursor = make_fake_conn()
    cursor.execute.side_effect = pymssql.Error("boom")
    monkeypatch.setattr(load, "get_conn", lambda: conn)

    with pytest.raises(pymssql.Error):
        load.load_weather(sample_data())

    conn.close.assert_called_once()
    conn.commit.assert_not_called()
