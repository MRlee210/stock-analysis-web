import pandas as pd
import yfinance as yf
import FinanceDataReader as fdr

# Cache krx items
_krx_df = None

def get_krx_data():
    global _krx_df
    if _krx_df is None:
        _krx_df = fdr.StockListing('KRX-DESC')
    return _krx_df

def get_all_sectors():
    df = get_krx_data()
    # Use 'Industry' instead of 'Sector' for better categorization
    sectors = df['Industry'].dropna().unique().tolist()
    sectors.sort()
    return sectors

def get_stocks_by_sector(sector_name: str):
    df = get_krx_data()
    sector_stocks = df[df['Industry'] == sector_name]
    return sector_stocks[['Code', 'Name']].to_dict(orient='records')

def search_stocks(query: str):
    """KRX 종목 검색"""
    df = get_krx_data()
    mask = df['Name'].str.contains(query, case=False, na=False)
    results = df[mask]
    return results[['Code', 'Name']].to_dict(orient='records')

def search_us_stocks(query: str):
    """미국 주식 종목 검색 - yfinance Search API 활용"""
    try:
        search_result = yf.Search(query, max_results=15)
        quotes = search_result.quotes
        results = []
        for q in quotes:
            symbol = q.get('symbol', '')
            name = q.get('longname') or q.get('shortname') or symbol
            # 미국 거래소 상장 주식만 (Equity 타입만)
            type_str = q.get('typeDisp', '')
            exchange = q.get('exchDisp', '')
            if type_str == 'Equity' and symbol:
                results.append({'Code': symbol, 'Name': name, 'Exchange': exchange})
        return results
    except Exception:
        # Fallback: ticker 직접 조회
        try:
            ticker_obj = yf.Ticker(query.upper())
            info = ticker_obj.info
            if info.get('longName'):
                return [{'Code': query.upper(), 'Name': info.get('longName', query.upper()), 'Exchange': info.get('exchange', '')}]
        except Exception:
            pass
        return []

def fetch_stock_data(ticker: str, period: str = "1y", market: str = "KR") -> pd.DataFrame:
    """주가 OHLCV 데이터 로드. market='KR' 또는 'US'"""
    ticker_clean = str(ticker).strip()
    start_date = pd.Timestamp.today() - pd.DateOffset(years=2)  # 2 years for 120MA and Ichimoku

    if market == "US":
        # 미국 주식: yfinance로 로드
        df = yf.download(ticker_clean.upper(), start=start_date.strftime('%Y-%m-%d'), auto_adjust=True)
    else:
        # 한국 주식: FDR 우선, 실패 시 yfinance fallback
        try:
            df = fdr.DataReader(ticker_clean, start=start_date.strftime('%Y-%m-%d'))
            if df.empty:
                df = yf.download(ticker_clean, period=period)
        except Exception:
            df = yf.download(ticker_clean, period=period)

    # yfinance 최신 버전은 MultiIndex 컬럼을 반환할 수 있으므로 flatten 처리
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.reset_index(inplace=True)
    # FinanceDataReader returns 'Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Change'
    return df
