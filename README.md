# Stock Price Forecasting

## Overview
This projects predicts stock prices using machine learning models.  
It collects data, trains forecasting models, and visualizes future stock trends.

## Features
- LSTM neural network
- Modern UI
- FastAPI

## Technology
### Backend
- Python
- FastAPI
- Tensorflow, Keras
- yfinance, investpy

### Frontend
- React
- TypeScript
- HTML, CSS

### Model
- LSTM
- 60 days seq
- min max scaling

### Data
- SQLite

### To Start
#### Terminal 1
- cd stock-dashboard/backend
- uvicorn app:app --reload
#### Terminal 2
- cd stock-dashboard
- npm start