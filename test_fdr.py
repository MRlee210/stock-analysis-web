import FinanceDataReader as fdr

def test_fdr_us():
    try:
        print("Testing FDR NASDAQ...")
        df_nasdaq = fdr.StockListing('NASDAQ')
        print(df_nasdaq.head())
        # Search Apple
        apple = df_nasdaq[df_nasdaq['Name'].str.contains('Apple', case=False, na=False)]
        print("Apple:", apple[['Symbol', 'Name']].to_dict(orient='records'))
    except Exception as e:
        print("Error:", e)

test_fdr_us()
