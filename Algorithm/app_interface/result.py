import os
import sys
import time
import uuid
import json
import threading
import subprocess
import concurrent.futures
import regex as re
import pandas as pd
import xml.etree.ElementTree as ET
from io import BytesIO
from log.log import log_debug, log_error
from flask import Flask, request, jsonify, send_file, Blueprint
from scheduling import getfrom_algorithm, getfrom_scheduling_results, getfrom_device_results, getform_data

result_bp = Blueprint('result', __name__)


@result_bp.route('/api/v1/scheduling/result', methods=['POST'])
def get_scheduling_result():
    try:
        # 获取前端请求体中的 JSON 数据
        data = request.get_json()
        User_configuration = getform_data()
        sch_uuid = data.get('schUuid')  # 获取 UUID
        # 检查是否提供了 schUuid
        if not sch_uuid:
            return jsonify({
                "errorCode": 500,
                "errorMsg": "Missing schUuid",
                "message": {},
                "User_configuration": {}
            }), 400
        # 加载任务结果数据
        scheduling_results = getfrom_scheduling_results()
        if scheduling_results is None:
            log_error(f"调度信息数据不存在")
            return jsonify({
                "errorCode": 500,
                "errorMsg": "Error loading task results data",
                "message": {},
                "User_configuration": {}
            }), 500
        # 查找任务结果
        result = scheduling_results.get(sch_uuid)
        if result:
            log_debug(f"{sch_uuid}任务下的调度信息成功返回")
            # 如果找到调度结果，返回结果
            return jsonify({
                "errorCode": 0,
                "errorMsg": "",
                "message": result,
                "User_configuration": User_configuration
            })
        else:
            # 如果找不到任务结果，返回错误信息
            log_error(f"{sch_uuid}对应的调度信息数据不存在")
            return jsonify({
                "errorCode": 500,
                "errorMsg": "scheduling result not found",
                "message": {},
                "User_configuration": {}
            }), 404
    except Exception as e:
        log_error(f"获取调度信息数据出错: {e}")
        # 捕获异常并返回错误信息
        return jsonify({
            "errorCode": 500,
            "errorMsg": str(e),
            "message": {},
            "User_configuration": {}
        }), 500


@result_bp.route('/api/v1/scheduling/result/device/preview', methods=['POST'])
def preview_device_results():
    try:
        # 从请求中获取参数
        data = request.get_json()
        sch_uuid = data.get("schUuid")  # 获取调度任务的 UUID
        limit = 20  # 默认展示为前X条，可以自己设置
        # 验证 schUuid 是否存在
        device_results = getfrom_device_results()
        if sch_uuid not in device_results:
            return jsonify({
                "errorCode": 500,
                "errorMsg": "device_results not found",
                "message": []
            }), 404
        # 获取对应 schUuid 的设备调度结果
        results = device_results[sch_uuid]
        # 如果 limit 大于 0，则限制结果集的大小
        if limit > 0 and limit < len(results):
            log_debug(f"{sch_uuid}任务下的结果信息成功返回，默认展示为前{limit}条数据")
            preview_results = results[:limit]  # 返回前 limit 条数据
        else:
            preview_results = results  # 如果没有指定 limit 或 limit 为 0，则返回所有数据
        # 返回符合条件的调度结果预览
        return jsonify({
            "errorCode": 0,
            "errorMsg": "",
            "message": preview_results
        })

    except Exception as e:
        log_error(str(e))
        return jsonify({
            "errorCode": 500,
            "errorMsg": str(e),
            "message": []
        }), 500


@result_bp.route('/api/v1/scheduling/result/device', methods=['POST'])
def filter_device_results():
    try:
        # 从请求中获取参数
        data = request.get_json()
        sch_uuid = data.get("schUuid")
        pageNumber = data.get("pageNumber", 1)  # 默认为第一页
        pageSize = data.get("pageSize", 50)  # 默认每页条数
        filter_criteria = data.get("filter", {})
        device_results = getfrom_device_results()
        # 验证 schUuid 是否存在
        if sch_uuid not in device_results:
            log_error(f"筛选结果不存在")
            return jsonify({
                "errorCode": 500,
                "errorMsg": "results not found",
                "message": [],
                "total": 0
            }), 404
        # 获取对应 schUuid 的设备调度结果
        results = device_results[sch_uuid]
        # 根据筛选条件过滤结果
        filtered_results = []
        for result in results:
            # 筛选时延范围
            if result.get("latency") == 'N/A':
                if all(result.get(key) == value for key, value in filter_criteria.items()
                       if key not in ["min_latency", "max_latency"]):
                    filtered_results.append(result)
            else:
                latency = float(result.get("latency"))
                latency_min = filter_criteria.get("min_latency")
                latency_max = filter_criteria.get("max_latency")
                if latency_min is not None and latency < latency_min:
                    continue  # 如果时延小于最小值，跳过该条记录
                if latency_max is not None and latency > latency_max:
                    continue  # 如果时延大于最大值，跳过该条记录
                # 根据其他筛选条件（如设备属性、路径等）进行筛选
                if all(result.get(key) == value for key, value in filter_criteria.items()
                       if key not in ["min_latency", "max_latency"]):
                    filtered_results.append(result)
        # 计算总条数
        total = len(filtered_results)
        # 根据 pageNumber 和 pageSize 进行分页
        start_index = (pageNumber - 1) * pageSize
        end_index = start_index + pageSize
        page_results = filtered_results[start_index:end_index]
        # 如果 limit 大于 0，则限制结果集数量
        log_debug(f"{sch_uuid}任务下用户筛选后的结果信息成功返回，展示为筛选后的第{pageNumber}页数据")
        # 返回符合条件的调度结果
        return jsonify({
            "errorCode": 0,
            "errorMsg": "",
            "message": page_results,
            "total": total
        })
    except Exception as e:
        log_error(f"获取筛结果出错: {e}")
        return jsonify({
            "errorCode": 500,
            "errorMsg": str(e),
            "message": [],
            "total": 0
        }), 500


@result_bp.route('/api/v1/scheduling/result/device/export', methods=['POST'])
def upload_file():
    try:
        UPLOAD_FOLDER = '../result'  # 文件保存在这个目录下
        file_names = ["tradeoff_results.csv", "trade_off_improved_results.csv",
                      "round_robin_results.csv", "greedy_allocation_results.csv"]
        algorithm = getfrom_algorithm()
        file_name = file_names[algorithm - 1]
        file_path = os.path.join(UPLOAD_FOLDER, file_name)
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return jsonify({
                "errorCode": 500,
                "errorMsg": "File not found",
                "message": {}
            }), 404
        log_debug(f"成功返回文件:{file_names[algorithm - 1]}")
        # 使用 send_file 将文件返回给客户端
        return send_file(
            file_path,
            as_attachment=True,  # 设置为附件下载
            download_name=file_name,  # 设置下载文件的名称
            mimetype='text/csv',  # 设置文件类型为 CSV
            last_modified=True
        )  # NO SONAR

    except Exception as e:
        log_error(f"导出文件出错: {e}")
        return jsonify({
            "errorCode": 500,
            "errorMsg": str(e),
            "message": {}
        }), 500
