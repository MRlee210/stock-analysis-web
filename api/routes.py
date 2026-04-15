from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import api.services.finance_service as fs
import api.services.technical_analysis as ta
import api.services.strategy as strat
import api.services.risk_management as rm
from api.services.llm_service import get_ai_opinion_async

router = APIRouter()

@router.get("/sectors")
async def get_sectors():
    """Return a list of available stock sectors"""
    sectors = fs.get_all_sectors()
    return {"sectors": sectors}

@router.get("/stocks")
async def get_stocks_in_sector(sector: str):
    """Return companies and tickers for a given sector"""
    stocks = fs.get_stocks_by_sector(sector)
    return {"stocks": stocks}

@router.get("/search")
async def search_stocks(q: str):
    """Search for companies by name"""
    stocks = fs.search_stocks(q)
    return {"stocks": stocks}

@router.get("/analyze")
async def analyze_stock(ticker: str, capital: float = Query(10000000, description="User capital for risk management")):
    """
    Given a ticker, fetch history, calculate indicators, 
    generate buy/sell signals, and provide risk management guide.
    """
    try:
        df = fs.fetch_stock_data(ticker, period="1y")
        if df.empty:
            raise HTTPException(status_code=404, detail="Ticker data not found")
        
        # Calculate indicators
        df = ta.calculate_indicators(df)
        
        # Market Phase Detection
        market_phase = strat.detect_market_phase(df)
        
        # Determine signals
        signals, current_status, detailed_advice = strat.generate_signals(df)
        
        # Detect Support / Resistance
        sr_lines = ta.detect_support_resistance(df)
        
        # Calculate risk management
        risk_guide = rm.calculate_position_size_and_stop_loss(df, capital)
        
        # Fibonacci levels
        fib_levels = ta.calculate_fibonacci_levels(df)
        
        # ── Gemini AI 코멘트 추가 ──
        try:
            ai_opinion = await get_ai_opinion_async(ticker, detailed_advice)
        except Exception:
            ai_opinion = "⚠️ AI 코멘트를 불러오지 못했습니다."
        
        # Format the response
        ohlcv = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].to_dict(orient="records")
        for row in ohlcv:
            row['time'] = row.pop('Date')
            row['open'] = row.pop('Open')
            row['high'] = row.pop('High')
            row['low'] = row.pop('Low')
            row['close'] = row.pop('Close')
            row['value'] = row.pop('Volume')
            
        # extract indicator series
        indicators = {
            "ma": df[['Date', 'SMA_5', 'SMA_20', 'SMA_60', 'SMA_120']].to_dict(orient="records"),
            "bb": df[['Date', 'BBL_20_2.0', 'BBM_20_2.0', 'BBU_20_2.0']].to_dict(orient="records"),
            "rsi": df[['Date', 'RSI_14']].to_dict(orient="records"),
            "macd": df[['Date', 'MACD_12_26_9', 'MACDh_12_26_9', 'MACDs_12_26_9']].to_dict(orient="records"),
        }
        
        # Ichimoku data for chart overlay
        ich_cols = ['Date', 'ICH_TENKAN', 'ICH_KIJUN', 'ICH_SPAN_A', 'ICH_SPAN_B']
        indicators["ichimoku"] = df[ich_cols].dropna(subset=['ICH_TENKAN', 'ICH_KIJUN']).to_dict(orient="records")
        
        # Stochastic data
        stoch_cols = ['Date', 'STOCH_K_5', 'STOCH_D_5', 'STOCH_K_10', 'STOCH_D_10', 'STOCH_K_20', 'STOCH_D_20']
        indicators["stochastic"] = df[stoch_cols].dropna(subset=['STOCH_K_5']).to_dict(orient="records")
        
        # Candle patterns (only non-empty)
        candle_data = df[df['CANDLE_PATTERN'] != ''][['Date', 'CANDLE_PATTERN']].to_dict(orient="records") if 'CANDLE_PATTERN' in df.columns else []
        
        return {
            "ticker": ticker,
            "ohlcv": ohlcv,
            "indicators": indicators,
            "signals": signals,
            "current_status": current_status,
            "detailed_advice": detailed_advice,
            "ai_opinion": ai_opinion,
            "market_phase": market_phase,
            "fibonacci_levels": fib_levels,
            "candle_patterns": candle_data,
            "support_resistance": sr_lines,
            "risk_management": risk_guide
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
