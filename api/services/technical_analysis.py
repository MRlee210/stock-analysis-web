import pandas as pd
import numpy as np

# ──────────────────────────────────────────────
# 기본 지표 계산 함수 (Basic Indicator Helpers)
# ──────────────────────────────────────────────

def calculate_ma(series, window):
    return series.rolling(window=window).mean()

def calculate_ema(series, window):
    return series.ewm(span=window, adjust=False).mean()

def calculate_rsi(series, window=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    ema_gain = gain.ewm(alpha=1/window, adjust=False).mean()
    ema_loss = loss.ewm(alpha=1/window, adjust=False).mean()
    rs = ema_gain / ema_loss
    return 100 - (100 / (1 + rs))

def calculate_macd(series, fast=12, slow=26, signal=9):
    ema_fast = calculate_ema(series, fast)
    ema_slow = calculate_ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    macd_hist = macd_line - signal_line
    return macd_line, signal_line, macd_hist

def calculate_bbands(series, window=20, std_dev=2):
    sma = calculate_ma(series, window)
    std = series.rolling(window=window).std()
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    return lower, sma, upper

def calculate_atr(df, window=14):
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    return true_range.ewm(alpha=1/window, adjust=False).mean()

# ──────────────────────────────────────────────
# 스토캐스틱 삼형제 (Stochastic Triple)
# ──────────────────────────────────────────────

def calculate_stochastic(df, k_period, d_period, smooth):
    """Calculate Stochastic %K and %D."""
    low_min = df['Low'].rolling(window=k_period).min()
    high_max = df['High'].rolling(window=k_period).max()
    fast_k = 100 * (df['Close'] - low_min) / (high_max - low_min)
    slow_k = fast_k.rolling(window=smooth).mean()
    slow_d = slow_k.rolling(window=d_period).mean()
    return slow_k, slow_d

# ──────────────────────────────────────────────
# 일목균형표 (Ichimoku Kinko Hyo)
# ──────────────────────────────────────────────

def calculate_ichimoku(df, tenkan=9, kijun=26, senkou_b=52, displacement=26):
    """Calculate Ichimoku Cloud components."""
    high = df['High']
    low = df['Low']
    
    # 전환선 (Tenkan-sen) = (최고가9 + 최저가9) / 2
    tenkan_sen = (high.rolling(window=tenkan).max() + low.rolling(window=tenkan).min()) / 2
    
    # 기준선 (Kijun-sen) = (최고가26 + 최저가26) / 2
    kijun_sen = (high.rolling(window=kijun).max() + low.rolling(window=kijun).min()) / 2
    
    # 선행스팬1 (Senkou Span A) = (전환선 + 기준선) / 2, 26일 앞으로 이동
    senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(displacement)
    
    # 선행스팬2 (Senkou Span B) = (최고가52 + 최저가52) / 2, 26일 앞으로 이동
    senkou_span_b = ((high.rolling(window=senkou_b).max() + low.rolling(window=senkou_b).min()) / 2).shift(displacement)
    
    # 후행스팬 (Chikou Span) = 현재 종가를 26일 뒤로 이동
    chikou_span = df['Close'].shift(-displacement)
    
    return tenkan_sen, kijun_sen, senkou_span_a, senkou_span_b, chikou_span

# ──────────────────────────────────────────────
# 피보나치 되돌림 (Fibonacci Retracement)
# ──────────────────────────────────────────────

def calculate_fibonacci_levels(df, lookback=120):
    """Calculate Fibonacci retracement levels based on recent swing high/low."""
    recent = df.tail(lookback)
    swing_high = recent['High'].max()
    swing_low = recent['Low'].min()
    diff = swing_high - swing_low
    
    levels = {
        "0.0%": round(float(swing_high), 2),
        "23.6%": round(float(swing_high - 0.236 * diff), 2),
        "38.2%": round(float(swing_high - 0.382 * diff), 2),
        "50.0%": round(float(swing_high - 0.500 * diff), 2),
        "61.8%": round(float(swing_high - 0.618 * diff), 2),
        "78.6%": round(float(swing_high - 0.786 * diff), 2),
        "100.0%": round(float(swing_low), 2),
    }
    return levels

# ──────────────────────────────────────────────
# ADX (Average Directional Index)
# ──────────────────────────────────────────────

def calculate_adx(df, period=14):
    """Calculate ADX to measure trend strength."""
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    plus_dm = high.diff()
    minus_dm = -low.diff()
    
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    
    atr = calculate_atr(df, period)
    
    plus_di = 100 * (plus_dm.ewm(alpha=1/period, adjust=False).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(alpha=1/period, adjust=False).mean() / atr)
    
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.ewm(alpha=1/period, adjust=False).mean()
    
    return adx, plus_di, minus_di

# ──────────────────────────────────────────────
# 캔들스틱 패턴 인식 (Candlestick Patterns)
# ──────────────────────────────────────────────

def detect_candle_patterns(df):
    """Detect key candlestick patterns. Returns a column of pattern names per row."""
    o, h, l, c = df['Open'], df['High'], df['Low'], df['Close']
    body = abs(c - o)
    upper_wick = h - pd.concat([c, o], axis=1).max(axis=1)
    lower_wick = pd.concat([c, o], axis=1).min(axis=1) - l
    total_range = h - l
    
    patterns = pd.Series('', index=df.index)
    
    # 망치형 (Hammer) — 하락장 바닥에서 긴 아랫꼬리 양봉
    is_hammer = (
        (lower_wick >= body * 2) &
        (upper_wick <= body * 0.5) &
        (c > o) &
        (total_range > 0)
    )
    patterns = patterns.where(~is_hammer, '망치형(Hammer)')
    
    # 역망치형 (Inverted Hammer) — 긴 윗꼬리 음봉
    is_inv_hammer = (
        (upper_wick >= body * 2) &
        (lower_wick <= body * 0.5) &
        (c < o) &
        (total_range > 0)
    )
    patterns = patterns.where(~is_inv_hammer, '역망치형(Inv.Hammer)')
    
    # 장대양봉 (Strong Bullish) — 몸통이 전체 범위의 70% 이상 + 양봉
    avg_body = body.rolling(20).mean()
    is_strong_bull = (c > o) & (body >= avg_body * 2) & (body >= total_range * 0.7)
    patterns = patterns.where(~is_strong_bull, '장대양봉')
    
    # 장대음봉 (Strong Bearish) — 몸통이 전체 범위의 70% 이상 + 음봉
    is_strong_bear = (c < o) & (body >= avg_body * 2) & (body >= total_range * 0.7)
    patterns = patterns.where(~is_strong_bear, '장대음봉')
    
    # 적삼병 (Three White Soldiers) — 양봉 3연속, 각각 전봉 종가 위에서 마감
    is_three_soldiers = (
        (c > o) &
        (c.shift(1) > o.shift(1)) &
        (c.shift(2) > o.shift(2)) &
        (c > c.shift(1)) &
        (c.shift(1) > c.shift(2))
    )
    patterns = patterns.where(~is_three_soldiers, '적삼병')
    
    # 흑삼병 (Three Black Crows) — 음봉 3연속, 각각 전봉 종가 아래에서 마감
    is_three_crows = (
        (c < o) &
        (c.shift(1) < o.shift(1)) &
        (c.shift(2) < o.shift(2)) &
        (c < c.shift(1)) &
        (c.shift(1) < c.shift(2))
    )
    patterns = patterns.where(~is_three_crows, '흑삼병')
    
    return patterns

# ──────────────────────────────────────────────
# MACD 다이버전스 감지 (Divergence Detection)
# ──────────────────────────────────────────────

def detect_macd_divergence(df, lookback=30):
    """
    Detect regular and hidden MACD divergences.
    Regular bullish: price makes lower low, MACD makes higher low → 상승 반전
    Regular bearish: price makes higher high, MACD makes lower high → 하락 반전
    Hidden bullish: price makes higher low, MACD makes lower low → 상승 지속
    Hidden bearish: price makes lower high, MACD makes higher high → 하락 지속
    """
    recent = df.tail(lookback).copy()
    divs = pd.Series('', index=recent.index)
    
    close = recent['Close']
    macd_hist = recent['MACDh_12_26_9']
    
    if macd_hist.isna().all():
        return divs
    
    # Find local minima/maxima (simplified)
    window = 5
    for i in range(window, len(recent) - 1):
        idx = recent.index[i]
        
        # Check price lows
        price_slice = close.iloc[max(0, i-window):i+window+1]
        if close.iloc[i] == price_slice.min():
            # Local price low found — check MACD
            prev_lows = []
            for j in range(max(0, i-lookback), i):
                ps = close.iloc[max(0, j-window):j+window+1]
                if len(ps) > 0 and close.iloc[j] == ps.min() and j != i:
                    prev_lows.append(j)
            
            if prev_lows:
                prev_i = prev_lows[-1]
                prev_macd = macd_hist.iloc[prev_i] if prev_i < len(macd_hist) else None
                curr_macd = macd_hist.iloc[i]
                
                if prev_macd is not None and curr_macd is not None:
                    if not pd.isna(prev_macd) and not pd.isna(curr_macd):
                        # Regular bullish: price lower low, MACD higher low
                        if close.iloc[i] < close.iloc[prev_i] and curr_macd > prev_macd:
                            divs.iloc[i] = '상승 다이버전스'
                        # Hidden bullish: price higher low, MACD lower low
                        elif close.iloc[i] > close.iloc[prev_i] and curr_macd < prev_macd:
                            divs.iloc[i] = '히든 상승 다이버전스'
        
        # Check price highs
        price_slice_h = close.iloc[max(0, i-window):i+window+1]
        if close.iloc[i] == price_slice_h.max():
            prev_highs = []
            for j in range(max(0, i-lookback), i):
                ps = close.iloc[max(0, j-window):j+window+1]
                if len(ps) > 0 and close.iloc[j] == ps.max() and j != i:
                    prev_highs.append(j)
            
            if prev_highs:
                prev_i = prev_highs[-1]
                prev_macd = macd_hist.iloc[prev_i] if prev_i < len(macd_hist) else None
                curr_macd = macd_hist.iloc[i]
                
                if prev_macd is not None and curr_macd is not None:
                    if not pd.isna(prev_macd) and not pd.isna(curr_macd):
                        # Regular bearish: price higher high, MACD lower high
                        if close.iloc[i] > close.iloc[prev_i] and curr_macd < prev_macd:
                            divs.iloc[i] = '하락 다이버전스'
                        # Hidden bearish: price lower high, MACD higher high
                        elif close.iloc[i] < close.iloc[prev_i] and curr_macd > prev_macd:
                            divs.iloc[i] = '히든 하락 다이버전스'
    
    return divs

# ──────────────────────────────────────────────
# 통합 지표 계산 (Calculate All Indicators)
# ──────────────────────────────────────────────

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df['Date'] = pd.to_datetime(df['Date'])
    df.sort_values(by='Date', inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    close = df['Close']
    
    # ── MAs ──
    df['SMA_5'] = calculate_ma(close, 5)
    df['SMA_20'] = calculate_ma(close, 20)
    df['SMA_60'] = calculate_ma(close, 60)
    df['SMA_120'] = calculate_ma(close, 120)

    # ── RSI ──
    df['RSI_14'] = calculate_rsi(close, 14)
    
    # ── MACD ──
    macd, signal, hist = calculate_macd(close, 12, 26, 9)
    df['MACD_12_26_9'] = macd
    df['MACDs_12_26_9'] = signal
    df['MACDh_12_26_9'] = hist

    # ── Bollinger Bands ──
    lower, mid, upper = calculate_bbands(close, 20, 2)
    df['BBL_20_2.0'] = lower
    df['BBM_20_2.0'] = mid
    df['BBU_20_2.0'] = upper

    # ── ATR ──
    df['ATRr_14'] = calculate_atr(df, 14)
    
    # ── ADX ──
    adx, plus_di, minus_di = calculate_adx(df, 14)
    df['ADX_14'] = adx
    df['DI_plus_14'] = plus_di
    df['DI_minus_14'] = minus_di
    
    # ── 스토캐스틱 삼형제 ──
    df['STOCH_K_5'], df['STOCH_D_5'] = calculate_stochastic(df, 5, 3, 3)
    df['STOCH_K_10'], df['STOCH_D_10'] = calculate_stochastic(df, 10, 6, 6)
    df['STOCH_K_20'], df['STOCH_D_20'] = calculate_stochastic(df, 20, 12, 12)
    
    # ── 일목균형표 ──
    tenkan, kijun, span_a, span_b, chikou = calculate_ichimoku(df)
    df['ICH_TENKAN'] = tenkan
    df['ICH_KIJUN'] = kijun
    df['ICH_SPAN_A'] = span_a
    df['ICH_SPAN_B'] = span_b
    df['ICH_CHIKOU'] = chikou
    
    # ── 캔들스틱 패턴 ──
    df['CANDLE_PATTERN'] = detect_candle_patterns(df)
    
    # ── MACD 다이버전스 ──
    df['MACD_DIVERGENCE'] = detect_macd_divergence(df)
    
    # ── BB 밴드폭 (횡보 판단용) ──
    df['BB_WIDTH'] = (df['BBU_20_2.0'] - df['BBL_20_2.0']) / df['BBM_20_2.0']
    
    df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
    df = df.replace({np.nan: None})
    return df

def detect_support_resistance(df: pd.DataFrame, num_lines=5) -> list:
    recent_prices = df['Close'].dropna().tail(120).values
    if len(recent_prices) == 0:
        return []
    hist, bins = np.histogram(recent_prices, bins=20)
    top_indices = np.argsort(hist)[-num_lines:]
    sr_lines = []
    for idx in top_indices:
        level = (bins[idx] + bins[idx+1]) / 2.0
        sr_lines.append(round(level, 2))
    sr_lines.sort()
    return sr_lines
