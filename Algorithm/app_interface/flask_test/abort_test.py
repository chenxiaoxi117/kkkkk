import requests

# Flask 服务地址
BASE_URL = "http://127.0.0.1:5000"
# 测试 schUuid
with open("../uuid.txt", "r") as file:
    sch_uuid = file.readline().strip()  # 去掉换行符和多余空格
def test_task_abort():
    """
    测试任务终止接口
    """
    url = f"{BASE_URL}/api/v1/scheduling/task/abort"
    payload = {"schUuid": sch_uuid}
    
    try:
        response = requests.post(url, json=payload)
        print(f"Task Abort Response: {response.status_code}, {response.json()}")
    except Exception as e:
        print(f"Task Abort Error: {e}")

if __name__ == "__main__":
    print("Testing Task Abort...")
    test_task_abort()
