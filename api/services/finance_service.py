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
    df = get_krx_data()
    mask = df['Name'].str.contains(query, case=False, na=False)
    results = df[mask]
    return results[['Code', 'Name']].to_dict(orient='records')

def fetch_stock_data(ticker: str, period: str = "1y") -> pd.DataFrame:
    # If ticker length is 6 digits entirely, append .KS or .KQ 
    # Actually FinanceDataReader can fetch generic KRX tickers easily, let's use yfinance for OHLCV
    # to maintain consistency with pandas_ta requirements. 
    # Wait, yfinance needs .KS or .KQ. For safety if it's numeric like 005930 -> 005930.KS.
    # Often Korean symbols need suffix in yf. Let's just use fdr for historical daily data! It's much safer for KRX.
    # FDR format: fdr.DataReader('005930', '2023')
    
    # Actually user might send something without suffix.
    ticker_clean = str(ticker).strip()
    
    # Fetch 1 year data back
    start_date = pd.Timestamp.today() - pd.DateOffset(years=2) # 2 years for 120MA and Ichimoku
    try:
        # Fdr works for KOSPI/KOSDAQ out of the box with numeric tickers
        df = fdr.DataReader(ticker_clean, start=start_date.strftime('%Y-%m-%d'))
        if df.empty:
            # Fallback to yfinance if it's an international ticker i.e., AAPL
            df = yf.download(ticker_clean, period=period)
    except Exception:
        df = yf.download(ticker_clean, period=period)
    
    # yfinance 최신 버전은 MultiIndex 컬럼을 반환할 수 있으므로 flatten 처리
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    df.reset_index(inplace=True)
    # Ensure standard names
    # FinanceDataReader returns 'Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Change'
    return df
