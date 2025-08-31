#有关tts的详细配置请移步service.py
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult          # pyright: ignore[reportMissingImports] 
from astrbot.api.star import Context, Star, register                                # pyright: ignore[reportMissingImports] 
from astrbot.api.provider import ProviderRequest                                    # pyright: ignore[reportMissingImports] 
from astrbot.api.message_components import *                                        # pyright: ignore[reportMissingImports] 
from astrbot.api import logger                                                      # pyright: ignore[reportMissingImports]
from astrbot.core.utils.astrbot_path import get_astrbot_data_path                   # pyright: ignore[reportMissingImports]
from multiprocessing import Process
from typing import Callable, Optional, Any
from pathlib import Path
import aiohttp
import asyncio
import os
import json


# 锁文件路径
lock_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),"child_process.lock")

temp_dir = os.path.join(get_astrbot_data_path(), "temp")
output_path = os.path.join(temp_dir,"output.wav")

class RequestTTSandConfig():
    def __init__(self):
        self.port = "5050"

    async def async_retry_request(
            self,
            request_func: Callable,
            max_retries: int = 20,
            initial_retry_delay: float = 2.0,
            max_retry_delay: float = 60.0,
            backoff_factor: float = 2.0,
            retry_exceptions: tuple = (asyncio.TimeoutError, aiohttp.ClientError),
            **kwargs
        ) -> Any:
        """
        通用的异步重试请求函数
        
        Args:
            request_func: 要执行的请求函数
            max_retries: 最大重试次数
            initial_retry_delay: 初始重试延迟（秒）
            max_retry_delay: 最大重试延迟（秒）
            backoff_factor: 退避因子
            retry_exceptions: 需要重试的异常类型
            **kwargs: 传递给请求函数的参数
        
        Returns:
            请求函数的返回结果
        
        Raises:
            ConnectionError: 所有重试都失败时抛出
            Exception: 不可重试的异常
        """
        retry_count = 0
        last_error = None
        
        while retry_count <= max_retries:
            try:
                result = await request_func(**kwargs)
                return result
                
            except retry_exceptions as e:
                last_error = e
                retry_count += 1
                if retry_count > max_retries:
                    break
                    
                delay = min(
                    initial_retry_delay * (backoff_factor ** (retry_count - 1)),
                    max_retry_delay
                )
                
                logger.warning(
                    f"请求失败({str(e)}), 正在进行第 {retry_count}/{max_retries} 次重试, "
                    f"等待 {delay:.1f} 秒后重试..."
                )
                
                await asyncio.sleep(delay)
                
            except Exception as e:
                logger.error(f"发生不可重试的错误: {str(e)}")
                raise
        
        logger.error(f"所有重试均失败, 最后错误: {str(last_error)}")
        raise ConnectionError(f"无法完成请求, 重试 {max_retries} 次后失败") from last_error

    # 具体的请求函数
    async def _post_config_request(
            self,
            server_ip: str,
            port: str,
            speech_name: str,
            prompt_text: str,
            speech_dialect: str,
            generate_method,
            CORRECT_API_KEY: str,
            timeout_seconds: Optional[float] = 60.0,
            **kwargs
        ) -> dict:
        """具体的POST配置请求实现"""
        url = f"http://{server_ip}:{port}/config"
        payload = {
            "speech_name": speech_name,
            "prompt_text": prompt_text,
            "speech_dialect": speech_dialect,
            "generate_method": generate_method,
            "CORRECT_API_KEY": CORRECT_API_KEY
        }
        
        # 处理可选参数
        
        payload["if_remove_think_tag"] = kwargs["if_remove_think_tag"] if "if_remove_think_tag" in kwargs else False
        
        payload["if_remove_emoji"] = kwargs["if_remove_emoji"] if "if_remove_emoji" in kwargs else False

        payload["if_preload"] = kwargs["if_preload"] if "if_preload" in kwargs else False

        payload["if_fp16"] = kwargs["if_fp16"] if "if_fp16" in kwargs else False

        payload["if_jit"] = kwargs["if_jit"] if "if_jit" in kwargs else False

        payload["if_trt"] = kwargs["if_trt"] if "if_trt" in kwargs else False
        
        headers = {
            'Authorization': f'Bearer {CORRECT_API_KEY}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
            async with session.post(url, json=payload) as response:
                response.raise_for_status()
                result = await response.json()
                logger.info(f"请求成功: {result}")
                return result

    async def _post_generate_request(
            self,
            server_ip: str,
            port: str,
            text: str,
            CORRECT_API_KEY: str,
            output_path: str,
            timeout_seconds: Optional[float] = 60.0,
        ) -> str:
            """具体的POST生成请求实现"""
            url = f"http://{server_ip}:{port}/audio/speech"
            payload = {
                "model": "",
                "input": text,
                "voice": ""
            }

            headers = {
                'Authorization': f'Bearer {CORRECT_API_KEY}',
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            
            timeout = aiohttp.ClientTimeout(total=timeout_seconds)
            async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
                async with session.post(url, json=payload) as response:
                    response.raise_for_status()
                    
                    # 检查响应内容类型
                    content_type = response.headers.get('Content-Type', '')
                    
                    if 'audio/wav' in content_type or 'audio/x-wav' in content_type:
                        # 处理音频文件响应
                        output_path_path = Path(output_path)
                        output_path_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        with open(output_path_path, 'wb') as f:
                            while True:
                                chunk = await response.content.read(1024)
                                if not chunk:
                                    break
                                f.write(chunk)
                        
                        logger.info(f"音频文件成功保存到: {output_path_path}")
                        return str(output_path_path)
                    else:
                        # 如果不是音频文件，尝试解析为JSON
                        result = await response.json()
                        logger.info(f"请求成功: {result}")
                    return result

    # 重构后的原始方法
    async def post_config_with_session_auth(
            self,
            server_ip: str,
            port: str,
            speech_name: str,
            prompt_text: str,
            speech_dialect: str,
            generate_method: str,
            CORRECT_API_KEY: str,
            timeout_seconds: Optional[float] = 60.0,
            max_retries: int = 20,
            initial_retry_delay: float = 1.0,
            max_retry_delay: float = 60.0,
            backoff_factor: float = 2.0,
            **kwargs
        ) -> dict:
        """发送带认证的POST请求到指定服务器，具有自动重试机制"""
        return await self.async_retry_request(
            request_func=self._post_config_request,
            max_retries=max_retries,
            initial_retry_delay=initial_retry_delay,
            max_retry_delay=max_retry_delay,
            backoff_factor=backoff_factor,
            server_ip=server_ip,
            port=port,
            speech_name=speech_name,
            prompt_text=prompt_text,
            speech_dialect=speech_dialect,
            generate_method=generate_method,
            CORRECT_API_KEY=CORRECT_API_KEY,
            timeout_seconds=timeout_seconds,
            **kwargs
        )

    async def post_generate_request_with_session_auth(
        self,
        server_ip: str,
        port: str,
        text: str,
        CORRECT_API_KEY: str,
        output_path: str,
        timeout_seconds: Optional[float] = 60.0,
        max_retries: int = 20,
        initial_retry_delay: float = 1.0,
        max_retry_delay: float = 60.0,
        backoff_factor: float = 2.0
    ) -> str:
        """发送带认证的POST请求到指定服务器，具有自动重试机制，返回保存的音频文件路径"""
        return await self.async_retry_request(
            request_func=self._post_generate_request,
            max_retries=max_retries,
            initial_retry_delay=initial_retry_delay,
            max_retry_delay=max_retry_delay,
            backoff_factor=backoff_factor,
            server_ip=server_ip,
            port=port,
            text=text,
            CORRECT_API_KEY=CORRECT_API_KEY,
            output_path=output_path,
            timeout_seconds=timeout_seconds
        )
    
    async def request_json_cfg(self, prompt_file_name: str, server_ip: str, port: str):
        try:
            payload = {"prompt_file_name": prompt_file_name}
            url = f"http://{server_ip}:{port}/config/json"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=60)) as response:
                    
                    # 先读取文本内容
                    text_response = await response.text()
                    
                    if response.status == 200:
                        try:
                            return await response.json()
                        except:
                            # 如果不是JSON，尝试手动解析
                            try:
                                return json.loads(text_response)
                            except:
                                return {"raw_response": text_response}
                    else:
                        return {"error": f"HTTP {response.status}", "response": text_response}
                        
        except Exception as e:
            return {"error": str(e)}

    async def request_wave_list(self, if_request: bool, server_ip: str, port):
        try:
            payload = {"if_request": if_request}
            url = f"http://{server_ip}:{port}/list/wav"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=60)) as response:
                    
                    # 先读取文本内容
                    text_response = await response.text()
                    
                    if response.status == 200:
                        try:
                            ret = ""
                            dict = await response.json()
                            wav_files = dict.get("wav_files")
                            count = dict.get("wav_count")
                            for t, wav_file in enumerate(wav_files):
                                ret += f"{t+1}.{wav_file}"
                                ret += "\n"
                            ret += f"共{count}个音频文件"

                            return ret
                        except:
                            # 如果不是JSON，尝试手动解析
                            try:
                                return json.loads(text_response)
                            except:
                                return {"raw_response": text_response}
                    else:
                        return {"error": f"HTTP {response.status}", "response": text_response}
                        
        except Exception as e:
            return {"error": str(e)}

