from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional, Dict
import json
import os
from pathlib import Path

app = FastAPI(title="Currency Rates Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_cache = {}
CACHE_TTL = 60  

class RateRequest(BaseModel):
    from_currency: str
    to_currency: str

class RateResponse(BaseModel):
    from_currency: str
    to_currency: str
    rate: float
    timestamp: str
    cached: bool

class RatesResponse(BaseModel):
    rates: Dict[str, float]
    timestamp: str
    cached: bool


_RATES_DB = {
    "USD_USD": 1.000000,
    "USD_EUR": 0.920000,
    "EUR_USD": 1.086956,
    "USD_RUB": 92.500000,
    "RUB_USD": 0.010811,
    "EUR_RUB": 85.100000,
    "RUB_EUR": 0.011751,
    "USD_UAH": 41.200000,
    "UAH_USD": 0.024272,
    "EUR_UAH": 45.600000,
    "UAH_EUR": 0.021930,
    "USD_GBP": 0.780000,
    "GBP_USD": 1.282051,
}

@app.get("/")
async def root():
    return {
        "service": "Currency Rates Service",
        "version": "1.0.0",
        "endpoints": [
            "/rates/{from_currency}/{to_currency}",
            "/rates/bulk",
            "/rates/update",
            "/rates/health",
            "/rates/cache/clear"
        ]
    }

@app.get("/rates/{from_currency}/{to_currency}", response_model=RateResponse)
async def get_rate(from_currency: str, to_currency: str):
    """Получить курс валюты"""
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()
    
    cache_key = f"{from_currency}_{to_currency}"

    if cache_key in _cache:
        cached_data = _cache[cache_key]
        if datetime.now() - cached_data['timestamp'] < timedelta(seconds=CACHE_TTL):
            return RateResponse(
                from_currency=from_currency,
                to_currency=to_currency,
                rate=cached_data['rate'],
                timestamp=cached_data['timestamp'].isoformat(),
                cached=True
            )

    rate_key = f"{from_currency}_{to_currency}"
    if rate_key not in _RATES_DB:
        reverse_key = f"{to_currency}_{from_currency}"
        if reverse_key in _RATES_DB:
            rate = 1 / _RATES_DB[reverse_key]
        else:
            raise HTTPException(status_code=404, detail=f"Rate not found for {from_currency}/{to_currency}")
    else:
        rate = _RATES_DB[rate_key]

    _cache[cache_key] = {
        'rate': rate,
        'timestamp': datetime.now()
    }
    
    return RateResponse(
        from_currency=from_currency,
        to_currency=to_currency,
        rate=rate,
        timestamp=datetime.now().isoformat(),
        cached=False
    )

@app.get("/rates/bulk", response_model=RatesResponse)
async def get_bulk_rates(from_currency: str, to_currencies: str):
    """Получить курсы для одной валюты ко многим"""
    from_currency = from_currency.upper()
    currencies = [c.strip().upper() for c in to_currencies.split(',')]
    
    rates = {}
    for to_currency in currencies:
        try:
            response = await get_rate(from_currency, to_currency)
            rates[to_currency] = response.rate
        except HTTPException:
            continue
    
    return RatesResponse(
        rates=rates,
        timestamp=datetime.now().isoformat(),
        cached=False
    )

@app.post("/rates/update")
async def update_rates():
    """Обновить курсы (имитация обновления из внешнего источника)"""

    _cache.clear()
    
    return {
        "status": "success",
        "message": "Rates updated",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/rates/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "cache_size": len(_cache),
        "rates_count": len(_RATES_DB)
    }

@app.post("/rates/cache/clear")
async def clear_cache():
    """Очистить кэш"""
    _cache.clear()
    return {
        "status": "success",
        "message": "Cache cleared",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/rates/debug")
async def debug():
    """Отладочная информация"""
    return {
        "cache": {k: {'rate': v['rate'], 'timestamp': v['timestamp'].isoformat()} 
                  for k, v in _cache.items()},
        "rates_db": _RATES_DB
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)