import requests

# Flask 服务地址
BASE_URL = "http://127.0.0.1:5000"
# 测试 schUuid
def test_task_status():
    """
    测试任务状态查询接口
    """
    url = f"{BASE_URL}/api/v1/scheduling/task/status"
    
    try:
        response = requests.get(url)
        print(f"Task Status Response: {response.status_code}, {response.json()}")
    except Exception as e:
        print(f"Task Status Error: {e}")

if __name__ == "__main__":
    print("Testing Task Status...")
    test_task_status()
