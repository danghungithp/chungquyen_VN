# api_client.py
import requests

def ssi_warrant_price(symbol, api_key):
    headers = {'Authorization': f'Bearer {api_key}'}
    url = f"https://api.ssi.com.vn/market/warrant/{symbol}"
    return requests.get(url, headers=headers).json()['price']
