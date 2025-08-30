import sys
import os
import re
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import FastAPI, HTTPException, Request, status, Depends
from fastapi.responses import FileResponse
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Union, List
from pydantic import BaseModel, Field
from pathlib import Path
from io import BytesIO
import subprocess
import torchaudio
import torch
import logging
import uvicorn
import asyncio
import wave
import json
import glob

sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'CosyVoice','third_party','Matcha-TTS'))

sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'CosyVoice'))

from cosyvoice.cli.cosyvoice import CosyVoice2          # pyright: ignore[reportMissingImports]
from cosyvoice.utils.file_utils import load_wav         # pyright: ignore[reportMissingImports]

app = FastAPI()

class JsonReader():
    def __init__(self):
        pass

    @staticmethod
    async def load_json_config(file_name):# return text
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
        
    @staticmethod
    async def find_wav_and_json_files(directory):
        # 改变当前工作目录到指定目录
        os.chdir(directory)
        all_files = ''
        # 查找所有.wav文件
        wav_files = glob.glob('*.wav')
        
        for count , wav_file in enumerate(wav_files):
            all_files += wav_file + '\n'
        all_files += '共' + str(count + 1) + '个音源文件'#从0计数故加一
        return all_files
    
    @staticmethod
    async def ensure_directory_exists(path: Path) -> None:
        """Ensure a directory exists, creating it if necessary."""
        try:
            await asyncio.to_thread(os.makedirs, path, exist_ok=True)
        except OSError as e:
            raise RuntimeError(f"Failed to create directory {path}: {str(e)}")
        
class TextPreprocess():

    async def split_text(self,text) -> list[str]:
        if text == "":
            return []
        text = text.replace('\n','').replace('\r','')# 字符处理(换行)

        if self._is_all_chinese(text):
            result = re.split(r'[\n。]', text)#如果是全中文则以'。'断句
        else:
            result = re.split(r'(?<!\d)\.(?!\d)|[\n]', text)#其他语种则以'.'断句

        return result

    @staticmethod
    def _is_all_chinese(text):#判断是否全是中文
        # 使用正则表达式匹配中文字符
        pattern = re.compile(r'^[\u4e00-\u9fa5]+$')
        return bool(pattern.match(text))

    @staticmethod
    async def remove_thinktag(text) -> str:
        if text:
            cleaned_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
            return cleaned_text
        else:
            return ''
        
    @staticmethod
    async def remove_emoji(text) -> str:
        emoji_pattern = re.compile(
            "["
            # 表情符号
            "\U0001F600-\U0001F64F"  # Emoticons
            # 杂项符号和象形文字
            "\U0001F300-\U0001F5FF"  # Miscellaneous Symbols and Pictographs
            # 交通和地图符号
            "\U0001F680-\U0001F6FF"  # Transport and Map Symbols
            # 补充符号和象形文字
            "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
            # 符号和象形文字扩展-A
            "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
            # 杂项符号
            "\U00002600-\U000026FF"  # Miscellaneous Symbols
            # 丁巴特文符号（补充）
            "\U0001F000-\U0001F02F"  # Mahjong Tiles etc.
            "]+", 
            flags=re.UNICODE
        )
        return emoji_pattern.sub(r'', text)
    
