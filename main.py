#有关tts的详细配置请移步service.py
from astrbot.api.all import *
from astrbot.api.provider import ProviderRequest
from astrbot.api.provider import LLMResponse
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.message_components import *
from astrbot.api.star import Context, Star, register
import sys
import os
from multiprocessing import Process
import atexit
import subprocess
import glob
import requests
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

global on_init ,reduce_parenthesis
on_init = True
reduce_parenthesis = False

global server_ip
global if_remove_think_tag ,instruct_speech_dialect ,zero_shot_text ,generate_method ,if_trt ,if_fp16 ,if_jit ,if_preload ,source_prompt

async def request_tts(text: str):
    payload = {
        "model": "",
        "input": text,
        "voice": ""
    }
    global server_ip
    if server_ip != '':
        url = 'http://' + server_ip + ':5050/audio/speech'
        try:
            # 设置超时时间为60秒
            response = requests.post(url, json=payload, stream=True, timeout=(5, 60))
            if response.status_code == 200:
                # 打开一个本地文件用于写入
                file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'file_receive.mp3')
                with open(file_path, 'wb') as file:
                    # 逐块写入文件
                    for chunk in response.iter_content(chunk_size=8192):
                        file.write(chunk)
                    return file_path
            else:
                print(f"请求失败，状态码: {response.status_code}")
                return ''
        except requests.exceptions.Timeout:
            print("请求超时，服务器未在60秒内响应")
            return ''
        except requests.exceptions.RequestException as e:
            print(f"请求发生错误: {e}")
            return ''
    else:
        print("Server url is void, please check your settings")
        return ''

def request_config(speech_dialect: str ,prompt_text: str ,prompt_file_name: str ,generate_method: str ,ip:str):
    payload = {
            "speech_dialect": speech_dialect,  
            "prompt_text": prompt_text,  
            "voice": prompt_file_name ,
            "generate_method": generate_method
            }
    url = 'http://' + ip + ':5050/config'
    ret = requests.post(url, json=payload, timeout=(10, 20))
    return ret

def request_config_init(speech_dialect: str ,prompt_text: str ,prompt_file_name: str ,generate_method: str ,if_jit: bool ,if_trt: bool ,if_fp16: bool ,if_preload: bool ,if_remove_think_tag: bool ,ip: str):
    payload = {
            "speech_dialect": speech_dialect,  
            "prompt_text": prompt_text,  
            "voice": prompt_file_name,
            "generate_method": generate_method,
            "if_jit": if_jit,
            "if_trt": if_trt,
            "if_fp16": if_fp16,
            "if_preload": if_preload,
            "if_remove_think_tag": if_remove_think_tag
            }
    url = 'http://' + ip + ':5050/config/init'
    ret = requests.post(url, json=payload, timeout=(20, 45))
    return ret

def load_json_config(file_name):# return text
    base_name = os.path.splitext(file_name)[0]
    # 构建对应的.json文件名
    json_file = f"{base_name}.json"
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'sounds',json_file)
    # 检查对应的.json文件是否存在
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            ret_list = [data.get('text'),data.get('form'),data.get('generate_method')]
            return ret_list
    else:
        print(f"未找到匹配的.json文件,使用默认模式")
        return []

def download_model_and_repo():
    if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)),'CosyVoice')):#克隆仓库
        pass
    else:
        base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),'CosyVoice')
        run_command(f"git clone --recursive https://github.com/FunAudioLLM/CosyVoice.git {base_dir}")
    if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)),'pretrained_models','CosyVoice2-0.5B')):
        pass
    else:
        from modelscope import snapshot_download
        snapshot_download('iic/CosyVoice2-0.5B', local_dir=os.path.join(os.path.dirname(os.path.abspath(__file__)),'pretrained_models','CosyVoice2-0.5B'))#下载模型

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

def child_process_function():
    import service 
    service.run_service()

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
    p = Process(
        target=child_process_function,
        args=()
        )
    p.start()
    print("Sub process (service.py) started")
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

