from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import numpy as np
import yfinance as yf
from tensorflow.keras.models import load_model
import joblib
from datetime import datetime, timedelta
import uvicorn

# Initialize FastAPI app
app = FastAPI(
    title="Stock Prediction API",
    description="LSTM-based stock price prediction API",
    version="1.0.0"
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model = load_model('../model/stock_model.h5')
scaler = joblib.load('../model/scaler.pkl')
print("Model loaded successfully!")

SEQUENCE_LENGTH = 60

def prepare_data(ticker, days_back=100):
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        data = yf.download(ticker, start=start_date, end=end_date, progress=False)
        if data.empty:
            return None, "No data found for this ticker"
        close_prices = data['Close'].values.reshape(-1, 1)
        scaled_data = scaler.transform(close_prices)
        return scaled_data, close_prices
    except Exception as e:
        return None, str(e)
    
def create_sequences(data, seq_length=60):
    X = []
    for i in range(seq_length, len(data)):
        X.append(data[i-seq_length:i, 0])
    return np.array(X).reshape(-1, seq_length, 1)

def predict_future_days(last_sequence, days=7):
    predictions = []
    current_sequence = last_sequence.copy() 
    for _ in range(days):
        next_pred = model.predict(current_sequence.reshape(1, SEQUENCE_LENGTH, 1), verbose=0)
        predictions.append(next_pred[0, 0])
        current_sequence = np.append(current_sequence[1:], next_pred)
    return np.array(predictions)




if __name__ == "__main__":
    print("hello")