class AudioProcess():
    
    @staticmethod
    def merge_audio_files_wave(audio_files: list, output_path = None):
        """使用wave模块合并WAV音频文件"""
        if not audio_files:
            logging.warning("No audio files to merge.")
            return None
        
        if len(audio_files) == 1:
            output_path = audio_files[0]
        
        # 读取第一个文件获取参数
        with wave.open(audio_files[0], 'rb') as first_wav:
            params = first_wav.getparams()
            sample_width = first_wav.getsampwidth()
            frame_rate = first_wav.getframerate()
            n_channels = first_wav.getnchannels()
            
            # 读取所有音频数据
            all_frames = first_wav.readframes(first_wav.getnframes())
        
        # 合并剩余文件
        for file_path in audio_files[1:]:
            if os.path.exists(file_path):
                try:
                    with wave.open(file_path, 'rb') as wav_file:
                        # 检查参数是否匹配
                        if (wav_file.getsampwidth() != sample_width or
                            wav_file.getframerate() != frame_rate or
                            wav_file.getnchannels() != n_channels):
                            logging.warning(f"Audio parameters mismatch in {file_path}, skipping.")
                            continue
                        
                        all_frames += wav_file.readframes(wav_file.getnframes())
                except Exception as e:
                    logging.error(f"Error reading {file_path}: {e}")
            else:
                logging.warning(f"Audio file {file_path} does not exist, skipping.")
        
        # 创建输出
        output_buffer = BytesIO()
        
        with wave.open(output_buffer, 'wb') as output_wav:
            output_wav.setparams(params)
            output_wav.writeframes(all_frames)
        
        output_buffer.seek(0)
        
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(output_buffer.getvalue())
            return output_path
        
    @staticmethod
    def merge_audio_files_torchaudio(audio_files: list, output_path = None):
        """使用torchaudio合并音频文件"""
        if not audio_files:
            return None
        
        if len(audio_files) == 1:
            return audio_files[0]
        
        # 读取所有音频
        waveforms = []
        sample_rates = []
        
        for file_path in audio_files:
            try:
                waveform, sample_rate = torchaudio.load(file_path)
                waveforms.append(waveform)
                sample_rates.append(sample_rate)
            except Exception as e:
                logging.error(f"Error loading {file_path}: {e}")
        
        # 检查采样率是否一致
        if len(set(sample_rates)) > 1:
            logging.warning("Sample rates differ, resampling might be needed")
            # 这里可以添加重采样逻辑
        
        # 合并波形
        merged_waveform = torch.cat(waveforms, dim=1)
        
        # 保存结果
        if output_path:
            torchaudio.save(output_path, merged_waveform, sample_rates[0])
            return output_path
        else:
            # 返回内存中的音频数据
            buffer = BytesIO()
            torchaudio.save(buffer, merged_waveform, sample_rates[0], format='wav')
            buffer.seek(0)
            return buffer
        
class RepoDownload():

    async def download_repo(self) -> None:
        repo_url = "https://github.com/FunAudioLLM/CosyVoice.git"
        repo_dir = Path(__file__).parent / 'CosyVoice'
        try:
            if repo_dir.exists():
                logging.info("Cosyvoice Github Repo found, skipping download.")
                return
                
            repo_dir.mkdir(parents=True, exist_ok=True)
            
            if not await self._is_git_available():
                raise RuntimeError("Git is not installed or not in PATH")
            
            logging.info("Downloading Cosyvoice Github Repo...")
            
            await self._run_command(
                ["git", "clone", "--recursive", repo_url, str(repo_dir)],
                timeout=600
            )
            
            logging.info("Successfully downloaded Cosyvoice Github Repo")
            
        except asyncio.TimeoutError:
            logging.error("Git clone operation timed out")
            raise
        except Exception as e:
            logging.error(f"Failed to download repository: {str(e)}")
            if repo_dir.exists():
                try:
                    await self._run_command(f"rm -rf {repo_dir}")
                except:
                    pass
            raise

    async def _is_git_available(self) -> bool:
        """检查系统是否安装了git"""
        try:
            await self._run_command(["git", "--version"], timeout=5)
            return True
        except:
            return False

    async def _run_command(self, command: Union[str, List[str]], timeout: Optional[float] = None) -> str:
        """异步执行命令并返回输出"""
        import shlex
        
        # 确定使用哪种方式执行
        if isinstance(command, str):
            # 字符串命令，使用 shell=False 的安全方式
            args = shlex.split(command)
            use_shell = False
            command_for_error = command
        else:
            # 已经是参数列表
            args = command
            use_shell = False
            command_for_error = ' '.join(shlex.quote(arg) for arg in command)
        
        if use_shell:
            # 只有在绝对必要时才使用 shell=True
            if isinstance(command, str):
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True
                )
            else:
                raise ValueError("Command must be a string when using shell=True")
        else:
            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True
            )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            if process.returncode != 0 and process.returncode is not None:
                error_msg = stderr.decode().strip()
                logging.error(f"Command failed with error: {error_msg}")
                raise subprocess.CalledProcessError(
                    process.returncode, 
                    command_for_error,  # 用于错误信息的命令字符串
                    stdout, 
                    stderr
                )
                
            return stdout.decode().strip()
            
        except asyncio.TimeoutError:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
            raise
        except Exception as e:
            if process.returncode is None:
                process.kill()
                await process.wait()
            raise
    
