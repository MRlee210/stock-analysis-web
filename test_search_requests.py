import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
}

def search(q):
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={q}"
    res = requests.get(url, headers=headers, verify=False)
    print("Status:", res.status_code)
    try:
        data = res.json()
        for q in data.get('quotes', []):
            if q.get('quoteType') == 'EQUITY':
                print(q.get('symbol'), q.get('longname') or q.get('shortname'))
    except Exception as e:
        print("Error parsing json", e)

search('Apple')
