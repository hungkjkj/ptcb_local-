import pandas as pd
import numpy as np
import time
import warnings

# Suppress warnings
warnings.filterwarnings('ignore')

import os
os.environ["CODESPACE_NAME"] = "render_bypass" # Fix bug hosting_service của vnstock trên server Render
from vnstock import Listing, Finance, Vnstock, Company

def get_available_sectors():
    """ Trả về danh sách tất cả các ngành nghề trên thị trường. """
    try:
        df = Listing().symbols_by_industries()
        if df is not None and not df.empty and 'industry_name' in df.columns:
            sectors = df['industry_name'].dropna().unique().tolist()
            blacklist = ["bất động sản"]
            filtered_sectors = []
            for s in sectors:
                if not s.strip(): continue
                if not any(b in s.lower() for b in blacklist):
                    filtered_sectors.append(s)
            return sorted(filtered_sectors)
        return []
    except Exception as e:
        print("Loi khi lấy danh sách ngành:", e)
        # Fallback danh sách tĩnh nếu API lỗi
        return ["Bán lẻ", "Công nghệ thông tin", "Dầu khí", "Hóa chất", "Hàng tiêu dùng", "Xây dựng và Vật liệu", "Tài nguyên Cơ bản"]

def get_tickers_by_sector(sector):
    """ Lấy danh sách ticker thuộc một ngành cụ thể. """
    import json
    import os
    try:
        if os.path.exists("sectors_config.json"):
            with open("sectors_config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
                for group, tickers in config.items():
                    if group.lower() == sector.lower():
                        return tickers
    except Exception as e:
        print("Loi đọc sectors_config.json:", e)

    # Fallback to old defaults if config doesn't exist
    s = sector.lower()
    if s in ['ngân hàng', 'banks']:
        return ["VCB", "BID", "CTG", "TCB", "VPB", "MBB", "ACB", "STB", "HDB", "VIB", "TPB", "SHB", "LPB", "SSB", "MSB", "OCB", "EIB", "NAB"]
    elif s == 'bán lẻ':
        return ["MWG", "PNJ", "FRT", "DGW", "PET"]
    elif s == 'công nghệ thông tin':
        return ["FPT", "CMG", "ELC", "ITD"]
    elif s == 'xây dựng và vật liệu':
        return ["HPG", "HSG", "NKG", "VCG", "CTD", "HBC", "HT1", "BCC"]
    elif s in ['chứng khoán', 'securities', 'dịch vụ tài chính']:
        return ["SSI", "VND", "VCI", "HCM", "SHS", "MBS", "FTS", "BSI", "CTS", "VIX"]

    try:
        df = Listing().symbols_by_industries()
        if df is not None and not df.empty and 'industry_name' in df.columns:
            df_sector = df[df['industry_name'] == sector]
            if not df_sector.empty and 'symbol' in df_sector.columns:
                return df_sector['symbol'].tolist()
    except Exception as e:
        print("Loi lấy mã theo ngành:", e)
    return []

def get_row_value(df, keywords, year_str, default=0):
    if df is None or df.empty:
        return default
    if isinstance(keywords, str):
        keywords = [keywords]
        
    try:
        matches = pd.DataFrame()
        item_col = df.columns[0] 
        for kw in keywords:
            m = df[df[item_col].astype(str).str.contains(kw, case=False, na=False, regex=False)]
            if not m.empty:
                matches = m
                break
                
        if not matches.empty:
            if year_str in matches.columns:
                for i in range(len(matches)):
                    val = matches.iloc[i][year_str]
                    if pd.notna(val) and str(val).strip() != '':
                        try:
                            return float(val)
                        except:
                            pass
    except Exception as e:
        pass
    return default

def get_ttm_value(df, keywords, default=0):
    if df is None or df.empty: return default
    if isinstance(keywords, str): keywords = [keywords]
    try:
        matches = pd.DataFrame()
        item_col = df.columns[0]
        for kw in keywords:
            m = df[df[item_col].astype(str).str.contains(kw, case=False, na=False, regex=False)]
            if not m.empty:
                matches = m
                break
        if not matches.empty:
            q_cols = [c for c in df.columns if '-Q' in str(c) and len(str(c)) == 7]
            q_cols.sort(reverse=True)
            if not q_cols: return default
            
            for i in range(len(matches)):
                valid_start_idx = -1
                for idx, q in enumerate(q_cols):
                    val = matches.iloc[i][q]
                    if pd.notna(val) and str(val).strip() != '':
                        valid_start_idx = idx
                        break
                
                if valid_start_idx != -1:
                    total = 0
                    valid_count = 0
                    for q in q_cols[valid_start_idx : valid_start_idx + 4]:
                        val = matches.iloc[i][q]
                        if pd.notna(val) and str(val).strip() != '':
                            try:
                                total += float(val)
                                valid_count += 1
                            except: pass
                    if valid_count > 0:
                        return total
    except: pass
    return default

def get_latest_q_value(df, keywords, default=0):
    if df is None or df.empty: return default
    if isinstance(keywords, str): keywords = [keywords]
    try:
        matches = pd.DataFrame()
        item_col = df.columns[0]
        for kw in keywords:
            m = df[df[item_col].astype(str).str.contains(kw, case=False, na=False, regex=False)]
            if not m.empty:
                matches = m
                break
        if not matches.empty:
            q_cols = [c for c in df.columns if '-Q' in str(c) and len(str(c)) == 7]
            q_cols.sort(reverse=True)
            if not q_cols: return default
            for i in range(len(matches)):
                for q in q_cols:
                    val = matches.iloc[i][q]
                    if pd.notna(val) and str(val).strip() != '':
                        try: return float(val)
                        except: pass
    except: pass
    return default

def get_latest_quarter_str(df, keywords):
    if df is None or df.empty: return ""
    if isinstance(keywords, str): keywords = [keywords]
    import pandas as pd
    try:
        matches = pd.DataFrame()
        item_col = df.columns[0]
        for kw in keywords:
            m = df[df[item_col].astype(str).str.contains(kw, case=False, na=False, regex=False)]
            if not m.empty:
                matches = m
                break
        if not matches.empty:
            q_cols = [c for c in df.columns if '-Q' in str(c) and len(str(c)) == 7]
            q_cols.sort(reverse=True)
            if not q_cols: return ""
            for q in q_cols:
                for i in range(len(matches)):
                    val = matches.iloc[i][q]
                    if pd.notna(val) and str(val).strip() != '':
                        return q
    except: pass
    return ""

def get_top_market_cap(tickers, limit=20):
    """ Lấy danh sách Top mã (ưu tiên vốn hóa lớn nhất) bằng cách đối chiếu với VN100. Tốc độ ánh sáng, không gọi API tài chính. """
    try:
        vn100_data = Listing().symbols_by_group('VN100')
        if vn100_data is not None and not vn100_data.empty:
            if isinstance(vn100_data, pd.Series):
                vn100_symbols = vn100_data.tolist()
            elif 'symbol' in vn100_data.columns:
                vn100_symbols = vn100_data['symbol'].tolist()
            elif 'ticker' in vn100_data.columns:
                vn100_symbols = vn100_data['ticker'].tolist()
            else:
                vn100_symbols = []
                
            # Lọc các mã trong ngành có mặt trong rổ VN100 (những công ty đầu ngành)
            top_vn100_tickers = [t for t in tickers if t in vn100_symbols]
            
            # Lấy market_cap để sort chính xác
            ticker_mcaps = []
            for t in top_vn100_tickers:
                try:
                    df = Company(symbol=t, source='VCI').overview()
                    mcap = df.iloc[0].get('market_cap', 0) if not df.empty else 0
                    ticker_mcaps.append((t, mcap))
                except:
                    ticker_mcaps.append((t, 0))
                    
            # Sắp xếp theo vốn hóa giảm dần
            ticker_mcaps.sort(key=lambda x: x[1], reverse=True)
            top_tickers = [x[0] for x in ticker_mcaps]
            
            # Nếu ngành nhỏ không đủ 10 mã trong VN100, lấy thêm các mã ngoài cho đủ limit
            for t in tickers:
                if t not in top_tickers:
                    top_tickers.append(t)
                if len(top_tickers) >= limit:
                    break
                    
            return top_tickers[:limit]
    except Exception as e:
        print("Loi khi đối chiếu VN100:", e)
        
    return tickers[:limit]

def calculate_engine_securities(ticker):
    try:
        f = Finance(symbol=ticker, source='KBS')
        df_ratio = f.ratio(period='year')
        
        try:
            df_ratio_q = f.ratio(period='quarter')
        except:
            df_ratio_q = None
        
        if df_ratio is None or df_ratio.empty:
            return None
            
        years_cols = [c for c in df_ratio.columns if str(c).startswith('20') and '-Năm' in str(c)]
        if not years_cols:
            years_cols = [c for c in df_ratio.columns if str(c).startswith('20')]
            if not years_cols:
                return None
        
        years_cols = sorted(years_cols, reverse=True)
        latest_year_str = years_cols[0]
        
        pb = get_latest_q_value(df_ratio_q, ["P/B", "giá trị sổ sách (P/B)"])
        if pb == 0: pb = get_row_value(df_ratio, ["P/B", "giá trị sổ sách (P/B)"], latest_year_str)
        
        pe = get_latest_q_value(df_ratio_q, ["P/E", "thu nhập trên cổ phần (P/E)"])
        if pe == 0: pe = get_row_value(df_ratio, ["P/E", "thu nhập trên cổ phần (P/E)"], latest_year_str)
        
        roe_ttm = get_latest_q_value(df_ratio_q, ["ROE bình quân 4 quý", "roe_trailling", "ROEA", "ROE", "lợi nhuận trên vốn chủ sở hữu"])
        if roe_ttm == 0: roe_ttm = get_row_value(df_ratio, ["ROEA", "ROE", "lợi nhuận trên vốn chủ sở hữu"], latest_year_str)
        if roe_ttm and abs(roe_ttm) > 1 and abs(roe_ttm) < 100: roe_ttm = roe_ttm / 100
        
        avg_roe_5y = 0
        valid_roe_count = 0
        for y_col in years_cols[:5]:
            val = get_row_value(df_ratio, ["ROEA", "ROE", "lợi nhuận trên vốn chủ sở hữu"], y_col)
            if val != 0:
                if abs(val) > 1 and abs(val) < 100: val = val / 100
                avg_roe_5y += val
                valid_roe_count += 1
        avg_roe_5y = avg_roe_5y / valid_roe_count if valid_roe_count > 0 else roe_ttm

        roa = get_latest_q_value(df_ratio_q, ["ROA bình quân 4 quý", "roa_trailling", "ROAA", "ROA", "sinh lợi trên tổng tài sản"])
        if roa == 0: roa = get_row_value(df_ratio, ["ROAA", "ROA", "sinh lợi trên tổng tài sản"], latest_year_str)
        if roa and abs(roa) < 100: roa = roa / 100

        equity_ratio = (roa / roe_ttm) if roe_ttm > 0 else 0
        
        try:
            overview_df = Company(symbol=ticker, source='VCI').overview()
            current_price = overview_df.iloc[0].get('current_price', 0) if not overview_df.empty else 0
        except:
            current_price = 0
            
        if not pb or not pe or not roe_ttm:
            return None
            
        return {
            'Ticker': ticker,
            'PB': float(pb),
            'PE': float(pe),
            'ROE_TTM': float(roe_ttm),
            'ROE_5Y': float(avg_roe_5y),
            'Equity_Ratio': float(equity_ratio),
            'Current_Price': float(current_price)
        }
    except Exception as e:
        return None

def calculate_engine_bank(ticker):
    try:
        f = Finance(symbol=ticker, source='KBS')
        df_ratio = f.ratio(period='year')
        
        try:
            df_ratio_q = f.ratio(period='quarter')
        except:
            df_ratio_q = None
        
        if df_ratio is None or df_ratio.empty:
            return None
            
        years_cols = [c for c in df_ratio.columns if str(c).startswith('20') and '-Năm' in str(c)]
        if not years_cols:
            years_cols = [c for c in df_ratio.columns if str(c).startswith('20')]
            if not years_cols:
                return None
        
        years_cols = sorted(years_cols, reverse=True)
        latest_year_str = years_cols[0]
        
        import re
        match = re.search(r'\d{4}', str(latest_year_str))
        if not match:
            return None
            
        latest_year = int(match.group(0))
        current_year = pd.Timestamp.now().year
        if latest_year < current_year - 2:
            return None
            
        roa = get_latest_q_value(df_ratio_q, ["ROA bình quân 4 quý", "roa_trailling", "ROAA", "ROA", "sinh lợi trên tổng tài sản"])
        if roa == 0: roa = get_row_value(df_ratio, ["ROAA", "ROA", "sinh lợi trên tổng tài sản"], latest_year_str)
        if roa and abs(roa) < 100: roa = roa / 100
             
        roe = get_latest_q_value(df_ratio_q, ["ROE bình quân 4 quý", "roe_trailling", "ROEA", "ROE", "lợi nhuận trên vốn chủ sở hữu"])
        if roe == 0: roe = get_row_value(df_ratio, ["ROEA", "ROE", "lợi nhuận trên vốn chủ sở hữu"], latest_year_str)
        if roe and abs(roe) > 1 and abs(roe) < 100: roe = roe / 100
             
        nim = get_latest_q_value(df_ratio_q, ["NIM", "lãi thuần", "thu nhập lãi thuần"])
        if nim == 0: nim = get_row_value(df_ratio, ["NIM", "lãi thuần", "thu nhập lãi thuần"], latest_year_str)
        if nim and abs(nim) > 0.5 and abs(nim) < 100: nim = nim / 100
            
        try:
            overview_df = Company(symbol=ticker, source='VCI').overview()
            current_price = overview_df.iloc[0].get('current_price', 0) if not overview_df.empty else 0
        except:
            current_price = 0
            
        pb = get_latest_q_value(df_ratio_q, ["P/B", "giá trị sổ sách (P/B)"])
        if pb == 0: pb = get_row_value(df_ratio, ["P/B", "giá trị sổ sách (P/B)"], latest_year_str)
        
        if not roa or not roe or not nim or not pb:
            return None
            
        value_ratio = roe / pb if pb > 0 else 0
        equity_ratio = (roa / roe) if roe > 0 else 0

        return {
            'Ticker': ticker,
            'ROA': float(roa),
            'ROE': float(roe),
            'NIM': float(nim),
            'PB': float(pb),
            'Value_Ratio': float(value_ratio),
            'Equity_Ratio': float(equity_ratio),
            'Current_Price': float(current_price)
        }
    except Exception as e:
        return None

def calculate_engine(ticker, tax_rate_fallback=0.2):
    try:
        f = Finance(symbol=ticker, source='KBS')
        
        df_ratio = f.ratio(period='year')
        if df_ratio is None or df_ratio.empty:
            return None
            
        try:
            df_ratio_q = f.ratio(period='quarter')
        except:
            df_ratio_q = None

        years_cols = [c for c in df_ratio.columns if '-' in str(c) or 'Năm' in str(c) or str(c).startswith('20')]
        years_cols = sorted(years_cols, reverse=True)
        if len(years_cols) < 3:
            return None
            
        import re
        latest_year_str = years_cols[0]
        
        try:
            overview_df = Company(symbol=ticker, source='VCI').overview()
            current_price = overview_df.iloc[0].get('current_price', 0) if not overview_df.empty else 0
        except:
            current_price = 0

        # Calculate ROIC 5Y from ROCE
        roic_list = []
        for i in range(min(len(years_cols), 5)):
            y = years_cols[i]
            roce = get_row_value(df_ratio, ["ROCE", "return_on_capital_employed_roce", "Tỷ suất sinh lợi trên vốn dài hạn bình quân"], year_str=str(y))
            if roce and abs(roce) < 200: roce = roce / 100
            if roce: roic_list.append(roce)
            
        avg_roic_5y = np.mean(roic_list) if roic_list else 0
        
        # Current Value Ratio
        pe = get_latest_q_value(df_ratio_q, ["pe_ratio", "P/E", "Chỉ số giá thị trường trên thu nhập"]) if df_ratio_q is not None else 0
        if pe == 0: pe = get_row_value(df_ratio, ["pe_ratio", "P/E", "Chỉ số giá thị trường trên thu nhập"], latest_year_str)
        
        ep_ratio = 1 / pe if pe > 0 else 0
        
        # CFO Quality
        cfo_quality_ttm = get_latest_q_value(df_ratio_q, ["cash_to_income_2", "Dòng tiền từ HĐKD trên Lợi nhuận thuần"]) if df_ratio_q is not None else 0
        if cfo_quality_ttm == 0:
            cfo_quality_ttm = get_row_value(df_ratio, ["cash_to_income_2", "Dòng tiền từ HĐKD trên Lợi nhuận thuần"], latest_year_str)
        if cfo_quality_ttm and abs(cfo_quality_ttm) > 1 and abs(cfo_quality_ttm) < 1000: cfo_quality_ttm = cfo_quality_ttm / 100

        # ED Current (Equity / Debt)
        de_current = get_latest_q_value(df_ratio_q, ["debt_to_equity", "Nợ vay trên Vốn chủ sở hữu"]) if df_ratio_q is not None else 0
        if de_current == 0:
            de_current = get_row_value(df_ratio, ["debt_to_equity", "Nợ vay trên Vốn chủ sở hữu"], latest_year_str)
        if de_current and abs(de_current) > 1 and abs(de_current) < 1000: de_current = de_current / 100
        
        ed_current = (1 / de_current) if de_current > 0 else 10.0
            
        # PB Current
        pb_current = get_latest_q_value(df_ratio_q, ["pb_ratio", "P/B"]) if df_ratio_q is not None else 0
        if pb_current == 0:
            pb_current = get_row_value(df_ratio, ["pb_ratio", "P/B"], latest_year_str)
            
        # ROIC TTM
        roic_ttm = get_latest_q_value(df_ratio_q, ["ROCE", "return_on_capital_employed_roce"]) if df_ratio_q is not None else 0
        if roic_ttm == 0:
            roic_ttm = get_row_value(df_ratio, ["ROCE", "return_on_capital_employed_roce"], latest_year_str)
        if roic_ttm and abs(roic_ttm) < 200: roic_ttm = roic_ttm / 100

        value_ratio = (ep_ratio / roic_ttm) if roic_ttm > 0 else 0

        if not pb_current or not avg_roic_5y or not ep_ratio:
            return None

        return {
            'summary': {
                'ROIC_5Y': float(avg_roic_5y),
                'Value_Ratio': float(value_ratio),
                'CFO_Quality_TTM': float(cfo_quality_ttm),
                'ED_Current': float(ed_current),
                'ROIC_TTM': float(roic_ttm),
                'PB_Current': float(pb_current),
                'Current_Price': float(current_price)
            },
            'Ticker': ticker,
            'ROIC_5Y': float(avg_roic_5y),
            'Value_Ratio': float(value_ratio),
            'CFO_Quality_TTM': float(cfo_quality_ttm),
            'ED_Current': float(ed_current),
            'ROIC_TTM': float(roic_ttm),
            'PB_Current': float(pb_current)
        }
    except Exception as e:
        print(f"Error in engine {ticker}: {e}")
        return None

import threading
_scrape_lock = threading.Lock()

def with_lock(lock):
    def decorator(func):
        def wrapper(*args, **kwargs):
            with lock:
                return func(*args, **kwargs)
        return wrapper
    return decorator

@with_lock(_scrape_lock)
def run_screener_for_sector(sector, force_update=False):
    import json
    import os
    from datetime import datetime
    
    CACHE_DIR = "cache"
    if not os.path.exists(CACHE_DIR):
        try:
            os.makedirs(CACHE_DIR)
        except:
            pass
            
    safe_sector = "".join([c if c.isalnum() else "_" for c in sector])
    today = datetime.now().strftime("%Y-%m-%d")
    screener_cache_file = os.path.join(CACHE_DIR, f"screener_{safe_sector}_{today}.json")
    medians_cache_file = os.path.join(CACHE_DIR, f"medians_{safe_sector}_{today}.json")
    
    if not force_update and os.path.exists(screener_cache_file):
        try:
            with open(screener_cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
            
    # Clean old caches occasionally
    try:
        for filename in os.listdir(CACHE_DIR):
            if filename.endswith(".json") and today not in filename:
                os.remove(os.path.join(CACHE_DIR, filename))
    except:
        pass

    tickers = get_tickers_by_sector(sector)
    if not tickers:
        return []
        
    top_tickers = get_top_market_cap(tickers, limit=20)
    
    results = []
    
    if sector.lower() in ['chứng khoán', 'securities', 'dịch vụ tài chính']:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future_to_ticker = {executor.submit(calculate_engine_securities, t): t for t in top_tickers}
            for future in concurrent.futures.as_completed(future_to_ticker):
                try:
                    res = future.result()
                    if res:
                        results.append(res)
                except Exception as e:
                    print(f"Loi song song {future_to_ticker[future]}: {e}")
        df = pd.DataFrame(results)
        if df.empty:
            return []
            
        median_pb = df['PB'].median()
        median_pe = df['PE'].median()
        median_roe_ttm = df['ROE_TTM'].median()
        median_roe_5y = df['ROE_5Y'].median()
        median_eq = df['Equity_Ratio'].median()
        
        if pd.isna(median_pb) or median_pb == 0: median_pb = 1.5
        if pd.isna(median_pe) or median_pe == 0: median_pe = 15.0
        if pd.isna(median_roe_ttm) or median_roe_ttm == 0: median_roe_ttm = 0.10
        if pd.isna(median_roe_5y) or median_roe_5y == 0: median_roe_5y = 0.10
        if pd.isna(median_eq) or median_eq == 0: median_eq = 0.10
            
        try:
            with open(medians_cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'median_pb': float(median_pb),
                    'median_pe': float(median_pe),
                    'median_roe_ttm': float(median_roe_ttm),
                    'median_roe_5y': float(median_roe_5y),
                    'median_eq': float(median_eq)
                }, f)
        except:
            pass

        df['Score_PB'] = (median_pb / df['PB'].replace(0, np.nan)) * 100
        df['Score_PE'] = (median_pe / df['PE'].replace(0, np.nan)) * 100
        df['Score_ROE_TTM'] = (df['ROE_TTM'] / median_roe_ttm) * 100
        df['Score_ROE_5Y'] = (df['ROE_5Y'] / median_roe_5y) * 100
        df['Score_EQ'] = (df['Equity_Ratio'] / median_eq) * 100
        
        df['Total Score'] = (df['Score_PB'] * 0.30) + \
                            (df['Score_ROE_TTM'] * 0.20) + \
                            (df['Score_ROE_5Y'] * 0.15) + \
                            (df['Score_PE'] * 0.20) + \
                            (df['Score_EQ'] * 0.15)
                            
        df = df.sort_values(by='Total Score', ascending=False).reset_index(drop=True)
        df = df.fillna(0)
        
        final_results = df.to_dict('records')
        try:
            df.to_json(screener_cache_file, orient='records', force_ascii=False)
        except Exception as e:
            print("CACHE ERROR:", e)
        return final_results
        
    elif sector.lower() in ['ngân hàng', 'banks']:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future_to_ticker = {executor.submit(calculate_engine_bank, t): t for t in top_tickers}
            for future in concurrent.futures.as_completed(future_to_ticker):
                try:
                    res = future.result()
                    if res:
                        results.append(res)
                except Exception as e:
                    print(f"Loi song song {future_to_ticker[future]}: {e}")
        df = pd.DataFrame(results)
        if df.empty:
            return []
            
        # Tính trung vị (Median) của Top 10 Ngân hàng lớn nhất để làm quy chuẩn chung
        median_roa = df['ROA'].median()
        median_nim = df['NIM'].median()
        median_value = df['Value_Ratio'].median()
        median_eq = df['Equity_Ratio'].median()
        
        # Fallback nếu trung vị lỗi hoặc bằng 0
        if pd.isna(median_roa) or median_roa == 0: median_roa = 0.02
        if pd.isna(median_nim) or median_nim == 0: median_nim = 0.035
        if pd.isna(median_value) or median_value == 0: median_value = 10.0
        if pd.isna(median_eq) or median_eq == 0: median_eq = 0.10
            
        try:
            with open(medians_cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'median_roa': float(median_roa),
                    'median_nim': float(median_nim),
                    'median_value': float(median_value),
                    'median_eq': float(median_eq)
                }, f)
        except:
            pass

        df['Score_ROA'] = (df['ROA'] / median_roa) * 100
        df['Score_NIM'] = (df['NIM'].clip(upper=0.045) / median_nim) * 100
        df['Score_Value'] = (df['Value_Ratio'] / median_value) * 100
        df['Score_EQ'] = (df['Equity_Ratio'] / median_eq) * 100
        
        df['Total Score'] = (df['Score_Value'] * 0.30) + (df['Score_EQ'] * 0.25) + (df['Score_ROA'] * 0.25) + (df['Score_NIM'] * 0.20)
        df = df.sort_values(by='Total Score', ascending=False).reset_index(drop=True)
        df = df.fillna(0)
        
        final_results = df.to_dict('records')
        try:
            df.to_json(screener_cache_file, orient='records', force_ascii=False)
        except Exception as e:
            print("CACHE ERROR:", e)
        return final_results
    else:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future_to_ticker = {executor.submit(calculate_engine, t): t for t in top_tickers}
            for future in concurrent.futures.as_completed(future_to_ticker):
                try:
                    res = future.result()
                    if res:
                        results.append(res)
                except Exception as e:
                    print(f"Loi song song {future_to_ticker[future]}: {e}")
        df = pd.DataFrame(results)
        if df.empty:
            return []
            
        # SCORING - Absolute Median Normalization
        median_roic = df['ROIC_5Y'].median()
        median_roic_ttm = df['ROIC_TTM'].median()
        median_value = df['Value_Ratio'].median()
        median_cfo_ttm = df['CFO_Quality_TTM'].median()
        median_ed_curr = df['ED_Current'].median()
        
        if pd.isna(median_roic) or median_roic == 0: median_roic = 0.10
        if pd.isna(median_roic_ttm) or median_roic_ttm == 0: median_roic_ttm = 0.10
        if pd.isna(median_value) or median_value == 0: median_value = 10.0
        if pd.isna(median_cfo_ttm) or median_cfo_ttm == 0: median_cfo_ttm = 1.0
        if pd.isna(median_ed_curr) or median_ed_curr == 0: median_ed_curr = 1.0
        
        try:
            with open(medians_cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'median_roic': float(median_roic),
                    'median_roic_ttm': float(median_roic_ttm),
                    'median_value': float(median_value),
                    'median_cfo_ttm': float(median_cfo_ttm),
                    'median_ed_curr': float(median_ed_curr)
                }, f)
        except:
            pass

        df['Score_ROIC'] = (df['ROIC_5Y'] / median_roic) * 100
        df['Score_ROIC_TTM'] = (df['ROIC_TTM'] / median_roic_ttm) * 100
        df['Score_Value'] = (df['Value_Ratio'] / median_value) * 100
        
        df['Score_CFO_TTM'] = (df['CFO_Quality_TTM'] / median_cfo_ttm) * 100
        df.loc[df['CFO_Quality_TTM'] < 0, 'Score_CFO_TTM'] = 0
        
        df['Score_ED_Current'] = (df['ED_Current'] / median_ed_curr) * 100
        
        df['Total Score'] = (df['Score_ROIC'] * 0.15) + (df['Score_ROIC_TTM'] * 0.25) + \
                            (df['Score_Value'] * 0.20) + \
                            (df['Score_CFO_TTM'] * 0.20) + \
                            (df['Score_ED_Current'] * 0.20)
                            
        df = df.sort_values(by='Total Score', ascending=False).reset_index(drop=True)
        df = df.fillna(0)
        
        final_results = df.to_dict('records')
        try:
            df.to_json(screener_cache_file, orient='records', force_ascii=False)
        except Exception as e:
            print("CACHE ERROR:", e)
        return final_results

