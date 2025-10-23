import React, { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { TrendingUp, Table2, ChartSpline } from 'lucide-react';
import './styles.css';

const API_BASE = 'http://127.0.0.1:8000';

export default function StockForecastDashboard() {
    const [models, setModels] = useState([]);
    const [allStocks, setAllStocks] = useState([]);
    // const [selectedModel, setSelectedModel] = useState(null);
    const [selectedStock, setSelectedStock] = useState(null);
    const [historicalData, setHistoricalData] = useState([]);
    const [predictions, setPredictions] = useState([]);
    const [viewMode, setViewMode] = useState('chart');
    const [loading, setLoading] = useState('false');
    const [currentPrice, setCurrentPrice] = useState(null);
    const [priceChange, setPriceChange] = useState(null);
    const [showWarning, setShowWarning] = useState(true)

    useEffect(() => {
        fetchModels();
    }, []);

    const fetchModels = async () => {
        try {
            const res = await fetch(`${API_BASE}/models`);
            const data = await res.json();
            setModels(data);
            // if (data.length > 0) {
            //     setSelectedModel(data[0].name);
            //     if (data[0].stocks.length > 0) {
            //         setSelectedStock(data[0].stocks)
            //     }
            // }
            const stocks = [];
            data.forEach(model => {
                model.stocks.forEach(stock => {
                    if (!stocks.find(s => s.name === stock)) {
                        stocks.push({
                            name: stock,
                            modelName: model.name
                        });
                    }
                });
            });
            setAllStocks(stocks);
            if (stocks.length > 0) {
                setSelectedStock(stocks[0]);
            }
        } catch (err) {
            console.log('Error fetching models', err)
        }
    };

    // useEffect(() => {
    //     if (selectedModel && selectedStock) {
    //         fetchData();
    //     }
    // }, [selectedModel, selectedStock]);

    useEffect(() => {
        if (selectedStock) {
            fetchData();
        }
    }, [selectedStock]);

    const fetchData = async () => {
        setLoading(true);
        try {
            const [histRes, predRes] = await Promise.all([
                fetch(`${API_BASE}/historical/${selectedStock.modelName}/${selectedStock.name}?days=90`),
                fetch(`${API_BASE}/predict`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        modelName: selectedStock.modelName,
                        stocks: [selectedStock.name],
                        days: 7
                    })
                })
            ]);
            const hisData = await histRes.json();
            const predData = await predRes.json();
            setHistoricalData(hisData.data);
            if (predData.predictions && predData.predictions.length > 0) {
                setPredictions(predData.predictions[0].predictions);
                setCurrentPrice(predData.predictions[0].currentPrice);
                setPriceChange({
                    value: predData.predictions[0].priceChange,
                    percent: predData.predictions[0].percentChange
                });
            }
        } catch (err) {
            console.error('Error fetching data', err)
        }
        setLoading(false);
    };

    // const currentModel = models.find(m => m.name === selectedModel);

    const chartData = [
        ...historicalData.slice(-60).map((d, i) => ({
            index: i,
            date: d.date,
            actual: d.close,
            type: 'historical'
        })),
        ...predictions.map((p, i) => ({
            index: historicalData.slice(-60).length + i,
            date: `Day +${p.day}`,
            predicted: p.price,
            type: 'prediction'
        }))
    ];

    const handleWarning = () => {
        setShowWarning(false);
    }

    return (
        <div className="dashboard-container">
            {showWarning && (
                <div className='warning-container'>
                    <div className='warning-container2'>
                        <h2 className='warning-title'>Salts</h2>
                        <p className='warning-items'>
                            Take it with a grain of salt<br />
                            Performance is not guaranteed
                        </p>
                        <button onClick={handleWarning} className='warning-button'>
                            OK
                        </button>
                    </div>
                </div>
            )}
            <div className="sidebar">
                <div className="sidebar-header">
                    <div className="header-title">
                        <TrendingUp className="header-icon" />
                        <h1>Stock Forecast</h1>
                    </div>
                    <p className="header-subtitle">LSTM-based predictions</p>
                </div>

                <div className="sidebar-content">
                    <div className="stocks-section">
                        <label className="section-label">Available Stocks</label>
                        <div className="stocks-list">
                            {allStocks.map(stock => (
                                <button
                                    key={`${stock.modelName}-${stock.name}`}
                                    onClick={() => setSelectedStock(stock)}
                                    className={`stock-button ${selectedStock?.name === stock.name ? 'active' : ''}`}
                                >
                                    <div className="stock-name">{stock.name}</div>
                                    <div className="stock-model">Model: {stock.modelName}</div>
                                    {selectedStock?.name === stock.name && currentPrice && (
                                        <div className="stock-details">
                                            <div>Current: RM {currentPrice.toFixed(4)}</div>
                                            {priceChange && (
                                                <div className={`price-change ${priceChange.percent >= 0 ? 'positive' : 'negative'}`}>
                                                    {priceChange.percent >= 0 ? '+' : ''}
                                                    {priceChange.percent.toFixed(2)}%
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </button>
                            ))}
                        </div>
                    </div>
                </div>
            </div>

            <div className="main-content">
                <div className="content-header">
                    <div className="header-info">
                        <h2>{selectedStock?.name || 'Select a stock'}</h2>
                        {currentPrice && (
                            <div className="price-info">
                                <span className="current-price">RM {currentPrice.toFixed(4)}</span>
                                {priceChange && (
                                    <span className={`change-indicator ${priceChange.percent >= 0 ? 'positive' : 'negative'}`}>
                                        {priceChange.percent >= 0 ? '+' : ''}
                                        {priceChange.value.toFixed(4)} ({priceChange.percent.toFixed(2)}%)
                                    </span>
                                )}
                            </div>
                        )}
                    </div>

                    <div className="view-buttons">
                        <button
                            onClick={() => setViewMode('chart')}
                            className={`view-button ${viewMode === 'chart' ? 'active' : ''}`}
                        >
                            <ChartSpline className="button-icon" />
                            Chart
                        </button>
                        <button
                            onClick={() => setViewMode('table')}
                            className={`view-button ${viewMode === 'table' ? 'active' : ''}`}
                        >
                            <Table2 className="button-icon" />
                            Table
                        </button>
                    </div>
                </div>

                <div className="content-body">
                    {loading ? (
                        <div className="loading-container">
                            <div className="loading-text">Loading...</div>
                        </div>
                    ) : viewMode === 'chart' ? (
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={chartData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                                <XAxis
                                    dataKey="date"
                                    tick={{ fontSize: 12 }}
                                    interval="preserveStartEnd"
                                />
                                <YAxis
                                    tick={{ fontSize: 12 }}
                                    domain={['auto', 'auto']}
                                />
                                <Tooltip
                                    contentStyle={{
                                        backgroundColor: 'white',
                                        border: '1px solid #e5e7eb',
                                        borderRadius: '8px'
                                    }}
                                />
                                <Legend />
                                <Line
                                    type="monotone"
                                    dataKey="actual"
                                    stroke="#3b82f6"
                                    strokeWidth={2}
                                    dot={false}
                                    name="Historical Price"
                                />
                                <Line
                                    type="monotone"
                                    dataKey="predicted"
                                    stroke="#10b981"
                                    strokeWidth={2}
                                    strokeDasharray="5 5"
                                    dot={false}
                                    name="Predicted Price"
                                />
                            </LineChart>
                        </ResponsiveContainer>
                    ) : (
                        <div className="table-container">
                            <div className="table-wrapper">
                                <table className="data-table">
                                    <thead>
                                        <tr>
                                            <th>Date</th>
                                            <th>Type</th>
                                            <th className="text-right">Price (RM)</th>
                                            <th className="text-right">Change</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {predictions.slice().reverse().map((p, i) => (
                                            <tr key={`pred-${i}`} className="prediction-row">
                                                <td>Day +{p.day}</td>
                                                <td className="type-predicted">Predicted</td>
                                                <td className="text-right">{p.price.toFixed(4)}</td>
                                                <td className="text-right">
                                                    {i < predictions.length - 1 ? (
                                                        <span className={p.price - predictions[predictions.length - 1 - (i + 1)].price >= 0 ? 'positive' : 'negative'}>
                                                            {((p.price - predictions[predictions.length - 1 - (i + 1)].price) / predictions[predictions.length - 1 - (i + 1)].price * 100).toFixed(2)}%
                                                        </span>
                                                    ) : (
                                                        <span className={p.price - historicalData[historicalData.length - 1].close >= 0 ? 'positive' : 'negative'}>
                                                            {((p.price - historicalData[historicalData.length - 1].close) / historicalData[historicalData.length - 1].close * 100).toFixed(2)}%
                                                        </span>
                                                    )}
                                                </td>
                                            </tr>
                                        ))}
                                        {historicalData.slice(-30).reverse().map((d, i) => (
                                            <tr key={`hist-${i}`}>
                                                <td>{d.date}</td>
                                                <td className="type-historical">Historical</td>
                                                <td className="text-right">{d.close.toFixed(4)}</td>
                                                <td className="text-right">
                                                    {i < 29 ? (
                                                        <span className={d.close - historicalData[historicalData.length - 30 + (29 - i)].close >= 0 ? 'positive' : 'negative'}>
                                                            {((d.close - historicalData[historicalData.length - 30 + (29 - i)].close) / historicalData[historicalData.length - 30 + (29 - i)].close * 100).toFixed(2)}%
                                                        </span>
                                                    ) : '-'}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
