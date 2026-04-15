import pandas as pd
import math

def calculate_position_size_and_stop_loss(df: pd.DataFrame, user_capital: float) -> dict:
    """
    Risk management tool using ATR.
    Risk per trade: 1.5% of user capital.
    Stop loss distance: 2 * ATR
    """
    if df.empty or 'ATRr_14' not in df.columns or df['ATRr_14'].dropna().empty:
        return {
            "current_price": 0,
            "atr": 0,
            "stop_loss_price": 0,
            "suggested_quantity": 0,
            "risk_amount": 0,
            "message": "ATR 계산을 위한 데이터가 부족합니다."
        }
    
    last_row = df.iloc[-1]
    current_price = last_row['Close']
    
    atr = last_row['ATRr_14']
    if pd.isna(atr):
        atr_cols = [c for c in df.columns if 'ATR' in c]
        if atr_cols:
            atr = last_row[atr_cols[0]]
        else:
            atr = current_price * 0.02
            
    stop_loss_price = max(0, current_price - (2 * atr))
    loss_per_share = current_price - stop_loss_price
    
    risk_amount = user_capital * 0.015
    
    if loss_per_share > 0:
        suggested_quantity = math.floor(risk_amount / loss_per_share)
    else:
        suggested_quantity = 0
        
    return {
        "current_price": float(current_price),
        "atr": float(atr),
        "stop_loss_price": float(stop_loss_price),
        "suggested_quantity": int(suggested_quantity),
        "risk_amount": float(risk_amount),
        "message": f"1.5% 포트폴리오 리스크({risk_amount:,.0f} 원) 기준, 권장 최대 매수 수량은 {suggested_quantity:,.0f}주 입니다. 손절가는 {stop_loss_price:,.0f} 원으로 엄수하세요."
    }
