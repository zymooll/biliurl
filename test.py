import json

cookie_example = "{'code': 803, 'message': '授权登陆成功', 'cookie': '123123'}"
cookie_example = cookie_example.replace("'", '"')  # 替换单引号为双引号（JSON 标准要求）
cookie = json.loads(cookie_example)
print(cookie)