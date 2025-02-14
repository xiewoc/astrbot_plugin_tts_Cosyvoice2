import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import re
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from fastapi.responses import FileResponse
import uvicorn

from tts_tofile import *

app = FastAPI()

class SpeechRequest(BaseModel):
    model: str
    input: str
    voice: str

@app.post("/audio/speech")
async def generate_speech(request: Request, speech_request: SpeechRequest):
    # 验证 Authorization 头是否包含正确的 Bearer token
    auth_header = request.headers.get('authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Unauthorized")
    script_path = os.path.dirname(os.path.abspath(__file__))
    prompt_speech_16k = load_wav(os.path.join(script_path,"zero_shot_prompt_明.wav"), 16000)
    speech_form = '用普通话说这句话'

    sound_path = wav2mp3(TTS(speech_request.input,prompt_speech_16k,speech_form,script_path),script_path)
        
    if not sound_path:
        raise HTTPException(status_code=500, detail="Failed to generate speech")

    # 使用FileResponse返回生成的语音文件
    return FileResponse(path=sound_path, media_type='audio/mp3', filename="output.mp3")

def run_service():
    uvicorn.run(app, host="127.0.0.1", port=5050)
    
if __name__ == "__main__":
    print("This is a model ,you can't run this seperately.")