class SubProcesControl():
    def __init__(self):
        self.child_process: Optional[Process] = None
        self.on_init = True

    def cleanup(self):
        """清理函数，用于在程序结束时删除锁文件"""
        if os.path.exists(lock_file_path):
            os.remove(lock_file_path)

    def child_process_function(self):
        from .service import run_service
        run_service()

    def start_child_process(self):

        """启动子进程的函数"""
        if os.path.exists(lock_file_path):
            if self.on_init == True:
                self.cleanup()
                self.on_init = False
                pass
            else:
                logger.error("Another instance of the child process is already running.")
                return None
        
        # 创建锁文件
        with open(lock_file_path, 'w') as f:
            f.write("Locked")
        
        # 创建并启动子进程
        p = Process(
            target=self.child_process_function,
            args=()
            )
        p.start()
        return p
    
    def terminate_child_process(self, child_process):
        """手动终止子进程"""
        if child_process and child_process.is_alive():
            child_process.terminate()
            child_process.join()
            self.cleanup()
            logger.info("Service.py process terminated.")

sbc = SubProcesControl()
rtac = RequestTTSandConfig()

@register("astrbot_plugin_tts_Cosyvoice2", "xiewoc ", "使用Cosyvoice2:0.5B对Astrbot的tts进行补充", "1.1.1", "https://github.com/xiewoc/astrbot_plugin_tts_Cosyvoice2")
class astrbot_plugin_tts_Cosyvoice2(Star):
    def __init__(self, context: Context,config: dict):
        super().__init__(context)

        self.config = config
        self.sub_config_misc = self.config.get('misc', {})
        self.sub_config_serve = self.config.get('serve_config', {})
        #读取设置

        self.reduce_parenthesis = self.config['if_reduce_parenthesis']

        self.server_ip = self.sub_config_serve.get('server_ip', '')
        
        self.generate_method = self.config['generate_method']
        self.instruct_speech_dialect = self.sub_config_misc.get('instruct_speech_dialect', '') 
        self.zero_shot_text = self.sub_config_misc.get('zero_shot_text', '')
        self.source_prompt = self.sub_config_misc.get('source_prompt', '')
        
        self.if_remove_think_tag = self.config['if_remove_think_tag']
        self.if_remove_emoji = self.config['if_remove_emoji']
        self.if_preload =  self.config['if_preload']
        self.if_trt = self.config['if_trt']
        self.if_fp16 = self.config['if_fp16']
        self.if_jit =  self.config['if_jit']
        self.if_seperate_serve = self.sub_config_serve.get('if_seperate_serve', '')
        
    async def initialize(self):
        if self.if_seperate_serve:#若为分布式部署
            pass
        else:
            try:
                sbc.child_process = sbc.start_child_process()
                if sbc.child_process:
                    logger.info(f"Sub process {sbc.child_process} run successfully")
            except Exception as e:
                raise e
        
        params = {
            "if_remove_think_tag": self.if_remove_think_tag,
            "if_remove_emoji": self.if_remove_emoji,
            "if_preload": self.if_preload,
            "if_trt": self.if_trt,
            "if_fp16": self.if_fp16,
            "if_jit": self.if_jit,
        }

        await rtac.post_config_with_session_auth(self.server_ip, rtac.port, self.source_prompt, self.zero_shot_text, self.instruct_speech_dialect, self.generate_method, self.server_ip, **params)

    async def terminate(self): 
        sbc.terminate_child_process(sbc.child_process)
        logger.info("已调用方法:Terminate,正在关闭")

    @filter.command_group("tts_cfg")
    def tts_cfg(self):
        pass

    @tts_cfg.group("set")
    def set(self):
        pass
    
    @set.command("voice")
    async def voice(self, event: AstrMessageEvent, prompt_file_name: str):

        ret = await rtac.request_json_cfg(prompt_file_name, self.server_ip, rtac.port)
        if ret == {}:
            await rtac.post_config_with_session_auth(self.server_ip, rtac.port, prompt_file_name, '', '普通话', 'instruct2', self.server_ip)
        else:
            #ret_list = [data.get('text'),data.get('form'),data.get('generate_method')]
            await rtac.post_config_with_session_auth(self.server_ip, rtac.port, prompt_file_name, str(ret["text"]), str(ret["form"]), str(ret["generate_method"]), self.server_ip)
        yield event.plain_result(f"音源更换成功: {prompt_file_name}")

    @set.command("dialect")
    async def dialect(self, event: AstrMessageEvent, dialect: str):
        await rtac.post_config_with_session_auth(self.server_ip, rtac.port, '' , '', dialect , 'instruct2', self.server_ip)
        yield event.plain_result(f"方言更换成功: {dialect}")

    @set.command("method")
    async def method(self, event: AstrMessageEvent, method: str):
        await rtac.post_config_with_session_auth(self.server_ip, rtac.port, '' ,'' , '', method, self.server_ip)
        yield event.plain_result(f"生成方式更换成功: {method}")

    @tts_cfg.command("list")
    async def list(self, event: AstrMessageEvent):
        opt = str(await rtac.request_wave_list(True, self.server_ip, rtac.port))
        yield event.plain_result(opt)
    
    @filter.on_llm_request()
    async def on_call_llm(self, event: AstrMessageEvent, req: ProviderRequest): # 请注意有三个参数
        global reduce_parenthesis
        if self.generate_method == "grained_control":
            req.system_prompt += """
                            请在生成的文本中，根据语境自然地插入以下情感和音效标签：
                            - **语气标签**：[sigh], [breath], [quick_breath]
                            - **笑声标签**：[laughter], <laughter>...</laughter>
                            - **动作音效**：[cough], [clucking], [lipsmack], [hissing]
                            - **语音特征**：[accent], [mn], [vocalized-noise]
                            - **特殊效果**：[noise], <strong>...</strong>

                            请确保标签的使用符合上下文，增强表现力而非堆砌。
                            """
        if self.reduce_parenthesis == True:
            req.system_prompt += "请在输出的字段中减少使用括号括起对动作,心情,表情等的描写，尽量只剩下口语部分"

    @filter.llm_tool(name="send_voice_msg") 
    async def send_voice_msg_cv(self, event: AstrMessageEvent, text: str, dialect: Optional[str] = None ) -> MessageEventResult:#这边optional了因为怕有的llm会看不懂
        '''发送语音消息。

        Args:
            text (string): 要转换为语音的文本。可嵌入情感与音效标签以增强表现力。支持的标签：呼吸类: [breath], [quick_breath], [sigh]；笑声类: [laughter], <laughter>...</laughter>；音效类: [cough], [clucking], [hissing], [lipsmack], [vocalized-noise], [mn], [noise]；特征类: [accent]；强调类: <strong>...</strong>。提示: 标签需按语境合理使用，避免过度堆砌。
        '''
        if text != '':
            if dialect != None:
                await rtac.post_config_with_session_auth(self.server_ip,rtac.port, '' , '', "普通话" ,'instruct2', self.server_ip)
            path = await rtac.post_generate_request_with_session_auth(
                self.server_ip,
                rtac.port,
                text,
                "1145141919810",
                output_path
            ) # 返回的是wav文件
            chain = [
                Record.fromFileSystem(path) # type: ignore
            ]
            yield event.chain_result(chain)