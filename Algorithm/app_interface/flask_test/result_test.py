import requests
import json

# Flask服务器的URL
url = 'http://127.0.0.1:5000/api/v1/scheduling/result'
with open("../uuid.txt", "r") as file:
    test_sch_uuid = file.readline().strip()  # 去掉换行符和多余空格
# 构造请求体
data = {
    'schUuid': test_sch_uuid
}

# 发送POST请求
response = requests.post(url, json=data)

# 打印响应内容
print("Status Code:", response.status_code)
print("Response Body:", response.json())
