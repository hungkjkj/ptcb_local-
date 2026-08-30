import re
with open('quant_screener.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if '"NIM"' in line:
        lines[i] = re.sub(r'\[\"NIM\".*?\]', '["NIM", "lãi thuần", "thu nhập lãi thuần"]', line)
    elif '"n' in line and '"NPL"' in line:
        lines[i] = re.sub(r'\[\"n.*?, \"NPL\"\]', '["nợ xấu", "NPL", "tỷ lệ nợ xấu"]', line)
    elif '"Bao ph' in line and 'LLR' in line:
        lines[i] = re.sub(r'\[\"Bao ph.*?, \"LLR\".*?\]', '["Bao phủ", "LLR", "dự phòng bao nợ xấu"]', line)
    elif 'Income tax expense' in line:
        lines[i] = re.sub(r'\[\"Chi ph.*?Income tax expense\"\]', '["thuế thu nhập doanh nghiệp", "Income tax expense"]', line)
    elif 'Liabilities' in line:
        lines[i] = re.sub(r'\[\"N.*?, \"Liabilities\".*?\]', '["Nợ phải trả", "Liabilities", "Tổng nợ"]', line)

with open('quant_screener.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
