import requests
import json

url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
headers = {
    "Authorization": "Bearer sk-d9321d77876b4f1a9f0aeba1222e74df",
    "Content-Type": "application/json"
}

data = {
    "model": "deepseek-r1",
    "messages": [{"role": "user", "content": "请分析一个复杂的中医病例"}],
    "stream": True,
    "include_usage": True  # 尝试获取更多信息
}

print("尝试获取完整思考过程...")
print("=" * 80)
response = requests.post(url, headers=headers, json=data, stream=True)

chunk_count = 0
thinking_count = 0
content_count = 0

for line in response.iter_lines():
    if line:
        line = line.decode('utf-8')
        if line.startswith('data: '):
            content = line[6:]
            if content.strip() == '[DONE]':
                break
            
            chunk_count += 1
            
            try:
                data = json.loads(content)
                
                # 打印完整的JSON结构
                print(f"\n[块 {chunk_count}] 完整JSON:")
                print(json.dumps(data, ensure_ascii=False, indent=2))
                
                if 'choices' in data and data['choices']:
                    choice = data['choices'][0]
                    
                    # 检查所有可能的字段
                    print(f"Choice中的所有字段: {list(choice.keys())}")
                    
                    if 'delta' in choice:
                        delta = choice['delta']
                        print(f"Delta中的所有字段: {list(delta.keys())}")
                        
                        # 检查是否有思考相关的字段
                        for key, value in delta.items():
                            if key == 'content':
                                if value is None:
                                    thinking_count += 1
                                    print(f"[思考步骤 {thinking_count}] content为None - 可能在思考")
                                elif value:
                                    content_count += 1
                                    print(f"[输出内容 {content_count}]: {repr(value)}")
                            else:
                                print(f"[其他字段 {key}]: {repr(value)}")
                    
                    # 检查choice中的其他字段
                    for key, value in choice.items():
                        if key != 'delta':
                            print(f"[Choice字段 {key}]: {repr(value)}")
                
                print("-" * 60)
                
            except Exception as e:
                print(f"解析错误: {e}")
                print(f"原始内容: {content}")

print(f"\n统计:")
print(f"总数据块: {chunk_count}")
print(f"思考步骤: {thinking_count}")
print(f"内容输出: {content_count}")
print("测试完成!")
