import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import re
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from fastapi.responses import FileResponse
import uvicorn
import logging

logging.getLogger().setLevel(logging.ERROR)
app = FastAPI()
global remove_think_tag

def remove_thinktag(text):
    cleaned_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return cleaned_text

class SpeechRequest(BaseModel):
    model: str
    input: str
    voice: str

def run_service(if_remove_think_tag,if_preload):
    global remove_think_tag
    remove_think_tag = if_remove_think_tag
    if if_preload == True:
        import tts_tofile as ts
    #print(if_remove_think_tag,"when service.py recieve if_remove_think_tag")
    #print(if_preload,"when service.py recieve if_preload")
    uvicorn.run(app, host="127.0.0.1", port=5050)
    
@app.post("/audio/speech")
async def generate_speech(request: Request, speech_request: SpeechRequest):
    global remove_think_tag
    # 验证 Authorization 头是否包含正确的 Bearer token
    auth_header = request.headers.get('authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Unauthorized")
    script_path = os.path.dirname(os.path.abspath(__file__))

    prompt_speech_16k_name = speech_request.voice #"zero_shot_prompt_明.wav"
    print("using",prompt_speech_16k_name,"as tts source file")
    speech_form = '用普通话说这句话'
    
    import tts_tofile as ts
    try:
        if remove_think_tag == True:
            input_text = remove_thinktag(speech_request.input)
            #print(remove_think_tag,"when generate_speech function recieve remove_think_tag")
        else:
            input_text = speech_request.input
        sound_path = ts.wav2mp3(ts.TTS(input_text,prompt_speech_16k_name,speech_form,script_path),script_path)
        
        if not sound_path or not os.path.exists(sound_path) or not os.access(sound_path, os.R_OK):
            logging.error(f"Invalid sound path: {sound_path}")
            raise HTTPException(status_code=500, detail="Failed to generate speech")
    except Exception as e:
        logging.exception("An error occurred during speech generation.")
        raise HTTPException(status_code=500, detail=str(e))
    # 使用FileResponse返回生成的语音文件
    return FileResponse(path=sound_path, media_type='audio/mp3', filename="output.mp3")

    
if __name__ == "__main__":
    print("This is a model ,you can't run this seperately.")