class TTSGenCosyvoice2():
    def __init__(self):

        self.prompt_speech_name = ''
        self.prompt_speech_dialect = ''
        self.prompt_zero_shot_text = ''
        self.generate_method = ''

        self.base_dir = Path(__file__).parent.resolve()
        self.model_dir = str(self.base_dir / 'pretrained_models' / 'CosyVoice2-0.5B')
        self.temp_dir = str(self.base_dir / 'temp')
        self.prompt_speech_path = ""
        self.model_repo = 'iic/CosyVoice2-0.5B'

        self.if_preload = False
        self.if_remove_think_tag = False
        self.if_remove_emoji = False

        self.if_jit = False
        self.if_fp16 = False
        self.if_trt = False

        self.on_init = True
        self.model_cosyvoice2 = None
        self.thread_pool: ThreadPoolExecutor
    
    async def Download_model(self,model_dir: Path, model_repo: str) -> None:
        # Download model if it doesn't exist
        if not model_dir.exists():
            from modelscope import snapshot_download
            await self._ensure_directory_exists(model_dir.parent)

            loop = asyncio.get_event_loop()

            self.model =  await loop.run_in_executor(
                    self.thread_pool, 
                    lambda: snapshot_download(model_repo,local_dir=str(model_dir))
                )

    async def _ensure_directory_exists(self,path: Path) -> None:
        """Ensure a directory exists, creating it if necessary."""
        try:
            await asyncio.to_thread(os.makedirs, path, exist_ok=True)
        except OSError as e:
            raise RuntimeError(f"Failed to create directory {path}: {str(e)}")
        
    async def load_model(self,if_jit: bool ,if_trt: bool ,if_fp16: bool):
        if self.on_init:
            loop = asyncio.get_event_loop()
            try:
                self.model_cosyvoice2 = await loop.run_in_executor(
                        self.thread_pool, 
                        lambda: CosyVoice2(self.model_dir, load_jit=if_jit, load_trt=if_trt, fp16=if_fp16)
                    )
                
                self.on_init = False

            except Exception as e:
                raise

    def TTS_Cosyvoice2(self, texts: list, prompt_speech_path: str, speech_form: str, generate_mode: str, zero_shot_text: str) -> str:

        if prompt_speech_path == "" or None:
            raise FileNotFoundError()
        
        prompt_speech_16k = load_wav(prompt_speech_path, 16000)# 加载音频文件，码率变为16KHz
        
        file_names = []
        
        if speech_form != "" and not None:
            speech_form = f"用{speech_form}说这句话"
        else:
            raise Exception
        
        if zero_shot_text == "" or None:
            logging.error("Zero Shot text con not be void")
            raise Exception

        for t, sp_sentences in enumerate(texts):
            if sp_sentences != '' and self.model_cosyvoice2 is not None:
                # max tokens ~= 80
                if generate_mode == 'zero_shot':
                    for i, j in enumerate(self.model_cosyvoice2.inference_zero_shot(sp_sentences, zero_shot_text, prompt_speech_16k, stream=False)):
                        filename = f'opt_{t}_{i}.wav'  # 修改文件名以避免重复
                        torchaudio.save(os.path.join(self.temp_dir,filename), j['tts_speech'], self.model_cosyvoice2.sample_rate)

                elif generate_mode == 'grained_control':
                    # fine grained control, for supported control, check cosyvoice/tokenizer/tokenizer.py#L248
                    for i, j in enumerate(self.model_cosyvoice2.inference_cross_lingual(sp_sentences, prompt_speech_16k, stream=False)):
                        filename = f'opt_{t}_{i}.wav'
                        torchaudio.save(os.path.join(self.temp_dir,filename), j['tts_speech'], self.model_cosyvoice2.sample_rate)

                elif generate_mode == 'instruct2':
                    for i, j in enumerate(self.model_cosyvoice2.inference_instruct2(sp_sentences, speech_form, prompt_speech_16k, stream=False)):
                        filename = f'opt_{t}_{i}.wav'  # 修改文件名以避免重复
                        torchaudio.save(os.path.join(self.temp_dir,filename), j['tts_speech'], self.model_cosyvoice2.sample_rate)

                else: #default in instruct mode
                    for i, j in enumerate(self.model_cosyvoice2.inference_instruct2(sp_sentences, speech_form, prompt_speech_16k, stream=False)):
                        filename = f'opt_{t}_{i}.wav'  # 修改文件名以避免重复
                        torchaudio.save(os.path.join(self.temp_dir,filename), j['tts_speech'], self.model_cosyvoice2.sample_rate)
                
            else:
                logging.error("Seperated text is void skipping generation.")
                continue
            
            file_names.append(os.path.join(self.temp_dir, filename))
            
        opt_path = os.path.join(self.temp_dir, 'output.wav')

        wav_path = AudioProcess.merge_audio_files_torchaudio(file_names, opt_path)
        
        return str(wav_path)

