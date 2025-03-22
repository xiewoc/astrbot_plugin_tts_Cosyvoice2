# astrbot_plugin_tts_Cosyvoice2

## Astrbot的tts功能补充（使用Cosyvoice2-0.5B本地模型）

# 配置

### 需要ffmpeg在系统路径下！

将[Cosyvoice官方文档](https://www.modelscope.cn/models/iic/CosyVoice2-0.5B/summary)中的操作做一遍，检查是否有遗漏的库未安装

再使用命令 `pip  install -r requirements.txt` 在shell安装所需库

与官方tts方法一致，配置时用openai_tts_api，api填入127.0.0.1:5050，超时建议在60~90s左右，key随意

# 使用

## eg. 

`/tts`以开启/关闭文字转语音

`/tts_cfg`（命令组）：

```
/tts_cfg
|-set|-voice
|    |-dialect
|    |-method
|-list
```

# 更新内容

## for 1.0.7

将传参方式大改了一下；重新加回了预加载；更新了`/tts_cfg set method xxx`指令，用以更换生成方式；支持了分布式部署；支持了function_call功能；优化了整体结构；

## previous versions

更新了指令，取消了预启动（真的不会做），更改了路径（./Cosyvoice/pretrained_models/Cosyvoice2_0.5B -> ./pretrained_models/Cosyvoice2_0.5B）、在插件配置中添加：TensorRT开关、fp16开关等

# 球球了，给孩子点个star吧！

# 自带音频

目前作者只给了`prompt_绯莎.wav`和`prompt_明.wav`，后续会持续更新，你们也可以自己创建，构建如下：

语音格式应为wav文件，码率不低于16KHz，创建同名.json文件内容如下：

```
{
    "text":"语音内容文字（模式若为instruct2则可不填）",
    "form":"语种（方言），目前支持普通话、四川话、上海话、湖北话等（见cosyvoice官方文档）",
    "generate_method":"生成模式（zero_shot或instruct2，如果不填，则为instruct2）"
}
```

eg.

```
{
    "text":"相信我吧，我会带你们走向光明",
    "form":"普通话",
    "generate_method":"zero_shot"
}
```

# 当然，A lot of codes borrowed from Cosyvoice ,show respect to them
