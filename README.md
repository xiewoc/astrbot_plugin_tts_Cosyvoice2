# astrbot_plugin_tts_Cosyvoice2

Astrbot的tts功能补充（使用Cosyvoice2-0.5b本地模型）

# 配置

需要ffmpeg在系统路径下

将[Cosyvoice官方文档](https://www.modelscope.cn/models/iic/CosyVoice2-0.5B/summary)中的操作做一遍，检查是否有遗漏的库未安装

使用以下命令在shell安装所需库

    pip  install -r requirements.txt

与官方tts方法一致，配置时用openai_tts_api，api填入127.0.0.1:5050，voice填入原声音文件(默认：zero_shot_prompt_明.wav)，超时建议在60左右，key随意

# 使用

eg. 

    /tts


# 新内容

for 1.0.4

添加提示词选项，将string类型的schema改为bool类型的