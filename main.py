#有关tts的详细配置请移步service.py
from astrbot.api.all import *
from astrbot.api.provider import ProviderRequest
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from multiprocessing import Process
import atexit

from service import *
global on_init 
on_init = True

# 锁文件路径
lock_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),"child_process.lock")

def cleanup():
    """清理函数，用于在程序结束时删除锁文件"""
    if os.path.exists(lock_file_path):
        os.remove(lock_file_path)

def child_process_function():
    run_service()

def start_child_process():
    global on_init 

    """启动子进程的函数"""
    if os.path.exists(lock_file_path):
        if on_init == True:
	    cleanup()
	    on_init = False
            pass
	else:
            print("Another instance of the child process is already running.")
            return None
    
    # 创建锁文件
    with open(lock_file_path, 'w') as f:
        f.write("Locked")
    
    # 注册清理函数
    atexit.register(cleanup)
    
    # 创建并启动子进程
    p = Process(target=child_process_function)
    p.start()
    return p

def terminate_child_process_on_exit(child_process):
    """注册一个函数，在主进程退出时终止子进程"""
    def cleanup_on_exit():
        if child_process and child_process.is_alive():
            print("Terminating child process...")
            child_process.terminate()
            child_process.join()  # 确保子进程已经完全终止
            print("Child process terminated.")
        cleanup()
    atexit.register(cleanup_on_exit)

@register("astrbot_plugin_tts_Cosyvoice2", "xiewoc ", "extention in astrbot for tts using local Cosyvoice2-0.5b model to create api in OpenAI_tts_api form", "0.0.2", "https://github.com/xiewoc/astrbot_plugin_tts_Cosyvoice2")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

child_process = start_child_process()
if child_process:
    terminate_child_process_on_exit(child_process)
    