def get_stock_report(ticker, tax_rate_fallback=0.2):
    try:
        try:
            overview_df = Company(symbol=ticker, source='VCI').overview()
            if not overview_df.empty:
                company_name = overview_df.iloc[0].get('organ_name', ticker)
                sector = overview_df.iloc[0].get('sector', '')
                market_cap_overview = overview_df.iloc[0].get('market_cap', 0)
                current_price = overview_df.iloc[0].get('current_price', 0)
            else:
                company_name = ticker
                sector = ""
                market_cap_overview = 0
                current_price = 0
        except:
            company_name = ticker
            sector = ""
            market_cap_overview = 0
            current_price = 0
            
        if sector.lower() in ['ngân hàng', 'banks']:
            f_ratio = Finance(symbol=ticker, source='KBS')
            df_ratio = f_ratio.ratio(period='year')
            
            f_bs = Finance(symbol=ticker, source='VCI')
            df_bs = f_bs.balance_sheet(period='year')
            
            if df_ratio is None or df_ratio.empty:
                return None
                
            years_cols = [c for c in df_ratio.columns if str(c).startswith('20') and '-Năm' in str(c)]
            if not years_cols:
                years_cols = [c for c in df_ratio.columns if str(c).startswith('20')]
                if not years_cols: return None
                
            years_cols = sorted(years_cols, reverse=True)
            latest_year_str = years_cols[0]
            
            import re
            match = re.search(r'\d{4}', str(latest_year_str))
            if not match: return None
            latest_year = int(match.group(0))
            
            history = []
            num_years = min(len(years_cols), 5)
                
            for i in range(num_years):
                target_year_str = str(latest_year - i)
                ratio_year_str = f"{target_year_str}-Năm" if f"{target_year_str}-Năm" in df_ratio.columns else target_year_str
                bs_year_str = target_year_str
                
                nim = get_row_value(df_ratio, ["NIM", "lãi thuần", "thu nhập lãi thuần"], ratio_year_str)
                if nim and abs(nim) > 0.5: nim = nim / 100
                    
                llr = get_row_value(df_ratio, ["Bao phủ", "LLR", "dự phòng bao nợ xấu"], ratio_year_str)
                if llr: llr = abs(llr)
                    
                pb = get_row_value(df_ratio, ["P/B", "giá trị sổ sách (P/B)"], ratio_year_str)
                pe = get_row_value(df_ratio, ["P/E", "Chỉ số giá thị trường trên thu nhập (P/E)"], ratio_year_str)
                ep = 1 / pe if pe and pe != 0 else 0
                roe = get_row_value(df_ratio, ["ROE", "lợi nhuận trên vốn chủ sở hữu"], ratio_year_str)
                if roe and abs(roe) < 100: roe = roe / 100
                
                roa = get_row_value(df_ratio, ["ROAA", "ROA", "sinh lợi trên tổng tài sản"], ratio_year_str)
                if roa and abs(roa) < 100: roa = roa / 100
                
                value_ratio = (roe / pb) if pb and pb > 0 and roe else 0.0

                history.append({
                    'year': target_year_str,
                    'roa': float(roa) if roa else 0.0,
                    'nim': float(nim) if nim else 0.0,
                    'pb': float(pb) if pb else 0.0,
                    'ep': float(ep) if ep else 0.0,
                    'roe': float(roe) if roe else 0.0,
                    'value_ratio': float(value_ratio)
                })
            
            history.reverse()
            
            try:
                df_ratio_q = Finance(symbol=ticker, source='KBS').ratio(period='quarter')
            except:
                df_ratio_q = None
                
            latest_q_str = ""
            if df_ratio_q is not None and not df_ratio_q.empty:
                latest_q_str = get_latest_quarter_str(df_ratio_q, ["ROE", "P/B"])
            latest_y_str = str(history[-1]['year']) if history else ""
                
            roa_q = get_latest_q_value(df_ratio_q, ["ROA bình quân 4 quý", "roa_trailling", "ROAA", "ROA", "sinh lợi trên tổng tài sản"])
            if roa_q == 0: roa_q = history[-1].get('roa', 0) if history else 0
            if roa_q and abs(roa_q) < 100: roa_q = roa_q / 100
                
            roe_q = get_latest_q_value(df_ratio_q, ["ROE bình quân 4 quý", "roe_trailling", "ROEA", "ROE", "lợi nhuận trên vốn chủ sở hữu"])
            if roe_q == 0: roe_q = history[-1].get('roe', 0) if history else 0
            if roe_q and abs(roe_q) > 1 and abs(roe_q) < 100: roe_q = roe_q / 100
            
            nim_q = get_latest_q_value(df_ratio_q, ["NIM", "lãi thuần", "thu nhập lãi thuần"])
            if nim_q == 0: nim_q = history[-1].get('nim', 0) if history else 0
            if nim_q and abs(nim_q) > 0.5 and abs(nim_q) < 100: nim_q = nim_q / 100
                
            pb_q = get_latest_q_value(df_ratio_q, ["P/B", "giá trị sổ sách (P/B)"])
            if pb_q == 0: pb_q = history[-1].get('pb', 0) if history else 0
            
            value_ratio_q = (roe_q / pb_q) if pb_q and pb_q > 0 else 0
            equity_ratio_q = (roa_q / roe_q) if roe_q and roe_q > 0 else 0

            return {
                'ticker': ticker,
                'company_name': company_name,
                'sector': 'Ngân hàng',
                'summary': {
                    'ROA_Current': float(roa_q) if roa_q else 0,
                    'ROE_Current': float(roe_q) if roe_q else 0,
                    'NIM_Current': float(nim_q) if nim_q else 0,
                    'PB_Current': float(pb_q) if pb_q else 0,
                    'Value_Ratio_Current': float(value_ratio_q) if value_ratio_q else 0,
                    'Equity_Ratio_Current': float(equity_ratio_q) if equity_ratio_q else 0,
                    'Current_Price': float(current_price) if current_price else 0,
                    'Latest_Quarter': latest_q_str,
                    'Latest_Year': latest_y_str
                },
                'history': history
            }
            
        elif sector.lower() in ['chứng khoán', 'securities', 'dịch vụ tài chính', 'dịch vụ tài chính (mở rộng)', 'financial services']:
            f_ratio = Finance(symbol=ticker, source='KBS')
            df_ratio = f_ratio.ratio(period='year')
            
            try:
                df_ratio_q = f_ratio.ratio(period='quarter')
            except:
                df_ratio_q = None
                
            if df_ratio is None or df_ratio.empty:
                return None
                
            years_cols = [c for c in df_ratio.columns if str(c).startswith('20') and '-Năm' in str(c)]
            if not years_cols:
                years_cols = [c for c in df_ratio.columns if str(c).startswith('20')]
                if not years_cols: return None
                
            years_cols = sorted(years_cols, reverse=True)
            latest_year_str = years_cols[0]
            
            import re
            match = re.search(r'\d{4}', str(latest_year_str))
            if not match: return None
            latest_year = int(match.group(0))
            
            history = []
            num_years = min(len(years_cols), 5)
            
            for i in range(num_years):
                target_year_str = str(latest_year - i)
                ratio_year_str = f"{target_year_str}-Năm" if f"{target_year_str}-Năm" in df_ratio.columns else target_year_str
                
                roe = get_row_value(df_ratio, ["ROEA", "ROE", "lợi nhuận trên vốn chủ sở hữu"], ratio_year_str)
                if roe and abs(roe) > 1 and abs(roe) < 100: roe = roe / 100
                
                pb = get_row_value(df_ratio, ["P/B", "giá trị sổ sách (P/B)"], ratio_year_str)
                pe = get_row_value(df_ratio, ["P/E", "thu nhập trên cổ phần (P/E)", "Chỉ số giá thị trường trên thu nhập (P/E)"], ratio_year_str)
                roa = get_row_value(df_ratio, ["ROAA", "ROA", "sinh lợi trên tổng tài sản"], ratio_year_str)
                if roa and abs(roa) < 100: roa = roa / 100
                
                equity_ratio = (roa / roe) if (roe and roe > 0) else 0
                
                history.append({
                    'year': target_year_str,
                    'roe': float(roe) if roe else 0.0,
                    'pb': float(pb) if pb else 0.0,
                    'pe': float(pe) if pe else 0.0,
                    'roa': float(roa) if roa else 0.0,
                    'equity_ratio': float(equity_ratio)
                })
                
            history.reverse()
            roe_list = [h['roe'] for h in history if h['roe'] != 0]
            avg_roe_5y = sum(roe_list) / len(roe_list) if roe_list else 0
            
            latest_q_str = ""
            if df_ratio_q is not None and not df_ratio_q.empty:
                latest_q_str = get_latest_quarter_str(df_ratio_q, ["ROE", "P/B"])
            latest_y_str = str(history[-1]['year']) if history else ""
            
            pb_q = get_latest_q_value(df_ratio_q, ["P/B", "giá trị sổ sách (P/B)"])
            if pb_q == 0: pb_q = history[-1].get('pb', 0) if history else 0
            
            pe_q = get_latest_q_value(df_ratio_q, ["P/E", "thu nhập trên cổ phần (P/E)", "Chỉ số giá thị trường trên thu nhập (P/E)"])
            if pe_q == 0: pe_q = history[-1].get('pe', 0) if history else 0
            
            roe_ttm = get_latest_q_value(df_ratio_q, ["ROE bình quân 4 quý", "roe_trailling", "ROEA", "ROE", "lợi nhuận trên vốn chủ sở hữu"])
            if roe_ttm == 0: roe_ttm = history[-1].get('roe', 0) if history else 0
            if roe_ttm and abs(roe_ttm) > 1 and abs(roe_ttm) < 100: roe_ttm = roe_ttm / 100
            
            roa_q = get_latest_q_value(df_ratio_q, ["ROA bình quân 4 quý", "roa_trailling", "ROAA", "ROA", "sinh lợi trên tổng tài sản"])
            if roa_q == 0: roa_q = history[-1].get('roa', 0) if history else 0
            if roa_q and abs(roa_q) < 100: roa_q = roa_q / 100
            
            equity_ratio_q = (roa_q / roe_ttm) if (roe_ttm and roe_ttm > 0) else 0
            
            return {
                'ticker': ticker,
                'company_name': company_name,
                'sector': 'Chứng khoán',
                'summary': {
                    'PB_Current': float(pb_q) if pb_q else 0,
                    'PE_Current': float(pe_q) if pe_q else 0,
                    'ROE_TTM': float(roe_ttm) if roe_ttm else 0,
                    'ROE_5Y': float(avg_roe_5y),
                    'Equity_Ratio_Current': float(equity_ratio_q),
                    'Current_Price': float(current_price) if current_price else 0,
                    'Latest_Quarter': latest_q_str,
                    'Latest_Year': latest_y_str
                },
                'history': history
            }

            
        f = Finance(symbol=ticker, source='VCI')
        
        df_cf = f.cash_flow(period='year')
        df_is = f.income_statement(period='year')
        df_bs = f.balance_sheet(period='year')
        
        if df_cf is None or df_is is None or df_bs is None:
            return None
            
        years_cols = [c for c in df_is.columns if str(c).startswith('20')]
        years_cols = sorted(years_cols, reverse=True)
        if len(years_cols) == 0:
            return None
            
        import re
        latest_year_str = years_cols[0]
        match = re.search(r'\d{4}', str(latest_year_str))
        if not match:
            return None
            
        latest_year = int(match.group(0))
        
        try:
            f_ratio = Finance(symbol=ticker, source='KBS')
            df_ratio = f_ratio.ratio(period='year')
        except:
            df_ratio = pd.DataFrame()
            
        num_years = min(len(years_cols), 5)
        
        history = []
        
        for i in range(num_years):
            target_year_str = str(latest_year - i)
            ebt = get_row_value(df_is, ["Lãi/(lỗ) trước thuế", "Tổng lợi nhuận kế toán trước thuế", "Lợi nhuận trước thuế", "Profit before tax"], year_str=target_year_str)
            tax = get_row_value(df_is, ["thuế thu nhập doanh nghiệp", "Income tax expense"], year_str=target_year_str)
            ni = get_row_value(df_is, ["Lãi/(lỗ) thuần sau thuế", "Lợi nhuận của Cổ đông của Công ty mẹ", "Lợi nhuận sau thuế", "Net income"], year_str=target_year_str)
            ebit = get_row_value(df_is, ["Lãi/(lỗ) từ hoạt động kinh doanh", "Lợi nhuận thuần từ hoạt động kinh doanh", "Operating profit"], year_str=target_year_str)
            if ebit == 0:
                ebit = ebt 
            
            if ebt > 0:
                tax_rate = tax / ebt
                tax_rate = max(0.0, min(0.22, tax_rate))
            else:
                tax_rate = tax_rate_fallback
                
            equity = get_row_value(df_bs, ["Vốn chủ sở hữu", "Equity"], year_str=target_year_str)
            debt = get_row_value(df_bs, ["Nợ phải trả", "Liabilities", "Tổng nợ"], year_str=target_year_str)
            cash = get_row_value(df_bs, ["Tiền và tương đương tiền", "Tiền và các khoản tương đương tiền", "Cash and cash equivalents"], year_str=target_year_str)
            
            cfo = get_row_value(df_cf, ["Lưu chuyển tiền tệ ròng từ các hoạt động sản xuất kinh doanh", "Lưu chuyển tiền thuần từ hoạt động kinh doanh", "Net cash flows from operating activities"], year_str=target_year_str)
            
            invested_capital = equity + debt - cash
            roic = (ebit * (1 - tax_rate)) / invested_capital if invested_capital > 0 else 0
            de = debt / equity if equity > 0 else 0
            
            # Tính B/P
            ratio_year_str = f"{target_year_str}-Năm"
            pb = get_row_value(df_ratio, ["P/B", "Chỉ số giá thị trường trên giá trị sổ sách (P/B)"], year_str=ratio_year_str)
            bp = 1 / pb if pb > 0 else 0
            pe = get_row_value(df_ratio, ["P/E", "Chỉ số giá thị trường trên thu nhập (P/E)"], year_str=ratio_year_str)
            ep = 1 / pe if pe and pe != 0 else 0
            
            # Tính ICR
            interest = get_row_value(df_is, ["Chi phí lãi vay", "Interest expense"], year_str=target_year_str)
            if interest and interest != 0:
                icr = ebit / abs(interest)
            else:
                icr = get_row_value(df_ratio, ["Khả năng thanh toán lãi vay", "ICR"], year_str=ratio_year_str)
                
            history.append({
                'year': target_year_str,
                'roic': roic,
                'de': de,
                'cfo': cfo,
                'ni': ni,
                'bp': bp,
                'icr': icr,
                'ep': ep
            })
            
        # Reverse history so it is chronological (oldest to newest)
        history.reverse()
        
        # Calculate averages for summary
        roic_list = [h['roic'] for h in history]
        de_list = [h['de'] for h in history]
        total_cfo = sum(h['cfo'] for h in history)
        total_ni = sum(h['ni'] for h in history)
        
        avg_roic_5y = np.mean(roic_list) if roic_list else 0
        avg_de_5y = np.mean(de_list) if de_list else 0
        cfo_quality = total_cfo / total_ni if total_ni != 0 else 0
        
        net_income_current = history[-1]['ni'] if history else 0
        
        ep_list = [h['ep'] for h in history if h['ep'] > 0]
        avg_ep = np.mean(ep_list) if ep_list else 0
        value_ratio = (avg_ep / avg_roic_5y) if avg_roic_5y != 0 else 0
        
        bp_list = [h['bp'] for h in history if h['bp'] > 0]
        avg_bp = np.mean(bp_list) if bp_list else 0
        
        ed_list = [1 / h['de'] if h['de'] > 0 else 1000 for h in history]
        avg_ed_5y = np.mean(ed_list) if ed_list else 0
        
        current_icr = history[-1]['icr'] if history else 0

        try:
            df_cf_q = f.cash_flow(period='quarter')
            df_is_q = f.income_statement(period='quarter')
            df_bs_q = f.balance_sheet(period='quarter')
            df_ratio_q = f.ratio(period='quarter')
        except:
            df_cf_q, df_is_q, df_bs_q, df_ratio_q = None, None, None, None

        roic_ttm = 0
        cfo_quality_ttm = 0
        de_current = 0
        pb_current = 0
        
        equity_q_val = get_latest_q_value(df_bs_q, ["của công ty mẹ", "Vốn chủ sở hữu", "Equity"]) if df_bs_q is not None else 0
        if equity_q_val == 0 and df_bs is not None:
            equity_q_val = get_row_value(df_bs, ["của công ty mẹ", "Vốn chủ sở hữu", "Equity"], str(latest_year))

        if market_cap_overview > 0 and equity_q_val > 0:
            mc = market_cap_overview * 1e9 if market_cap_overview < 1000000 else market_cap_overview
            pb_current = mc / equity_q_val
        else:
            if df_ratio_q is not None and not df_ratio_q.empty:
                pb_q = get_latest_q_value(df_ratio_q, ["P/B", "giá trị sổ sách (P/B)"])
                if pb_q:
                    pb_current = float(pb_q)
            if pb_current == 0 and history:
                pb_current = 1 / history[-1]['bp'] if history[-1]['bp'] > 0 else 0

        latest_q_str = ""
        if df_is_q is not None and not df_is_q.empty and df_bs_q is not None and not df_bs_q.empty:
            latest_q_str = get_latest_quarter_str(df_is_q, ["Lãi/(lỗ) từ hoạt động kinh doanh", "Lợi nhuận thuần từ hoạt động kinh doanh", "Operating profit"])
            ebt_ttm = get_ttm_value(df_is_q, ["Lãi/(lỗ) trước thuế", "Tổng lợi nhuận kế toán trước thuế", "Lợi nhuận trước thuế", "Profit before tax"])
            tax_ttm = get_ttm_value(df_is_q, ["thuế thu nhập doanh nghiệp", "Income tax expense"])
            ni_ttm = get_ttm_value(df_is_q, ["Lãi/(lỗ) thuần sau thuế", "Lợi nhuận của Cổ đông của Công ty mẹ", "Lợi nhuận sau thuế", "Net income"])
            ebit_ttm = get_ttm_value(df_is_q, ["Lãi/(lỗ) từ hoạt động kinh doanh", "Lợi nhuận thuần từ hoạt động kinh doanh", "Operating profit"])
            if ebit_ttm == 0: ebit_ttm = ebt_ttm
            
            interest_ttm = get_ttm_value(df_is_q, ["Chi phí lãi vay", "Interest expense"])
            if interest_ttm != 0:
                current_icr = ebit_ttm / abs(interest_ttm)
            elif df_ratio_q is not None and not df_ratio_q.empty:
                icr_q = get_latest_q_value(df_ratio_q, ["Khả năng thanh toán lãi vay", "ICR"])
                if icr_q: current_icr = float(icr_q)
                
            cfo_ttm = get_ttm_value(df_cf_q, ["Lưu chuyển tiền tệ ròng từ các hoạt động sản xuất kinh doanh", "Lưu chuyển tiền thuần từ hoạt động kinh doanh", "Net cash flows from operating activities"]) if df_cf_q is not None else 0
            tax_rate_ttm = tax_ttm / ebt_ttm if ebt_ttm > 0 else tax_rate_fallback
            tax_rate_ttm = max(0.0, min(0.22, tax_rate_ttm))
            equity_q = get_latest_q_value(df_bs_q, ["Vốn chủ sở hữu", "Equity"])
            debt_q = get_latest_q_value(df_bs_q, ["Nợ phải trả", "Liabilities", "Tổng nợ"])
            cash_q = get_latest_q_value(df_bs_q, ["Tiền và tương đương tiền", "Tiền và các khoản tương đương tiền", "Cash and cash equivalents"])
            invested_capital_q = equity_q + debt_q - cash_q
            if invested_capital_q > 0: roic_ttm = (ebit_ttm * (1 - tax_rate_ttm)) / invested_capital_q
            if equity_q > 0: de_current = debt_q / equity_q
            if ni_ttm != 0: cfo_quality_ttm = cfo_ttm / ni_ttm

        return {
            'ticker': ticker,
            'company_name': company_name,
            'sector': sector,
            'summary': {
                'ROIC_5Y': avg_roic_5y,
                'Value_Ratio': value_ratio,
                'BP_5Y': avg_bp,
                'ED_5Y': avg_ed_5y,
                'CFO_Quality': cfo_quality,
                'DE_5Y': avg_de_5y,
                'ICR_Current': current_icr,
                'ROIC_TTM': roic_ttm,
                'CFO_Quality_TTM': cfo_quality_ttm,
                'DE_Current': de_current,
                'PB_Current': pb_current,
                'Current_Price': float(current_price) if current_price else 0,
                'Latest_Quarter': latest_q_str,
                'Latest_Year': str(history[-1]['year']) if history else ""
            },
            'history': history
        }
    except Exception as e:
        try:
            print(f"Loi khi lay du lieu cho {ticker}: {str(e)[:50]}...")
        except:
            pass
        return None

