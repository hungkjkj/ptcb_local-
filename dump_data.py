import pandas as pd
from vnstock import Finance
f = Finance(symbol='FPT', source='VCI')
df_cf = f.cash_flow(period='year')
df_cf.to_csv('fpt_cf.csv', encoding='utf-8-sig')
df_is = f.income_statement(period='year')
df_is.to_csv('fpt_is.csv', encoding='utf-8-sig')
df_bs = f.balance_sheet(period='year')
df_bs.to_csv('fpt_bs.csv', encoding='utf-8-sig')
