import requests
import json

url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
headers = {
    "Authorization": "Bearer sk-d9321d77876b4f1a9f0aeba1222e74df",
    "Content-Type": "application/json"
}

data = {
    "model": "deepseek-r1",
    "messages": [{"role": "user", "content": "请详细分析一个复杂的中医病例，包括症状分析、病机推理、证型判断和治疗方案"}],
    "stream": True
}

print("🧠 Deepseek R1 完整思考过程展示")
print("=" * 80)
response = requests.post(url, headers=headers, json=data, stream=True)

thinking_content = ""
output_content = ""
thinking_mode = True

print("💭 【思考过程】:")
print("-" * 40)

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
                    choice = data['choices'][0]
                    if 'delta' in choice:
                        delta = choice['delta']
                        
                        # 处理思考过程
                        if 'reasoning_content' in delta and delta['reasoning_content']:
                            thinking_content += delta['reasoning_content']
                            print(delta['reasoning_content'], end='', flush=True)
                        
                        # 处理输出内容
                        if 'content' in delta and delta['content']:
                            if thinking_mode:
                                print(f"\n\n{'='*80}")
                                print("📝 【最终回答】:")
                                print("-" * 40)
                                thinking_mode = False
                            
                            output_content += delta['content']
                            print(delta['content'], end='', flush=True)
                            
            except Exception as e:
                continue

print(f"\n\n{'='*80}")
print("📊 【统计信息】:")
print(f"思考过程长度: {len(thinking_content)} 字符")
print(f"最终回答长度: {len(output_content)} 字符")
print(f"思考/回答比例: {len(thinking_content)/(len(output_content)+1):.2f}")

# 保存完整内容
with open('thinking_process.txt', 'w', encoding='utf-8') as f:
    f.write("=== 思考过程 ===\n")
    f.write(thinking_content)
    f.write("\n\n=== 最终回答 ===\n")
    f.write(output_content)

print("完整内容已保存到 thinking_process.txt")
print("🎉 测试完成!")
