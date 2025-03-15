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
global remove_think_tag ,instruct_speech_form ,zero_shot_text ,generate_method ,trt ,fp16 ,source_prompt_file
global prompt_speech_16k_name ,prompt_speech_form ,prompt_zero_shot_text#较为恒定的变量
prompt_speech_16k_name = ''
prompt_speech_form = ''
prompt_zero_shot_text = ''

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
    speech_form:str
    prompt_text: str
    voice: str

def run_service(if_remove_think_tag,inpt_instruct_speech_form ,inpt_zero_shot_text ,inpt_generate_method ,if_trt ,if_fp16 ,source_prompt):
    global remove_think_tag ,instruct_speech_form ,zero_shot_text ,generate_method ,trt ,fp16 ,source_prompt_file
    
    remove_think_tag = if_remove_think_tag
    instruct_speech_form = inpt_instruct_speech_form
    zero_shot_text = inpt_zero_shot_text
    generate_method = inpt_generate_method
    trt = if_trt
    fp16 = if_fp16
    source_prompt_file = source_prompt
    
    uvicorn.run(app, host="127.0.0.1", port=5050)
    
@app.post("/audio/speech")
async def generate_speech(request: Request, speech_request: SpeechRequest):
    global remove_think_tag ,instruct_speech_form ,zero_shot_text ,generate_method ,trt ,fp16 ,source_prompt_file
    
    # 验证 Authorization 头是否包含正确的 Bearer token
    auth_header = request.headers.get('authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    script_path = os.path.dirname(os.path.abspath(__file__))

    #源文件名称
    global prompt_speech_16k_name
    if prompt_speech_16k_name == '':
        prompt_speech_16k_name = source_prompt_file
    else:
        prompt_speech_16k_name = prompt_speech_16k_name

    #语种
    global prompt_speech_form
    if prompt_speech_form == '':
        speech_form = instruct_speech_form
    else:
        speech_form = prompt_speech_form
    speech_form = '用' + speech_form + '说这句话'

    #zero_shot文字
    global prompt_zero_shot_text
    if prompt_zero_shot_text == '':
        zero_shot_text = zero_shot_text
    else:
        zero_shot_text = prompt_zero_shot_text

    print("config:","form:",speech_form,"zeroshot text:",zero_shot_text,"source file:",prompt_speech_16k_name,'\n')
    import tts_tofile as ts
    try:
        if remove_think_tag == True:
            input_text = remove_thinktag(speech_request.input)
        else:
            input_text = speech_request.input

        if input_text != '':
            sound_path = ts.wav2mp3(
                ts.TTS(
                    input_text,
                    prompt_speech_16k_name,
                    speech_form,
                    script_path,
                    generate_method,
                    zero_shot_text,
                    trt,
                    fp16
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
        speech_form:str
        prompt_text: str
        voice: str
    '''
    global prompt_speech_16k_name ,prompt_speech_form ,prompt_zero_shot_text
    
    if config_request.speech_form:
        prompt_speech_form = config_request.speech_form
    if config_request.prompt_text:
        prompt_zero_shot_text = config_request.prompt_text
    if config_request.voice:
        prompt_speech_16k_name = config_request.voice
    print("updated config:","form:",prompt_speech_form,"zeroshot text:",prompt_zero_shot_text,"source file:",prompt_speech_16k_name,'\n')

    
if __name__ == "__main__":
    print("This is a model ,you can't run this seperately.")
