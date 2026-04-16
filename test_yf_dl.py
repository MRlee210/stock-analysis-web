import os
import yfinance as yf

# Set SSL certs paths
cert_path = os.path.abspath("cacert.pem")
os.environ["CURL_CA_BUNDLE"] = cert_path
os.environ["REQUESTS_CA_BUNDLE"] = cert_path
os.environ["SSL_CERT_FILE"] = cert_path

print("Testing download...")
try:
    df = yf.download("AAPL", period="1mo")
    print(df.head())
except Exception as e:
    print("Download error:", e)