@register("astrbot_plugin_tts_Cosyvoice2", "xiewoc ", "extention in astrbot for tts using local Cosyvoice2-0.5b model to create api in OpenAI_tts_api form", "1.0.7", "https://github.com/xiewoc/astrbot_plugin_tts_Cosyvoice2")
class astrbot_plugin_tts_Cosyvoice2(Star):
    def __init__(self, context: Context,config: dict):
        super().__init__(context)

        download_model_and_repo()

        self.config = config
        sub_config_misc = self.config.get('misc', {})
        sub_config_serve = self.config.get('serve_config', {})
        #读取设置

        global reduce_parenthesis#减少‘（）’提示词
        reduce_parenthesis = self.config['if_reduce_parenthesis']
        global server_ip
        server_ip = sub_config_serve.get('server_ip', '')
        
        global if_remove_think_tag ,instruct_speech_dialect ,zero_shot_text ,generate_method ,if_trt ,if_fp16 ,if_jit ,if_preload ,source_prompt
        if_remove_think_tag = self.config['if_remove_think_tag']
        generate_method = self.config['generate_method']
        instruct_speech_dialect = sub_config_misc.get('instruct_speech_dialect', '') 
        zero_shot_text = sub_config_misc.get('zero_shot_text', '')
        source_prompt = sub_config_misc.get('source_prompt', '')
        if_trt = self.config['if_trt']
        if_fp16 = self.config['if_fp16']
        if_jit =  self.config['if_jit']
        if_preload =  self.config['if_preload']

        if sub_config_serve.get('if_seperate_serve', ''):#若为分布式部署
            pass
        else:
            child_process = start_child_process()
            if child_process:
                terminate_child_process_on_exit(child_process)

        request_config_init(
            instruct_speech_dialect,
            zero_shot_text,
            source_prompt,
            generate_method,
            if_jit,
            if_trt,
            if_fp16,
            if_preload,
            if_remove_think_tag,
            server_ip
                )

    @filter.command_group("tts_cfg")
    def tts_cfg(self):
        pass

    @tts_cfg.group("set")
    def set(self):
        pass
    
    @set.command("voice")
    async def voice(self, event: AstrMessageEvent, prompt_file_name: str):
        ret = load_json_config(prompt_file_name)#fomant: list
        '''
        request_config(speech_dialect:str,prompt_text:str,prompt_file_name:str,ip:str)
        '''
        global server_ip
        if ret == []:
            request_config('普通话', '', prompt_file_name, 'instruct2', server_ip)
        else:
            request_config(ret[1], ret[0], prompt_file_name, ret[2], server_ip)
        yield event.plain_result(f"音源更换成功: {prompt_file_name}")

    @set.command("dialect")
    async def dialect(self, event: AstrMessageEvent, dialect: str):
        global server_ip
        request_config(dialect ,'' , '', '', server_ip)
        yield event.plain_result(f"方言更换成功: {dialect}")

    @set.command("method")
    async def method(self, event: AstrMessageEvent, method: str):
        global server_ip
        request_config('' ,'' , '', method, server_ip)
        yield event.plain_result(f"生成方式更换成功: {method}")

    @tts_cfg.command("list")
    async def list(self, event: AstrMessageEvent):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'sounds')
        opt = str(find_wav_and_json_files(path))
        yield event.plain_result(opt)
    
    @filter.on_llm_request()
    async def on_call_llm(self, event: AstrMessageEvent, req: ProviderRequest): # 请注意有三个参数
        global reduce_parenthesis
        if reduce_parenthesis == True:
            req.system_prompt += "请在输出的字段中减少使用括号括起对动作,心情,表情等的描写，尽量只剩下口语部分"

    @llm_tool(name="send_vocal_msg") 
    async def send_vocal_msg(self, event: AstrMessageEvent, text: str) -> MessageEventResult:
        '''发送语音消息。

        Args:
            text(string): 要转语音的文字
        '''
        if text != '':
            path = await request_tts(text)#返回的是mp3文件
            chain = [
                Record.fromFileSystem(path)
                ]
            yield event.chain_result(chain)
        #if text_not_to_tts != '':
        #    yield event.plain_result(text_not_to_tts)