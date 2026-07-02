import numpy as np
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    mock_model = MagicMock()
    mock_model.predict.return_value = np.array([12.5])

    mock_cube_row = {
        "District": "Khordha",
        "LBW_Rate_%": 10.2,
        "Stunting_Total_%": 34.1,
        "Measurement_Efficiency": 78.5,
    }

    import pandas as pd
    mock_cube = pd.DataFrame([mock_cube_row])

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("joblib.load", return_value=mock_model),
        patch("pathlib.Path.glob", return_value=iter(["district_cube_2025-11.csv"])),
        patch("pandas.read_csv", return_value=mock_cube),
    ):
        from api.main import app
        yield TestClient(app)


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "running" in r.json()["message"].lower()


def test_predict_lbw_returns_float(client):
    payload = {
        "PW_Anaemia_Rate": 45.0,
        "Optimum_WG_Latest_": 55.0,
        "PW_Hb_Measured_": 70.0,
        "Measurement_Efficiency": 80.0,
        "HV_Percentage": 65.0,
        "SAM_Rate_": 3.5,
        "SUW_Rate_": 12.0,
    }
    r = client.post("/predict/lbw", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert "LBW_Predicted" in body
    assert isinstance(body["LBW_Predicted"], float)


def test_predict_stunting_returns_float(client):
    payload = {
        "Measurement_Efficiency": 80.0,
        "SAM_Rate_": 3.5,
        "SUW_Rate_": 12.0,
        "Active_AWC_": 92.0,
        "HV_Percentage": 65.0,
        "LBW_Rate_": 10.0,
    }
    r = client.post("/predict/stunting", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert "Stunting_Predicted" in body
    assert isinstance(body["Stunting_Predicted"], float)


def test_predict_lbw_no_features_returns_400(client):
    r = client.post("/predict/lbw", json={})
    assert r.status_code == 400


def test_district_found(client):
    r = client.get("/district/Khordha")
    assert r.status_code == 200
    body = r.json()
    assert body["District"] == "Khordha"


def test_district_not_found(client):
    r = client.get("/district/NonExistentPlace")
    assert r.status_code == 404


def test_district_structured_found(client):
    r = client.get("/district_structured/Khordha")
    assert r.status_code == 200
    body = r.json()
    assert "district" in body
    assert "stunting_5_6" in body
    assert "maternal_indicators" in body
    assert "service_delivery" in body
    assert "raw" in body
