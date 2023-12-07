import subprocess
import logging
import datetime
import socket
import sys
import yaml
import re
import time


def get_host_ip():
    """
    查询本机ip地址
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip


def check_ip(ip):
    """检查IP格式"""
    re_ip = re.compile(
        r'^((2([0-4]\d|5[0-5]))|[1-9]?\d|1\d{2})(\.((2([0-4]\d|5[0-5]))|[1-9]?\d|1\d{2})){3}$')
    result = re_ip.match(ip)
    if result:
        return True
    else:
        print(f"ERROR in IP format of {ip}, please check.")
        return False


# def exec_local_cmd(cmd):
#     """
#     命令执行
#     """
#     sub_conn = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
#     if sub_conn.returcode == 0:
#         result = sub_conn.stdout
#         return {"st": True, "rt": result}
#     else:
#         print(f"Can't to execute command: {cmd}")
#         err = sub_conn.stderr
#         print(f"Error message:{err}")
#         return {"st": False, "rt": err}


def exec_cmd(cmd):
    result = subprocess.getoutput(cmd)
    result = result.decode() if isinstance(result, bytes) else result
    log_data = f'{get_host_ip()} - {cmd} - {result}'
    Log().logger.info(log_data)
    if result:
        result = result.rstrip('\n')
    return result



class ConfFile(object):
    def __init__(self):
        self.yaml_file = 'ha_config.yaml'
        self.config = self.read_yaml()

    def read_yaml(self):
        """读YAML文件"""
        try:
            with open(self.yaml_file, 'r', encoding='utf-8') as f:
                yaml_dict = yaml.safe_load(f)
            return yaml_dict
        except FileNotFoundError:
            print("Please check the file name:", self.yaml_file)
        except TypeError:
            print("Error in the type of file name.")


class Log(object):
    def __init__(self):
        pass

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_instance'):
            Log._instance = super().__new__(cls)
            Log._instance.logger = logging.getLogger()
            Log._instance.logger.setLevel(logging.INFO)
            Log.set_handler(Log._instance.logger)
        return Log._instance

    @staticmethod
    def set_handler(logger):
        now_time = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        file_name = str(now_time) + '.log'
        fh = logging.FileHandler(file_name, mode='a')
        fh.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        fh.setFormatter(formatter)
        logger.addHandler(fh)
