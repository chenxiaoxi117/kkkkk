from flask import Blueprint, request, jsonify
import json
from flask_cors import CORS
from log.log import log_debug,log_error
# 创建 Blueprint 实例
topology_bp = Blueprint('topology', __name__)
@topology_bp.route('/api/v1/scheduling/topology', methods=['GET'])
def get_topology():
    try:
        json_file_path="./data/topology.json"
        # 从 JSON 文件中读取数据
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        #  JSON 数据包含节点和链路信息
        node_list = data.get('nodeList', [])
        link_list = data.get('linkList', [])
        log_debug(f"成功获取拓扑数据")
        # 构建返回的数据格式
        response = {
            "errorCode": 0,
            "errorMsg": "",
            "message": {
                "nodeList": node_list,
                "linkList": link_list
            }
        }

        return jsonify(response)  # 返回 JSON 格式的数据

    except FileNotFoundError:
        # 返回文件未找到的错误
        return jsonify({
            "errorCode": 500,
            "errorMsg": "File not found",
            "message": {}
        }), 404
    except Exception as e:
        log_error(f"获取拓扑数据出错: {e}")
        # 处理其他错误
        return jsonify({
            "errorCode": 500,
            "errorMsg": str(e),
            "message": {}
        }), 500



