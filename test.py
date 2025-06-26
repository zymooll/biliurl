import requests

url = "https://163.0061226.xyz/login/qr/key"
resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
print(resp.text)