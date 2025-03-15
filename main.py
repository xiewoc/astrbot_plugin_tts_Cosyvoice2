#有关tts的详细配置请移步service.py
from astrbot.api.all import *
from astrbot.api.provider import ProviderRequest
from astrbot.api.provider import LLMResponse
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from multiprocessing import Process
import atexit
import subprocess
import glob
import requests
import json

global on_init , reduce_parenthesis
on_init = True
reduce_parenthesis = False

def load_json_config(file_name):# return text
    base_name = os.path.splitext(file_name)[0]
    # 构建对应的.json文件名
    json_file = f"{base_name}.json"
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'sounds',json_file)
    # 检查对应的.json文件是否存在
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            ret_list = [data.get('text'),data.get('form')]
            return ret_list
    else:
        print(f"未找到匹配的.json文件")


def find_wav_and_json_files(directory):
    # 改变当前工作目录到指定目录
    os.chdir(directory)
    all_files = ''
    # 查找所有.wav文件
    wav_files = glob.glob('*.wav')
    
    for wav_file in wav_files:
        all_files += wav_file + '\n'
    return all_files

def run_command(command):#cmd line  git required!!!!
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, error = process.communicate()
    if error:
        print(f"Error: {error.decode()}")
    return output.decode()

# 锁文件路径
lock_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),"child_process.lock")

def cleanup():
    """清理函数，用于在程序结束时删除锁文件"""
    if os.path.exists(lock_file_path):
        os.remove(lock_file_path)

def child_process_function(remove_think_tag,instruct_speech_form ,zero_shot_text ,generate_method ,use_trt ,use_fp16 ,source_prompt):
    #print(remove_think_tag,"when passing arg remove_think_tag")#debug
    import service 
    service.run_service(remove_think_tag,instruct_speech_form ,zero_shot_text ,generate_method ,use_trt ,use_fp16 ,source_prompt)

def start_child_process(remove_think_tag,instruct_speech_form ,zero_shot_text ,generate_method ,use_trt ,use_fp16 ,source_prompt):
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
    p = Process(
        target=child_process_function,
        args=(
            remove_think_tag,
            instruct_speech_form,
            zero_shot_text ,
            generate_method,
            use_trt,
            use_fp16,
            source_prompt,
            )
        )
    p.start()
    print("sub process started")
    return p

def terminate_child_process_on_exit(child_process):
    """注册一个函数，在主进程退出时终止子进程"""
    def cleanup_on_exit():
        if child_process and child_process.is_alive():
            child_process.terminate()
            child_process.join()  # 确保子进程已经完全终止
            print("Service.py process terminated.")
        cleanup()
    atexit.register(cleanup_on_exit)

@register("astrbot_plugin_tts_Cosyvoice2", "xiewoc ", "extention in astrbot for tts using local Cosyvoice2-0.5b model to create api in OpenAI_tts_api form", "1.0.6", "https://github.com/xiewoc/astrbot_plugin_tts_Cosyvoice2")
class astrbot_plugin_tts_Cosyvoice2(Star):
    def __init__(self, context: Context,config: dict):
        super().__init__(context)
        self.config = config
        
        global reduce_parenthesis
        reduce_parenthesis = self.config['if_reduce_parenthesis']
        
        sub_config = self.config.get('misc', {})
        
        child_process = start_child_process(            #传递参数
            self.config['if_remove_think_tag'],
            sub_config.get('instruct_speech_form', '') ,
            sub_config.get('zero_shot_text', '') ,
            self.config['generate_method'],
            self.config['if_trt'],
            self.config['if_fp16'],
            sub_config.get('source_prompt', '')
            )
        if child_process:
            terminate_child_process_on_exit(child_process)

    @filter.command_group("tts_cfg")
    def tts_cfg(self):
        pass

    @tts_cfg.group("set")
    def set(self):
        pass
    
    @set.command("voice")
    async def voice(self, event: AstrMessageEvent, sound:str):
        ret = load_json_config(sound)#fomant: list
        payload = {
            "speech_form": ret[1],  
            "prompt_text": ret[0],  
            "voice": sound  
            }
        requests.post('http://127.0.0.1:5050/config', json=payload)
        yield event.plain_result(f"音源更换成功: {sound}")

    @set.command("form")
    async def form(self, event: AstrMessageEvent, form:str):
        payload = {
            "speech_form": form,  
            "prompt_text": "",  
            "voice": "" 
            }
        requests.post('http://127.0.0.1:5050/config', json=payload)
        yield event.plain_result(f"方言更换成功: {form}")

    @tts_cfg.command("list")
    async def list(self, event: AstrMessageEvent):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'sounds')
        opt = str(find_wav_and_json_files(path))
        yield event.plain_result(opt)
    
    @filter.on_llm_request()
    async def on_call_llm(self, event: AstrMessageEvent, req: ProviderRequest): # 请注意有三个参数
        global reduce_parenthesis
        if reduce_parenthesis == True:
            req.system_prompt += "请在输出的字段中减少在括号中对动作、心情等的描写，尽量只剩下口语部分"

if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)),'CosyVoice')):#克隆仓库
    if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)),'CosyVoice','cosyvoice')):
        pass
    else:
        base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),'CosyVoice')
        run_command(f"git clone --recursive https://github.com/FunAudioLLM/CosyVoice.git {base_dir}")
    pass
else:
    if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)),'CosyVoice','cosyvoice')):
        pass
    else:
        base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),'CosyVoice')
        run_command(f"git clone --recursive https://github.com/FunAudioLLM/CosyVoice.git {base_dir}")
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),'CosyVoice')
    run_command(f"git clone --recursive https://github.com/FunAudioLLM/CosyVoice.git {base_dir}")
    from modelscope import snapshot_download
    snapshot_download('iic/CosyVoice2-0.5B', local_dir=os.path.join(os.path.dirname(os.path.abspath(__file__)),'pretrained_models','CosyVoice2-0.5B'))#下载模型
