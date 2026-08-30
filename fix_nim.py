import re

with open('quant_screener.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Force VCI for df_ratio_q
content = content.replace("df_ratio_q = f.ratio(period='quarter')", "df_ratio_q = Finance(symbol=ticker, source='VCI').ratio(period='quarter')")

# Fix nim division
content = re.sub(r'if nim: nim = nim / 100', 'if nim and abs(nim) > 0.5: nim = nim / 100', content)
content = re.sub(r'if nim_q: nim_q = nim_q / 100', 'if nim_q and abs(nim_q) > 0.5: nim_q = nim_q / 100', content)

with open('quant_screener.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Patched quant_screener.py")
