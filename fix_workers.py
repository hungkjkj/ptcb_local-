import re
with open('quant_screener.py', 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace('max_workers=5', 'max_workers=2')
with open('quant_screener.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Set max_workers to 2")
