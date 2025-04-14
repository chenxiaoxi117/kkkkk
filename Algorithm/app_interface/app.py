from flask import Flask
from flask_cors import CORS
from topology import topology_bp
from scheduling import scheduling_bp
from result import result_bp
import os
os.environ['FLASK_DEBUG'] = 'production'
app = Flask(__name__)
CORS(app)
app.register_blueprint(topology_bp)  #获取当前调度任务所使用的拓扑资源接口
app.register_blueprint(scheduling_bp)#开始调度任务接口，查询调度状态接口，终端接口
app.register_blueprint(result_bp)
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
