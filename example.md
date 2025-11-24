python

import time
import hmac
import hashlib

API_KEY = 'your-secret-key'
timestamp = int(time.time())
sign_str = f"{API_KEY}:{timestamp}"
signature = hmac.new(API_KEY.encode(), sign_str.encode(), hashlib.sha256).hexdigest()

# 作为查询参数
url = f"http://127.0.0.1:8000/api/bili/BV1u9kUBfEZA?type=raw&key={API_KEY}&ts={timestamp}&sig={signature}"

Request
headers = {
    'X-API-Key': 'your-secret-key',
    'X-Timestamp': str(timestamp),
    'X-Signature': signature
}


Csharp
long timestamp = (long)(System.DateTime.UtcNow - System.DateTime.UnixEpoch).TotalSeconds;
string signStr = $"{API_KEY}:{timestamp}";
string signature = HMAC_SHA256(API_KEY, signStr);
string url = $"http://api.example.com/api/bili/BV1u9kUBfEZA?type=raw&key={API_KEY}&ts={timestamp}&sig={signature}";