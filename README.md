# astrbot_plugin_tts_Cosyvoice2

Astrbot的tts功能补充（使用Cosyvoice2-0.5B本地模型）

# 配置

需要ffmpeg在系统路径下

将[Cosyvoice官方文档](https://www.modelscope.cn/models/iic/CosyVoice2-0.5B/summary)中的操作做一遍，检查是否有遗漏的库未安装

使用命令 `pip  install -r requirements.txt` 在shell安装所需库

与官方tts方法一致，配置时用openai_tts_api，api填入127.0.0.1:5050，超时建议在60左右，key随意

在插件配置中添加：TensorRT开关、fp16开关等

# 使用

eg. 

`/tts`以开启/关闭文字转语音

`/tts_cfg`（命令组）包括`/tts_cfg list` 、 `/tts_cfg set voice xxx` 、 `/tts_cfg set form 普通话`


# 新内容

## for 1.0.6

很多，可以自己看看，更新了指令，取消了预启动（真的不会做）
