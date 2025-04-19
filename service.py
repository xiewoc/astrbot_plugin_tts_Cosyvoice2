import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import re
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from fastapi.responses import FileResponse
import uvicorn
import json
import glob

app = FastAPI()

global prompt_speech_name ,prompt_speech_dialect ,prompt_zero_shot_text ,generate_method ,if_jit ,if_fp16 ,if_trt 
#后续传参的变量

global prompt_speech_name_init ,prompt_speech_dialect_init ,prompt_zero_shot_text_init ,generate_method_init ,if_jit_init ,if_fp16_init ,if_trt_init ,if_remove_think_tag_init 
#初次设定参数的变量(init)

prompt_speech_16k_name = ''
prompt_speech_form = ''
prompt_zero_shot_text = ''
if_remove_think_tag_init = False
if_jit = False
if_trt = False
if_fp16 = False

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

def find_wav_and_json_files(directory):
    # 改变当前工作目录到指定目录
    os.chdir(directory)
    all_files = ''
    # 查找所有.wav文件
    wav_files = glob.glob('*.wav')
    
    for count , wav_file in enumerate(wav_files):
        all_files += wav_file + '\n'
    all_files += '共' + str(count + 1) + '个音源文件'#从0计数故加一
    return all_files

def remove_thinktag(text):
    if text:
        cleaned_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        return cleaned_text
    else:
        return ''

class SpeechRequest(BaseModel):
    model: str
    input: str
    voice: str

class ConfigRequest(BaseModel):#when change configs
    speech_dialect: str
    prompt_text: str
    voice: str
    generate_method: str

class ConfigInitRequest(BaseModel):#when set initial configs
    speech_dialect: str
    prompt_text: str
    voice: str
    generate_method: str
    if_jit: bool
    if_fp16: bool
    if_trt: bool
    if_preload: bool
    if_remove_think_tag: bool

class LoadJsonRequest(BaseModel):
    prompt_file_name:str

class WaveFileListRequest(BaseModel):
    if_request: bool

def run_service():
    uvicorn.run(app, host="0.0.0.0", port=5050)
    
@app.post("/audio/speech")
async def generate_speech(request: Request, speech_request: SpeechRequest):
    
    script_path = os.path.dirname(os.path.abspath(__file__))

    #源文件名称
    global prompt_speech_name

    #语种（方言）
    global prompt_speech_dialect
    speech_dialect = '用' + prompt_speech_dialect + '说这句话'

    #zero_shot文字
    global prompt_zero_shot_text
    
    global if_jit ,if_fp16 ,if_trt ,generate_method
    global if_remove_think_tag_init

    print("config:","dialect:",prompt_speech_dialect,"zeroshot text:",prompt_zero_shot_text,"source file:",prompt_speech_name,'\n')

    import tts_tofile as ts
    try:
        global if_remove_think_tag_init
        if if_remove_think_tag_init == True:
            input_text = remove_thinktag(speech_request.input)
        else:
            input_text = speech_request.input

        if input_text != '':
            sound_path = ts.wav2mp3(
                await ts.TTS(
                    input_text,
                    prompt_speech_name,
                    speech_dialect,
                    script_path,
                    generate_method,
                    prompt_zero_shot_text,
                    if_jit,
                    if_trt,
                    if_fp16
                    ),
                script_path
                )
        else:
            return ''
        
        if not sound_path or not os.path.exists(sound_path) or not os.access(sound_path, os.R_OK):
            raise HTTPException(status_code=500, detail="Failed to generate speech")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    # 使用FileResponse返回生成的语音文件
    return FileResponse(path=sound_path, media_type='audio/mp3', filename="output.mp3")

@app.post("/audio/speech/wav")
async def generate_speech(request: Request, speech_request: SpeechRequest):
    
    script_path = os.path.dirname(os.path.abspath(__file__))

    #源文件名称
    global prompt_speech_name

    #语种（方言）
    global prompt_speech_dialect
    speech_dialect = '用' + prompt_speech_dialect + '说这句话'

    #zero_shot文字
    global prompt_zero_shot_text
    
    global if_jit ,if_fp16 ,if_trt ,generate_method
    global if_remove_think_tag_init

    print("config:","dialect:",prompt_speech_dialect,"zeroshot text:",prompt_zero_shot_text,"source file:",prompt_speech_name,'\n')

    import tts_tofile as ts
    try:
        global if_remove_think_tag_init
        if if_remove_think_tag_init == True:
            input_text = remove_thinktag(speech_request.input)
        else:
            input_text = speech_request.input

        if input_text != '':
            sound_path = await ts.TTS(
                    input_text,
                    prompt_speech_name,
                    speech_dialect,
                    script_path,
                    generate_method,
                    prompt_zero_shot_text,
                    if_jit,
                    if_trt,
                    if_fp16
                    )
        else:
            return ''
        
        if not sound_path or not os.path.exists(sound_path) or not os.access(sound_path, os.R_OK):
            raise HTTPException(status_code=500, detail="Failed to generate speech")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    # 使用FileResponse返回生成的语音文件
    return FileResponse(path=sound_path, media_type='audio/wav', filename="merged_audio_final.wav")

