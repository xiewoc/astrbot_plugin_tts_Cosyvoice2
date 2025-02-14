# astrbot_plugin_tts_Cosyvoice2

Astrbot的tts功能补充（使用Cosyvoice2-0.5b本地模型）

# 环境准备

将[Cosyvoice官方文档](https://www.modelscope.cn/models/iic/CosyVoice2-0.5B/summary)中的操作做一遍，检查是否有遗漏的库（详见backup_py310.yaml与req.txt）

记得将Cosyvoice的项目文件clone到插件文件夹下 (只下载Cosyvoice2 0.5b模型便可)  

eg.E:\AstrBot\data\plugins\astrbot_plugin_tts_Cosyvoice2

# 使用

与官方tts方法一致，配置时用openai_tts_api即可，api填入127.0.0.1:5050，其余随意

'zero_shot_prompt_明.wav'为音色模仿源，需要16kHz的wav文件，文件源名称在'service.py'中可以更改

切记路径都是在插件目录下！

eg. /tts 传入llm的内容