CORRECT_API_KEY = 1145141919810

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
        """验证API密钥"""
        if credentials.scheme != "Bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme"
            )
        if credentials.credentials != CORRECT_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        return credentials.credentials

port = 5050

json_reader = JsonReader()
text_preprocess = TextPreprocess()
tts_gen_cosyvoice2 = TTSGenCosyvoice2()
repo_download = RepoDownload()

class SpeechRequest(BaseModel):
    model: str
    input: str
    voice: str

class ConfigRequest(BaseModel):#when change configs
    speech_dialect: str = Field(..., description="语种/方言")
    prompt_text: str = Field(..., description="Zero Shot文字")
    speech_name: str = Field(..., description="原语音名称")
    generate_method: str = Field(..., description="生成模式")

    if_jit: bool = Field(False, description="是否使用即时编译")
    if_fp16: bool = Field(False, description="是否使用bf16精度")
    if_trt: bool = Field(False, description="是否使用TensorRT")
    if_preload: bool = Field(False, description="是否预加载模型")
    if_remove_think_tag: bool = Field(False, description="是否移除思考标签")
    if_remove_emoji: bool = Field(False, description="是否移除emoji")

class LoadJsonRequest(BaseModel):
    prompt_file_name:str

class WaveFileListRequest(BaseModel):
    if_request: bool

def run_service():
    uvicorn.run(app, host="0.0.0.0", port=port)

@app.on_event("startup")
async def startup_event():
    print("TTS CosyVoice2 service is starting...")
    try:
        await repo_download.download_repo()  # 确保在服务启动前下载仓库
    except Exception as e:
        logging.error(f"Failed to download repository: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to download repository")
    # 在服务类或模块级别创建线程池
    tts_gen_cosyvoice2.thread_pool = ThreadPoolExecutor(max_workers=4)  # 根据你的服务器配置调整worker数量

@app.on_event("shutdown")
async def shut_down():
    tts_gen_cosyvoice2.thread_pool.shutdown(wait=True)
    
