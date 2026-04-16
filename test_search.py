import os
import yfinance as yf

# Set SSL certs paths
cert_path = os.path.abspath("cacert.pem")
os.environ["CURL_CA_BUNDLE"] = cert_path
os.environ["REQUESTS_CA_BUNDLE"] = cert_path
os.environ["SSL_CERT_FILE"] = cert_path

try:
    print("Testing yf.Search with env vars...")
    res = yf.Search("Apple", max_results=15)
    print("Search Result Quotes:")
    print(res.quotes)
except Exception as e:
    print("yf.Search error:", str(e))

try:
    print("\nTesting fallback Ticker search...")
    ticker = yf.Ticker("AAPL")
    print(ticker.info.get('longName'))
except Exception as e:
    print("Ticker error:", str(e))
