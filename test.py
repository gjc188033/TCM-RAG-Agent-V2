import requests
import json

url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
headers = {
    "Authorization": "Bearer sk-d9321d77876b4f1a9f0aeba1222e74df",
    "Content-Type": "application/json"
}

data = {
    "model": "deepseek-r1",
    "messages": [{"role": "user", "content": "请分析中医阴阳理论"}],
    "stream": True
}

print("开始测试...")
response = requests.post(url, headers=headers, json=data, stream=True)

for line in response.iter_lines():
    if line:
        line = line.decode('utf-8')
        if line.startswith('data: '):
            content = line[6:]
            if content.strip() == '[DONE]':
                break
            try:
                data = json.loads(content)
                if 'choices' in data and data['choices']:
                    delta = data['choices'][0].get('delta', {})
                    if 'content' in delta and delta['content'] is not None:
                        text = delta['content']
                        print(text, end='', flush=True)
                    elif 'content' in delta and delta['content'] is None:
                        print("[思考中...]", end='', flush=True)
            except:
                pass

print("\n完成!")
