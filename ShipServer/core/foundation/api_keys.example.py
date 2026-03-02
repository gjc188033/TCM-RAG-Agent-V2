import os

# 阿里云 DashScope API 配置
# 请设置环境变量 DASHSCOPE_API_KEY，或在此处填写你的 API Key
APIkey = os.environ.get("DASHSCOPE_API_KEY", "your-api-key-here")

APIUrl = "https://dashscope.aliyuncs.com/compatible-mode/v1"

model = "qwen3-max"
