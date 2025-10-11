from pydantic import BaseModel
from typing import Dict, List, Optional, Any

class PredictionRequest(BaseModel):
    modelName: str
    stocks: Optional[List[str]] = None
    days: Optional[int] = None

class StockPrediction(BaseModel):
    stock: str
    currentPrice: float
    predictions: List[Dict[str, float]]
    priceChange: float
    percentChange: float

class PredictionResponse(BaseModel):
    modelName: str
    predictions: List[StockPrediction]
    timestamp: str
    modelInfo: Dict[str, Any]

class ModelInfo(BaseModel):
    name: str
    stocks: List[str]
    timeStep: int
    outputLength: int
    features: List[str]
    status: str

class HistoricalDataResponse(BaseModel):
    stock: str
    data: List[Dict[str, Any]]