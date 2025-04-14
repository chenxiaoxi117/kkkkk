import requests
import json
# 假设你有一个包含模拟数据的字典，或者你有实际的schUuid
with open("../uuid.txt", "r") as file:
    sch_uuid = file.readline().strip()  # 去掉换行符和多余空格
# 发送POST请求
url = 'http://127.0.0.1:5000/api/v1/scheduling/result/device/preview'
headers = {'Content-Type': 'application/json'}  # 声明请求的JSON格式
payload = {"schUuid": sch_uuid}
response = requests.post(url, json=payload)
# 检查响应状态码
if response.status_code == 200:
    # 如果状态码是200，表示请求成功，你可以获取JSON响应数据
    response_data = response.json()
    print("Success! Preview data:")
    print(response_data)
else:
    print(f"Request failed with status code: {response.status_code}")
    print("Error message:", response.json().get("errorMsg"))

# 打印其他状态码时的错误消息，比如500
print(response.json().get("errorMsg", "No error message provided"))