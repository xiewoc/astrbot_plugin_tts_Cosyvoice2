import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import re
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from fastapi.responses import FileResponse
import uvicorn

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

def run_service():
    uvicorn.run(app, host="127.0.0.1", port=5050)
    
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

@app.post("/config")
async def generate_speech(request: Request, config_request: ConfigRequest):
    
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
async def generate_speech(request: Request, config_init_request: ConfigInitRequest):
    
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

if __name__ == "__main__":
    print("This is a model ,you can't run this seperately.")