@app.post("/audio/speech")
async def generate_speech(request: Request, speech_request: SpeechRequest):
    
    if speech_request.input == "" or speech_request.input is None:
        raise HTTPException(status_code=500, detail="Input text is void, please check your client")
    
    text = await text_preprocess.remove_thinktag(speech_request.input) if tts_gen_cosyvoice2.if_remove_think_tag else speech_request.input

    text = await text_preprocess.remove_emoji(text) if tts_gen_cosyvoice2.if_remove_emoji else text

    texts = await text_preprocess.split_text(text) if len(text) > 80 else [text]

    if tts_gen_cosyvoice2.model_cosyvoice2 == None and tts_gen_cosyvoice2.if_preload == False:
        await tts_gen_cosyvoice2.load_model(
            tts_gen_cosyvoice2.if_jit,
            tts_gen_cosyvoice2.if_trt,
            tts_gen_cosyvoice2.if_fp16
        )

    try: 
        loop = asyncio.get_event_loop()

        wav_path = str(
            await loop.run_in_executor(
                    tts_gen_cosyvoice2.thread_pool, 
                    lambda: tts_gen_cosyvoice2.TTS_Cosyvoice2(
                                    texts,
                                    tts_gen_cosyvoice2.prompt_speech_path,
                                    tts_gen_cosyvoice2.prompt_speech_dialect,
                                    tts_gen_cosyvoice2.generate_method,
                                    tts_gen_cosyvoice2.prompt_zero_shot_text
                                        )
                )
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    if not wav_path or not os.path.exists(wav_path) or not os.access(wav_path, os.R_OK):
        raise HTTPException(status_code=500, detail="Failed to generate speech")
    # 使用FileResponse返回生成的语音文件
    return FileResponse(path=wav_path, media_type='audio/wav', filename="output.wav")

@app.post("/config")
async def set_config(request: Request, config_request: ConfigRequest):

    tts_gen_cosyvoice2.if_preload = config_request.if_preload if config_request.if_preload == True else False
    tts_gen_cosyvoice2.if_remove_emoji = config_request.if_remove_emoji if config_request.if_remove_emoji == True else False
    tts_gen_cosyvoice2.if_remove_think_tag = config_request.if_remove_think_tag if config_request.if_remove_think_tag == True else False

    if config_request.speech_name != "" and not None:
        tts_gen_cosyvoice2.prompt_speech_name = config_request.speech_name
        tts_gen_cosyvoice2.prompt_speech_path = str(tts_gen_cosyvoice2.base_dir / "sounds" / tts_gen_cosyvoice2.prompt_speech_name)

    if config_request.speech_dialect != "" and not None:
        tts_gen_cosyvoice2.prompt_speech_dialect = config_request.speech_dialect

    if config_request.prompt_text != "" and not None:
        tts_gen_cosyvoice2.prompt_zero_shot_text = config_request.prompt_text 
        
    if config_request.generate_method != "" and not None:
        tts_gen_cosyvoice2.generate_method = config_request.generate_method 

    tts_gen_cosyvoice2.if_fp16 = config_request.if_fp16 if config_request.if_fp16 == True else False
    tts_gen_cosyvoice2.if_jit = config_request.if_jit if config_request.if_jit == True else False
    tts_gen_cosyvoice2.if_trt = config_request.if_trt if config_request.if_trt == True else False

    print(f"tts_gen_cosyvoice2.if_preload: {tts_gen_cosyvoice2.if_preload} \n",
          f"tts_gen_cosyvoice2.if_remove_emoji: {tts_gen_cosyvoice2.if_remove_emoji}",
          f"tts_gen_cosyvoice2.if_remove_think_tag: {tts_gen_cosyvoice2.if_remove_think_tag}",
          f"config_request.speech_dialect: {config_request.speech_dialect}",
          f"config_request.speech_name: {config_request.speech_name}",
          f"config_request.prompt_text: {config_request.prompt_text}"
          )

@app.post("/config/json")
async def get_config(request: Request, json_request: LoadJsonRequest):
    ret = json_reader.load_json_config(json_request.prompt_file_name)
    return ret
    
@app.post("/list/wav")
async def get_wav_list(request: Request, wav_request: WaveFileListRequest):
    if wav_request.if_request:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'sounds')
        ret = json_reader.find_wav_and_json_files(path)
        return ret
    else:
        return ""

if __name__ == "__main__":
    logging.warning("This is a model ,you can't run this seperately.")