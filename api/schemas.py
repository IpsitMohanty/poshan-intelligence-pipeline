# api/schemas.py

from pydantic import BaseModel

class PredictRequest(BaseModel):
    PW_Anaemia_Rate: float | None = None
    Optimum_WG_Latest_: float | None = None
    PW_Hb_Measured_: float | None = None
    Measurement_Efficiency: float | None = None
    HV_Percentage: float | None = None
    SAM_Rate_: float | None = None
    SUW_Rate_: float | None = None
    Active_AWC_: float | None = None
    LBW_Rate_: float | None = None
