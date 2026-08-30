import re

with open('quant_screener.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace Thuế
content = re.sub(r'\["Chi phA.*?thu.*?nh.*?p doanh nghi.*?p", "Income tax expense"\]', '["thuế thu nhập doanh nghiệp", "Income tax expense"]', content)
# Replace Nợ
content = re.sub(r'\["N.*? ph.*?i tr.*?", "Liabilities", "T.*? ng n.*?"\]', '["nợ phải trả", "Liabilities", "tổng nợ"]', content)

with open('quant_screener.py', 'w', encoding='utf-8') as f:
    f.write(content)