@app.post("/config")
async def set_config(request: Request, config_request: ConfigRequest):
    
    '''
    class ConfigRequest(BaseModel):#when change configs
            speech_dialect: str
            prompt_text: str
            voice: str
            generate_method: str
    '''
    global prompt_speech_name ,prompt_speech_dialect ,prompt_zero_shot_text ,generate_method
    
    if config_request.speech_dialect:
        prompt_speech_dialect = config_request.speech_dialect

    if config_request.prompt_text:
        prompt_zero_shot_text = config_request.prompt_text

    if config_request.voice:
        prompt_speech_name = config_request.voice

    if config_request.generate_method:
        generate_method = config_request.generate_method

    print("updated config:","dialect:",prompt_speech_dialect,"zeroshot text:",prompt_zero_shot_text,"source file:",prompt_speech_name,"method:",generate_method,'\n')

@app.post("/config/init")
async def set_init_config(request: Request, config_init_request: ConfigInitRequest):
    
    '''
    class ConfigInitRequest(BaseModel):#when set initial configs
    speech_dialect: str
    prompt_text: str
    voice: str
    generate_method: str
    if_jit: bool
    if_fp16: bool
    if_trt: bool
    if_preload: bool
    if_remove_think_tag: bool

    '''
    global prompt_speech_name_init ,prompt_speech_dialect_init ,prompt_zero_shot_text_init ,generate_method_init ,if_jit_init ,if_fp16_init ,if_trt_init ,if_remove_think_tag_init 
    
    global prompt_speech_name ,prompt_speech_dialect ,prompt_zero_shot_text ,generate_method ,if_jit ,if_fp16 ,if_trt 

    if config_init_request.voice:#仿制音源
        prompt_speech_name_init = config_init_request.voice
        prompt_speech_name = prompt_speech_name_init
    
    if config_init_request.speech_dialect:#方言
        prompt_speech_dialect_init = config_init_request.speech_dialect
        prompt_speech_dialect = prompt_speech_dialect_init

    if config_init_request.prompt_text:#zeroshot
        prompt_zero_shot_text_init = config_init_request.prompt_text
        prompt_zero_shot_text = prompt_zero_shot_text_init
    
    if config_init_request.generate_method:#zeroshot
        generate_method_init = config_init_request.generate_method
        generate_method = generate_method_init

    if config_init_request.if_jit:#jit
        if_jit_init = config_init_request.if_jit
        if_jit = if_jit_init

    if config_init_request.if_fp16:#fp16
        if_fp16_init = config_init_request.if_fp16
        if_fp16 = if_fp16_init

    if config_init_request.if_trt:#trt
        if_trt_init = config_init_request.if_trt
        if_trt = if_trt_init

    if config_init_request.if_preload:#preload
        import tts_tofile as ts
        ts.preload(config_init_request.if_jit,
                   config_init_request.if_trt,
                   config_init_request.if_fp16
                   )
        
    if config_init_request.if_remove_think_tag:#remove think tag
        if_remove_think_tag_init  = config_init_request.if_remove_think_tag

    print("init config:" ,"\n" ,"form:",prompt_speech_dialect ,"\n" ,"zeroshot text:",prompt_zero_shot_text ,"\n" ,"source file:", prompt_speech_name ,"\n" ,"method:" ,generate_method ,"\n" ,"remove_think_tag:" ,if_remove_think_tag_init ,"\t")

@app.post("/config/json")
async def set_init_config(request: Request, json_request: LoadJsonRequest):
    ret = load_json_config(json_request.prompt_file_name)
    return ret
    
@app.post("/list/wav")
async def set_init_config(request: Request, wav_request: WaveFileListRequest):
    if wav_request.if_request:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'sounds')
        ret = find_wav_and_json_files(path)
        return ret
    else:
        return ""

if __name__ == "__main__":
    print("This is a model ,you can't run this seperately.")