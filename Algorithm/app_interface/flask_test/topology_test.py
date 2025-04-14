import requests
import json

# 定义要测试的 API 地址
api_url = "http://127.0.0.1:5000/api/v1/scheduling/topology"

def test_get_topology():
    headers = {
        'Accept': '*/*',
        'User-Agent': 'curl/7.64.1'
    }
    try:
        # 发送 GET 请求，并设置与 curl 相同的请求头
        response = requests.get(api_url, headers=headers)
        # 检查响应状态码
        if response.status_code == 200:
            print("API Test Passed: Status Code 200")
            # 打印响应内容
            print("Response Data:")
            print(response.json())
        else:
            print(f"API Test Failed: Status Code {response.status_code}")
            print("Response Data:")
            print(response.text)
    except requests.exceptions.RequestException as e:
        # 打印请求异常信息
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    test_get_topology()
