import sys
import codecs
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())

import json
from quant_screener import get_comparative_report

print("--- Testing FPT (Non-Bank) ---")
res = get_comparative_report("FPT")
print(json.dumps(res['ranking'], indent=2, ensure_ascii=False))

print("--- Testing VCB (Bank) ---")
res2 = get_comparative_report("VCB")
print(json.dumps(res2['ranking'], indent=2, ensure_ascii=False))
