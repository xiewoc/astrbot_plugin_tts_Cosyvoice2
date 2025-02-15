# astrbot_plugin_tts_Cosyvoice2

Astrbot的tts功能补充（使用Cosyvoice2-0.5b本地模型）

#配置

将[Cosyvoice官方文档](https://www.modelscope.cn/models/iic/CosyVoice2-0.5B/summary)中的操作做一遍，检查是否有遗漏的库（详见backup_py310.yaml），记得将Cosyvoice的项目文件拷贝到插件文件夹下  （eg.E:\AstrBot\data\plugins\astrbot_plugin_tts_Cosyvoice2 ）

只用下载CosyVoice2-0.5B模型即可

与官方tts方法一致，配置时用openai_tts_api即可，api填入127.0.0.1:5050，其余瞎填便可 

# 使用

eg. 

    /tts

    传入llm的内容

#新内容

for 1.0.0

优化了启动速度及顺序，更新了文件管理