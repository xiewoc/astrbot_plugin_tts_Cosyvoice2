from astrbot.api.message_components import *
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.all import *
from astrbot.api.provider import ProviderRequest
import sys
import os
sys.path.append('./third_party/Matcha-TTS')
sys.path.insert(0, './third_party/Matcha-TTS')
from cosyvoice.cli.cosyvoice import CosyVoice2
from cosyvoice.utils.file_utils import load_wav
import onnxruntime
import torchaudio
from pydub import AudioSegment
import re

providers = ['CUDAExecutionProvider','AzureExecutionProvider', 'CPUExecutionProvider']
cosyvoice = CosyVoice2('pretrained_models/CosyVoice2-0.5B', load_jit=False, load_trt=True, fp16=True)

def cleanup_temp_files(directory):
    # 清理'instruct_数字_数字.wav'格式的临时文件
    for f in os.listdir(directory):
        if re.match(r'^instruct_\d+_\d+\.wav$', f):
            os.remove(os.path.join(directory, f))
    
    # 清理'merged_audio_数字.wav'格式的中间文件
    for f in os.listdir(directory):
        if re.match(r'^merged_audio_\d+\.wav$', f):
            os.remove(os.path.join(directory, f))

def merge_audio_files(input_filename_form,output_filename, directory):#r'^instruct_\d+\.wav$'
    
    combined = AudioSegment.empty()

    # 使用正则表达式过滤出匹配'instruct_数字.wav'模式的文件
    audio_files = [f for f in os.listdir(directory) if re.match(input_filename_form, f)]
    
    # 如果没有找到任何匹配的文件，则提示用户并退出
    if not audio_files:
        return
    
    # 按照数字部分对文件进行排序
    audio_files.sort(key=lambda x: int(re.search(r'\d+', x).group()))

    for file_name in audio_files:
        audio_path = os.path.join(directory, file_name)
        audio = AudioSegment.from_wav(audio_path)
        combined += audio  # 合并音频

    combined.export(output_filename, format="wav")


def TTS(text,prompt_speech_16k):
    text = text.replace('\n','').replace('\r','')
    result = re.split(r'[\n。]', text)
    for t, sp_sentences in enumerate(result):
        print(sp_sentences,'\n')
        if sp_sentences != '':
            for i, j in enumerate(cosyvoice.inference_instruct2(sp_sentences, '用普通话说这句话', prompt_speech_16k, stream=False)):
                filename = f"instruct_{t}_{i}.wav"  # 修改文件名以避免重复
                torchaudio.save(filename, j['tts_speech'], cosyvoice.sample_rate)

                # 仅在此处合并当前段落的所有音频片段到一个中间文件
                merge_audio_files(r'^instruct_%d_\d+\.wav$' % t, f"merged_audio_{t}.wav", './')
        else:
            pass
    # 所有句子处理完后，合并所有中间文件
    merge_audio_files(r'^merged_audio_\d+\.wav$', "merged_audio_final.wav", './')
    script_path = os.path.dirname(os.path.abspath(__file__))
    cleanup_temp_files(script_path)
    sound_path = script_path + "\\merged_audio_final.wav"
    return sound_path

prompt_speech_16k = load_wav('zero_shot_prompt_明.wav', 16000)

@register("astrbot_plugin_tts_Cosyvoice2", "xiewoc ", "extention in astrbot for tts using local Cosyvoice2-0.5b model", "0.0.1", "https://github.com/xiewoc/astrbot_plugin_tts_Cosyvoice2")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    '''防止“/t2s”被llm处理'''
    @filter.command("t2s")
    async def call_llm(self, event: AstrMessageEvent,prompt_from_user: str):
        func_tools_mgr = self.context.get_llm_tool_manager()
    
        # 获取用户当前与 LLM 的对话以获得上下文信息。
        curr_cid = await self.context.conversation_manager.get_curr_conversation_id(event.unified_msg_origin) # 当前用户所处对话的对话id，是一个 uuid。
        conversation = None # 对话对象
        context = [] # 上下文列表
        if curr_cid:
            conversation = await self.context.conversation_manager.get_conversation(event.unified_msg_origin, curr_cid)
            context = json.loads(conversation.history)
        else:
            curr_cid = await self.context.conversation_manager.new_conversation(event.unified_msg_origin)
        
        yield event.request_llm(
            prompt=prompt_from_user,
            func_tool_manager=func_tools_mgr,
            session_id=curr_cid, # 对话id。如果指定了对话id，将会记录对话到数据库
            contexts=context, # 列表。如果不为空，将会使用此上下文与 LLM 对话。
            system_prompt="",
            image_urls=[], # 图片链接，支持路径和网络链接
            conversation=conversation # 如果指定了对话，将会记录对话
            )
        
    '''在返回回应时'''
    @filter.command("t2s")
    @filter.on_decorating_result()
    async def on_decorating_result(self, event: AstrMessageEvent):
        result = event.get_result()
        chain = result.chain
        for component in chain:
            if isinstance(component, Plain):  
                plain_text = component.text
                print(plain_text)
        chain.append(Record.fromFileSystem(TTS(plain_text,prompt_speech_16k)))

    
