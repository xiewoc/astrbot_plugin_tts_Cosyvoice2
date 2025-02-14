import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),'third_party\\Matcha-TTS'))
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'third_party\\Matcha-TTS'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from cosyvoice.cli.cosyvoice import CosyVoice2
from cosyvoice.utils.file_utils import load_wav
from pydub import AudioSegment
import onnxruntime
import torchaudio
import re
import logging
from modelscope.utils.logger import get_logger

logger = get_logger()
logger.setLevel(logging.ERROR)
providers = ['CUDAExecutionProvider','AzureExecutionProvider', 'CPUExecutionProvider']
cosyvoice = CosyVoice2(os.path.join(os.path.dirname(os.path.abspath(__file__)),'pretrained_models/CosyVoice2-0.5B'), load_jit=False, load_trt=False, fp16=True)

def wav2mp3(wav_path,script_path):
    audio = AudioSegment.from_wav(wav_path)
    audio.export(os.path.join(script_path, "output.mp3"), format="mp3")
    mp3_path = os.path.join(script_path, "output.mp3")
    return mp3_path

def cleanup_temp_files(directory):
    # 清理'instruct_数字_数字.wav'格式的临时文件
    for f in os.listdir(directory):
        if re.match(r'^instruct_\d+_\d+\.wav$', f):
            os.remove(os.path.join(directory, f))
    
    # 清理'merged_audio_数字.wav'格式的中间文件
    for f in os.listdir(directory):
        if re.match(r'^merged_audio_\d+\.wav$', f):
            os.remove(os.path.join(directory, f))

def merge_audio_files(input_filename_form,output_filename, directory):
    
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

    combined.export(os.path.join(directory,output_filename), format="wav")


def TTS(text,prompt_speech_16k,speech_form,script_path):
    text = text.replace('\n','').replace('\r','')
    result = re.split(r'[\n。]', text)
    for t, sp_sentences in enumerate(result):
        if sp_sentences != '':
            for i, j in enumerate(cosyvoice.inference_instruct2(sp_sentences, speech_form, prompt_speech_16k, stream=False)):
                filename = f"instruct_{t}_{i}.wav"  # 修改文件名以避免重复
                torchaudio.save(os.path.join(script_path,filename), j['tts_speech'], cosyvoice.sample_rate)
                # 仅在此处合并当前段落的所有音频片段到一个中间文件
                merge_audio_files(r'^instruct_%d_\d+\.wav$' % t, f"merged_audio_{t}.wav",script_path)
        else:
            pass
    # 所有句子处理完后，合并所有中间文件
    merge_audio_files(r'^merged_audio_\d+\.wav$', "merged_audio_final.wav",script_path)
    cleanup_temp_files(script_path)
    sound_path = os.path.join(script_path, "merged_audio_final.wav")
    return sound_path

if __name__ == "__main__":
    print("This is a model ,you can't run this seperately.")
