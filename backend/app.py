from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import tensorflow as tf
import joblib
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
from ta.volume import OnBalanceVolumeIndicator
import sqlite3
from responseModel import *

seed = 8989
tf.random.set_seed(seed)
np.random.seed(seed)

app = FastAPI(
    title="Stock Forecasting Api",
    description="LSTM based"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODELCONFIG = {
    "mbsb_model": {
        "modelPath": "mbsb_model.h5",
        "scalerFeaturesPath": "mbsb_scaler_features.pkl",
        "scalerTargetPath": "mbsb_scaler_target.pkl",
        "tickers": {
            'MBSB': '1171.KL',
        },
        "timeStep": 90,
        "outputLength": 30,
        "features": ['Open', 'High', 'Low', 'Close', 'Volume', 'SMA_20', 'EMA_50', 
                     'MACD', 'RSI_14', 'Momentum_10', 'BB_upper', 'BB_lower', 'ATR_14', 'OBV']
    }
}

MODELS = {}
SCALERS_FEATURES = {}
SCALERS_TARGET = {}

for model, config in MODELCONFIG.items():
    MODELS[model] = tf.keras.models.load_model(f"model/models/{config["modelPath"]}")
    SCALERS_FEATURES[model] = joblib.load(f"model/scalers/{config['scalerFeaturesPath']}")
    SCALERS_TARGET[model] = joblib.load(f"model/scalers/{config['scalerTargetPath']}")
    

def normalize_columns(df):
    col_map = {}
    for col in df.columns:
        if "Open" in col:
            col_map[col] = "Open"
        elif "High" in col:
            col_map[col] = "High"
        elif "Low" in col:
            col_map[col] = "Low"
        elif "Close" in col:
            col_map[col] = "Close"
        elif "Volume" in col:
            col_map[col] = "Volume"
    df = df.rename(columns=col_map)
    return df

def calculateFeatures(data):
    df = data.copy()
    df['SMA_20'] = SMAIndicator(df['Close'], window=20).sma_indicator()
    df['EMA_50'] = EMAIndicator(df['Close'], window=50).ema_indicator()
    df['MACD'] = MACD(df['Close']).macd()
    df['RSI_14'] = RSIIndicator(df['Close'], window=14).rsi()
    df['Momentum_10'] = df['Close'] / df['Close'].shift(10) - 1
    bb = BollingerBands(df['Close'], window=20, window_dev=2)
    df['BB_upper'] = bb.bollinger_hband()
    df['BB_lower'] = bb.bollinger_lband()
    df['ATR_14'] = (df['High'] - df['Low']).rolling(14).mean()
    obv = OnBalanceVolumeIndicator(df['Close'], df['Volume'])
    df['OBV'] = obv.on_balance_volume()
    return df
    
def findData(tickers, days=None):
    allStockData = {}
    
    for name, ticker in tickers.items():
        data = yf.download(ticker, period="5y", interval="1d")
        if not data.empty:
            data = normalize_columns(data)
            if days is not None:
                data = data.tail(days)
            allStockData[name] = data
            print(f"{name}: {len(data)} days - fetched from Yahoo Finance")
        else:
            print(f"{name}: No data available from Yahoo Finance")
    
    return allStockData

def predictStockPrices(modelName, stockName, stockData, timeStep, outputLength):
    model = MODELS[modelName]
    scaler_features = SCALERS_FEATURES[modelName]
    scaler_target = SCALERS_TARGET[modelName]
    config = MODELCONFIG[modelName]
    feature_columns = config["features"]
    
    df = pd.DataFrame({
        'Open': stockData['Open'].values,
        'High': stockData['High'].values,
        'Low': stockData['Low'].values,
        'Close': stockData['Close'].values,
        'Volume': stockData['Volume'].values
    })
    df = calculateFeatures(df)
    df_clean = df[feature_columns].dropna()
    
    if len(df_clean) < timeStep:
        raise HTTPException(status_code=400, 
                          detail=f"Insufficient data. Need {timeStep} days, got {len(df_clean)}")
    
    previousPrice = df_clean['Close'].iloc[-2]
    currentPrice = df_clean['Close'].iloc[-1]
    scaled_features = scaler_features.transform(df_clean[feature_columns].values)
    last_sequence = scaled_features[-timeStep:]
    X = last_sequence.reshape(1, timeStep, len(feature_columns))
    predictions = []
    current_seq = X.copy()
    
    for day in range(1, outputLength + 1):
        pred_scaled = model.predict(current_seq, verbose=0)
        pred_price = scaler_target.inverse_transform(pred_scaled)[0][0]
        predictions.append({
            "day": day,
            "price": round(float(pred_price), 3)
        })
        new_features = current_seq[0, -1, :].copy()
        close_idx = feature_columns.index('Close')
        new_features[close_idx] = pred_scaled[0][0]
        new_features = new_features.reshape(1, 1, len(feature_columns))
        current_seq = np.concatenate([current_seq[:, 1:, :], new_features], axis=1)
        
    priceChange = currentPrice - previousPrice
    percentChange = (priceChange / previousPrice) * 100
    
    return {
        "stock": stockName,
        "currentPrice": round(float(currentPrice), 4),
        "predictions": predictions,
        "priceChange": round(float(priceChange), 4),
        "percentChange": round(float(percentChange), 4)
    }
    
@app.get("/models", response_model=List[ModelInfo])
async def listModels():
    models = []
    for model, config in MODELCONFIG.items():
        models.append(ModelInfo(
            name=model,
            stocks=list(config["tickers"].keys()),
            timeStep=config["timeStep"],
            outputLength=config["outputLength"],
            features=list(config["features"]),
            status="loaded" if model in MODELS else "failed"
        ))
    return models

@app.get("/models/{modelName}", response_model=ModelInfo)
async def getModel(modelName: str):
    if modelName not in MODELCONFIG:
        raise HTTPException(status_code=404, detail=f"{modelName} not found")
    config = MODELCONFIG[modelName]
    return ModelInfo(
            name=modelName,
            stocks=list(config["tickers"].keys()),
            timeStep=config["timeStep"],
            outputLength=config["outputLength"],
            features=list(config["features"]),
            status="loaded" if modelName in MODELS else "failed"
        )

@app.post("/predict", response_model=PredictionResponse)
async def prediction(request: PredictionRequest):
    if request.modelName not in MODELCONFIG or request.modelName not in MODELS:
        raise HTTPException(status_code=404, detail=f"{request.modelName} not found")
    config = MODELCONFIG[request.modelName]
    stocks = request.stocks if request.stocks else list(config["tickers"].keys())
    invalidStocks = [stock for stock in stocks if stock not in config["tickers"]]
    if invalidStocks:
        raise HTTPException(status_code=404, detail="Invalid Stocks")
    outputLength = request.days if request.days else config["outputLength"]
    tickers = {key: value for key, value in config["tickers"].items() if key in stocks}
    stockData = findData(tickers)
    
    predictions = []
    for stock in stocks:
        prediction = predictStockPrices(request.modelName,
                                        stock,
                                        stockData[stock],
                                        config["timeStep"],
                                        outputLength)
        predictions.append(prediction)
    return PredictionResponse(
        modelName=request.modelName,
        predictions=predictions,
        timestamp=datetime.now().isoformat(),
        modelInfo={
            "timeStep": config["timeStep"],
            "outputLength": outputLength
        }
    )
    
@app.get("/historical/{modelName}/{stock}", response_model=HistoricalDataResponse)
async def getHistoricalData(modelName: str, stock: str, days: Optional[int] = Query(None, gt=0)):
    if modelName not in MODELCONFIG:
        raise HTTPException(status_code=404, detail=f"{modelName} not found")
    config = MODELCONFIG[modelName]
    if stock not in config["tickers"]:
        raise HTTPException(status_code=404, detail=f"{stock} not found")
    stockData = findData({stock: config["tickers"][stock]}, days)
    if stock not in stockData:
        raise HTTPException(status_code=404, detail=f"{stock} not found")
    data = stockData[stock]
    historical = []
    for date, row in data.iterrows():
        historical.append({
            "date": date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date),
            "open": round(float(row['Open']), 3) if 'Open' in row else None,
            "high": round(float(row['High']), 3) if 'High' in row else None,
            "low": round(float(row['Low']), 3) if 'Low' in row else None,
            "close": round(float(row['Close']), 3) if 'Close' in row else None,
            "volume": int(row['Volume']) if 'Volume' in row else None
        })
    return HistoricalDataResponse(
        stock=stock,
        data=historical
    )
    

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app="app:app", host="0.0.0.0", port=8000, reload=True)