def get_sector_medians(sector):
    if not sector: return {}
    import os, json
    from datetime import datetime
    
    CACHE_DIR = "cache"
    safe_sector = "".join([c if c.isalnum() else "_" for c in sector])
    today = datetime.now().strftime("%Y-%m-%d")
    medians_cache_file = os.path.join(CACHE_DIR, f"medians_{safe_sector}_{today}.json")
    
    if os.path.exists(medians_cache_file):
        try:
            with open(medians_cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
            
    # Nếu chưa có cache, không gọi đồng bộ để tránh sập RAM trên Render.
    # Cache sẽ được tạo ngầm thông qua background tasks hoặc cron job.
    # run_screener_for_sector(sector)
    
    if os.path.exists(medians_cache_file):
        try:
            with open(medians_cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}

def get_comparative_report(main_ticker, peers_str="", tax_rate_fallback=0.2):
    import re
    import numpy as np
    import pandas as pd
    tickers = [main_ticker]
    if peers_str:
        peer_list = [p.strip().upper() for p in re.split(r'[,\s]+', peers_str) if p.strip()]
        for p in peer_list:
            if p not in tickers:
                tickers.append(p)
                
    reports = {}
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future_to_ticker = {executor.submit(get_stock_report, t, tax_rate_fallback): t for t in tickers}
        for future in concurrent.futures.as_completed(future_to_ticker):
            t = future_to_ticker[future]
            try:
                rep = future.result()
                if rep:
                    reports[t] = rep
            except Exception as exc:
                print(f"Loi khi lấy {t} song song: {exc}")
            
    if main_ticker not in reports:
        return {'status': 'error', 'detail': f'Không tìm thấy dữ liệu cho mã chính {main_ticker}'}
        
    rank_data = []
    is_bank = False
    is_securities = False
    for t, rep in reports.items():
        summary = rep['summary']
        if rep['sector'].lower() in ['ngân hàng', 'banks']:
            is_bank = True
            rank_data.append({
                'ticker': t,
                'ROA_Current': summary.get('ROA_Current', 0),
                'ROE_Current': summary.get('ROE_Current', 0),
                'NIM_Current': summary.get('NIM_Current', 0),
                'PB_Current': summary.get('PB_Current', 0),
                'Value_Ratio_Current': summary.get('Value_Ratio_Current', 0),
                'Equity_Ratio_Current': summary.get('Equity_Ratio_Current', 0),
                'Current_Price': summary.get('Current_Price', 0)
            })
        elif rep['sector'].lower() in ['chứng khoán', 'securities', 'dịch vụ tài chính', 'dịch vụ tài chính (mở rộng)', 'financial services']:
            is_securities = True
            rank_data.append({
                'ticker': t,
                'PB_Current': summary.get('PB_Current', 0),
                'PE_Current': summary.get('PE_Current', 0),
                'ROE_TTM': summary.get('ROE_TTM', 0),
                'ROE_5Y': summary.get('ROE_5Y', 0),
                'Equity_Ratio_Current': summary.get('Equity_Ratio_Current', 0),
                'Current_Price': summary.get('Current_Price', 0)
            })
        else:
            rank_data.append({
                'ticker': t,
                'ROIC_5Y': summary.get('ROIC_5Y', 0),
                'ROIC_TTM': summary.get('ROIC_TTM', 0),
                'Value_Ratio': summary.get('Value_Ratio', 0),
                'CFO_Quality': summary.get('CFO_Quality', 0),
                'CFO_Quality_TTM': summary.get('CFO_Quality_TTM', 0),
                'DE_5Y': summary.get('DE_5Y', 0),
                'DE_Current': summary.get('DE_Current', 0),
                'PB_Current': summary.get('PB_Current', 0),
                'BP_5Y': summary.get('BP_5Y', 0),
                'Current_Price': summary.get('Current_Price', 0)
            })
    
    df_rank = pd.DataFrame(rank_data)
    if not df_rank.empty:
        # Lấy median của sector từ main_ticker
        main_sector = reports[main_ticker]['sector'] if main_ticker in reports else ""
        medians = get_sector_medians(main_sector)
        
        if is_bank:
            m_roa = medians.get('median_roa', 0.02)
            m_nim = medians.get('median_nim', 0.035)
            m_value = medians.get('median_value', 10.0)
            m_eq = medians.get('median_eq', 0.1)
            
            df_rank['Score_ROA'] = (df_rank['ROA_Current'] / m_roa) * 100
            df_rank['Score_NIM'] = (df_rank['NIM_Current'].clip(upper=0.045) / m_nim) * 100
            df_rank['Score_Value'] = (df_rank['Value_Ratio_Current'] / m_value) * 100
            df_rank['Score_EQ'] = (df_rank['Equity_Ratio_Current'] / m_eq) * 100
            df_rank['Total_Score'] = (df_rank['Score_Value'] * 0.30) + (df_rank['Score_EQ'] * 0.25) + (df_rank['Score_ROA'] * 0.25) + (df_rank['Score_NIM'] * 0.20)
        elif is_securities:
            m_pb = medians.get('median_pb', 1.5)
            m_pe = medians.get('median_pe', 15.0)
            m_roe = medians.get('median_roe_ttm', 0.1)
            m_roe5 = medians.get('median_roe_5y', 0.1)
            m_eq = medians.get('median_eq', 0.3)
            
            df_rank['Score_PB'] = np.where(df_rank['PB_Current'] > 0, (m_pb / df_rank['PB_Current']) * 100, 0)
            df_rank['Score_PE'] = np.where(df_rank['PE_Current'] > 0, (m_pe / df_rank['PE_Current']) * 100, 0)
            df_rank['Score_ROE_TTM'] = (df_rank['ROE_TTM'] / m_roe) * 100
            df_rank['Score_ROE_5Y'] = (df_rank['ROE_5Y'] / m_roe5) * 100
            df_rank['Score_EQ'] = (df_rank['Equity_Ratio_Current'] / m_eq) * 100
            
            df_rank['Total_Score'] = (df_rank['Score_PB'] * 0.30) + (df_rank['Score_PE'] * 0.20) + \
                                     (df_rank['Score_ROE_TTM'] * 0.20) + (df_rank['Score_ROE_5Y'] * 0.15) + \
                                     (df_rank['Score_EQ'] * 0.15)
        else:
            m_roic = medians.get('median_roic', 0.10)
            m_roic_ttm = medians.get('median_roic_ttm', 0.10)
            m_value = medians.get('median_value', 10.0)
            m_cfo = medians.get('median_cfo', 1.0)
            m_cfo_ttm = medians.get('median_cfo_ttm', 1.0)
            m_de = medians.get('median_de', 1.0)
            m_de_curr = medians.get('median_de_curr', 1.0)

            df_rank['Score_ROIC'] = (df_rank['ROIC_5Y'] / m_roic) * 100
            df_rank['Score_ROIC_TTM'] = (df_rank['ROIC_TTM'] / m_roic_ttm) * 100
            df_rank['Score_Value'] = (df_rank['Value_Ratio'] / m_value) * 100
            
            df_rank['Score_CFO'] = (df_rank['CFO_Quality'] / m_cfo) * 100
            df_rank.loc[df_rank['CFO_Quality'] < 0, 'Score_CFO'] = 0
            df_rank['Score_CFO_TTM'] = (df_rank['CFO_Quality_TTM'] / m_cfo_ttm) * 100
            df_rank.loc[df_rank['CFO_Quality_TTM'] < 0, 'Score_CFO_TTM'] = 0
            
            df_rank['Score_DE'] = np.maximum(0, 2 - (df_rank['DE_5Y'] / m_de)) * 100
            df_rank['Score_DE_Current'] = np.maximum(0, 2 - (df_rank['DE_Current'] / m_de_curr)) * 100
            
            df_rank['Total_Score'] = (df_rank['Score_ROIC'] * 0.15) + (df_rank['Score_ROIC_TTM'] * 0.25) + \
                                     (df_rank['Score_Value'] * 0.20) + \
                                     (df_rank['Score_CFO'] * 0.10) + (df_rank['Score_CFO_TTM'] * 0.15) + \
                                     (df_rank['Score_DE'] * 0.05) + (df_rank['Score_DE_Current'] * 0.10)
        
        df_rank = df_rank.fillna(0)
        df_rank = df_rank.sort_values(by='Total_Score', ascending=False)
        ranking = df_rank.to_dict('records')
    else:
        ranking = []
        
    result_dict = {
        'status': 'success',
        'main_ticker': main_ticker,
        'reports': reports,
        'ranking': ranking
    }
    
    import math
    def sanitize(obj):
        import math
        import pandas as pd
        import numpy as np
        
        if isinstance(obj, dict):
            return {k: sanitize(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [sanitize(v) for v in obj]
            
        if isinstance(obj, bool):
            return obj
            
        try:
            if pd.isna(obj):
                return 0
        except Exception:
            pass
            
        try:
            if isinstance(obj, (float, np.floating)):
                if np.isinf(obj) or np.isnan(obj):
                    return 0
                return float(obj)
            elif isinstance(obj, (int, np.integer)):
                return int(obj)
        except Exception:
            pass
            
        return obj
        
    return sanitize(result_dict)
