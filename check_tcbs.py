import os
os.environ["CODESPACE_NAME"] = "render_bypass"
import json
import codecs

try:
    with codecs.open('tcbs.json', 'r', encoding='utf-16le') as f:
        content = f.read()
        if content.startswith('\ufeff'):
            content = content[1:]
        try:
            data = json.loads(content)
            print("IT IS JSON! Keys:", list(data[0].keys())[:5])
        except Exception as e:
            print("NOT JSON. Content:", content[:300])
except Exception as e:
    print("Error:", e)
