import pandas as pd
import numpy as np
import time
import warnings

# Suppress warnings
warnings.filterwarnings('ignore')

import os
os.environ["CODESPACE_NAME"] = "render_bypass" # Fix bug hosting_service của vnstock trên server Render
from vnstock import Listing, Finance, Vnstock, Company, Quote

def with_retry(func):
    def wrapper(*args, **kwargs):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                print(f"Lỗi truy xuất API ({e}). Đợi 10s để thử lại (Lần {attempt+1}/{max_retries})...")
                time.sleep(10)
        return func(*args, **kwargs)
    return wrapper

Finance.ratio = with_retry(Finance.ratio)
Finance.balance_sheet = with_retry(Finance.balance_sheet)
Finance.income_statement = with_retry(Finance.income_statement)
Finance.cash_flow = with_retry(Finance.cash_flow)
Company.overview = with_retry(Company.overview)

import threading
USER_PRIORITY_FLAG = threading.Event()
_QUOTE_HISTORY_CACHE = {}
_QUOTE_HISTORY_CACHE_LOCK = threading.RLock()
_VALUATION_ASSUMPTION_CACHE = {}
_VALUATION_ASSUMPTION_CACHE_LOCK = threading.RLock()

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


def _optional_row_value(df, keywords, period_col):
    """Return a statement value or None when the row/period is unavailable."""
    if df is None or getattr(df, 'empty', True) or period_col is None:
        return None
    if isinstance(keywords, str):
        keywords = [keywords]
    try:
        item_col = df.columns[0]
        for keyword in keywords:
            matches = df[df[item_col].astype(str).str.contains(keyword, case=False, na=False, regex=False)]
            exact = matches[matches[item_col].astype(str).str.strip().str.casefold() == keyword.strip().casefold()]
            ordered = pd.concat([exact, matches[~matches.index.isin(exact.index)]])
            for _, row in ordered.iterrows():
                value = row.get(period_col)
                if pd.isna(value) or str(value).strip() == '':
                    continue
                try:
                    number = float(value)
                    if np.isfinite(number):
                        return number
                except (TypeError, ValueError):
                    continue
    except Exception:
        pass
    return None


def _period_column(df, year):
    if df is None or getattr(df, 'empty', True):
        return None
    year = str(year)
    for column in df.columns:
        label = str(column)
        if label == year or (label.startswith(year + '-') and '-Q' not in label.upper()):
            return column
    return None


def _quarter_columns(df):
    if df is None or getattr(df, 'empty', True):
        return []
    columns = [column for column in df.columns if '-Q' in str(column).upper()]
    return sorted(columns, key=lambda column: str(column), reverse=True)


def _market_cap_to_vnd(value):
    """Normalize VCI overview market cap to VND, matching the existing P/B logic."""
    try:
        value = float(value)
        if not np.isfinite(value) or value <= 0:
            return None
        return value * 1e9 if value < 1_000_000 else value
    except (TypeError, ValueError):
        return None


def _read_interest_bearing_debt(df, period_col):
    short_debt = _optional_row_value(df, [
        'Vay và nợ thuê tài chính ngắn hạn', 'Vay ngắn hạn',
        'Nợ vay ngắn hạn', 'Short-term borrowings'
    ], period_col)
    long_debt = _optional_row_value(df, [
        'Vay và nợ thuê tài chính dài hạn', 'Vay dài hạn',
        'Nợ vay dài hạn', 'Long-term borrowings'
    ], period_col)
    if short_debt is not None and long_debt is not None:
        return short_debt + long_debt, short_debt
    total_debt = _optional_row_value(df, [
        'Tổng vay và nợ thuê tài chính', 'Tổng nợ vay',
        'Total interest-bearing debt', 'Total borrowings'
    ], period_col)
    return total_debt, short_debt


def _build_nonfinancial_valuation_inputs(df_is, df_cf, df_bs, years_cols,
                                        market_cap, current_price, tax_rate_fallback,
                                        df_is_q=None, df_bs_q=None):
    """Build historical FCFF inputs and capital structure from raw statements.

    Missing statement rows remain null so the UI can distinguish unavailable data
    from genuine zero values.
    """
    import re
    raw_years = {}
    for column in years_cols:
        if '-Q' in str(column).upper():
            continue
        match = re.search(r'20\d{2}', str(column))
        if match:
            raw_years[int(match.group(0))] = str(match.group(0))
    years = sorted(raw_years)[-5:]
    fallback_tax_rate = tax_rate_fallback if tax_rate_fallback is not None and 0 <= tax_rate_fallback <= 1 else None

    annual = []
    for year in years:
        year_str = str(year)
        is_col = _period_column(df_is, year_str) or year_str
        cf_col = _period_column(df_cf, year_str)
        bs_col = _period_column(df_bs, year_str)

        ebit = _optional_row_value(df_is, [
            'Lợi nhuận thuần từ hoạt động kinh doanh',
            'Lãi/(lỗ) từ hoạt động kinh doanh',
            'Operating profit', 'Profit from operating activities'
        ], is_col)
        ebt = _optional_row_value(df_is, [
            'Lãi/(lỗ) trước thuế', 'Tổng lợi nhuận kế toán trước thuế',
            'Lợi nhuận trước thuế', 'Profit before tax'
        ], is_col)
        net_income = _optional_row_value(df_is, [
            'Lợi nhuận sau thuế của cổ đông công ty mẹ',
            'Lãi/(lỗ) thuần sau thuế', 'Lợi nhuận sau thuế', 'Net income'
        ], is_col)
        tax_expense = _optional_row_value(df_is, [
            'Tổng chi phí thuế thu nhập doanh nghiệp',
            'Income tax expense'
        ], is_col)
        if tax_expense is None:
            current_tax = _optional_row_value(df_is, [
                'Chi phí thuế thu nhập doanh nghiệp hiện hành', 'Current income tax'
            ], is_col)
            deferred_tax = _optional_row_value(df_is, [
                'Chi phí thuế thu nhập doanh nghiệp hoãn lại', 'Deferred income tax'
            ], is_col)
            if current_tax is not None or deferred_tax is not None:
                tax_expense = (current_tax or 0) + (deferred_tax or 0)

        effective_tax = tax_expense / ebt if tax_expense is not None and ebt and ebt > 0 else None
        if effective_tax is not None and not 0 <= effective_tax <= 1:
            effective_tax = None
        tax_for_fcff = effective_tax if effective_tax is not None else fallback_tax_rate
        tax_basis = 'reported_effective_rate' if effective_tax is not None else ('user_tax_input_fallback' if fallback_tax_rate is not None else None)

        da = _optional_row_value(df_cf, [
            'Khấu hao tài sản cố định và bất động sản đầu tư',
            'Khấu hao tài sản cố định', 'Khấu hao TSCĐ', 'Khấu hao và phân bổ', 'Khấu hao',
            'Depreciation and amortisation', 'Depreciation and amortization',
            'Depreciation', 'Amortization'
        ], cf_col)
        capex = _optional_row_value(df_cf, [
            'Tiền chi để mua sắm, xây dựng tài sản cố định',
            'Tiền chi để mua sắm, xây dựng TSCĐ',
            'Chi mua sắm tài sản cố định', 'Chi mua sắm TSCĐ',
            'Mua sắm, xây dựng tài sản cố định',
            'Purchase and construction of fixed assets',
            'Payments for purchase or construction of fixed assets'
        ], cf_col)
        if da is not None:
            da = abs(da)
        if capex is not None:
            capex = abs(capex)

        current_assets = _optional_row_value(df_bs, [
            'Tổng cộng tài sản ngắn hạn', 'Tổng tài sản ngắn hạn',
            'Tài sản ngắn hạn', 'Current assets'
        ], bs_col)
        current_liabilities = _optional_row_value(df_bs, [
            'Tổng nợ ngắn hạn', 'Nợ ngắn hạn', 'Current liabilities'
        ], bs_col)
        cash = _optional_row_value(df_bs, [
            'Tiền và các khoản tương đương tiền', 'Tiền và tương đương tiền',
            'Cash and cash equivalents'
        ], bs_col)
        short_investments = _optional_row_value(df_bs, [
            'Đầu tư tài chính ngắn hạn', 'Short-term investments'
        ], bs_col)
        interest_bearing_debt, short_debt = _read_interest_bearing_debt(df_bs, bs_col)

        nwc = None
        nwc_missing_inputs = [
            key for key, value in (
                ('current_assets', current_assets), ('cash', cash),
                ('short_term_investments', short_investments),
                ('current_liabilities', current_liabilities), ('short_term_debt', short_debt)
            ) if value is None
        ]
        if not nwc_missing_inputs:
            operating_current_assets = current_assets - cash - short_investments
            operating_current_liabilities = current_liabilities - short_debt
            nwc = operating_current_assets - operating_current_liabilities

        nopat = ebit * (1 - tax_for_fcff) if ebit is not None and tax_for_fcff is not None else None
        annual.append({
            'year': year,
            'ebit': ebit,
            'net_income': net_income,
            'tax_expense': tax_expense,
            'effective_tax_rate': effective_tax,
            'tax_rate_used_for_fcff': tax_for_fcff,
            'tax_rate_basis': tax_basis,
            'da': da,
            'capex': capex,
            'cash': cash,
            'interest_bearing_debt': interest_bearing_debt,
            'nwc': nwc,
            'nwc_missing_inputs': nwc_missing_inputs,
            'delta_nwc': None,
            'nopat': nopat,
            'fcff': None,
            'fcff_missing_inputs': []
        })

    by_year = {row['year']: row for row in annual}
    for row in annual:
        previous = by_year.get(row['year'] - 1)
        if row['nwc'] is not None and previous and previous['nwc'] is not None:
            row['delta_nwc'] = row['nwc'] - previous['nwc']
        missing = [key for key in ('ebit', 'da', 'capex', 'delta_nwc', 'nopat') if row[key] is None]
        row['fcff_missing_inputs'] = missing
        if not missing:
            row['fcff'] = row['nopat'] + row['da'] - row['capex'] - row['delta_nwc']

    latest = annual[-1] if annual else {}
    prior = annual[-2] if len(annual) > 1 else {}
    latest_interest = None
    latest_interest_year = None
    for year in reversed(years):
        col = _period_column(df_is, str(year)) or str(year)
        interest = _optional_row_value(df_is, ['Chi phí lãi vay', 'Interest expense'], col)
        if interest is not None:
            latest_interest = abs(interest)
            latest_interest_year = year
            break

    q_cols = _quarter_columns(df_bs_q)
    latest_q_col = q_cols[0] if q_cols else None
    comparable_q_col = q_cols[4] if len(q_cols) > 4 else None
    quarter_debt_now = quarter_debt_prev = quarter_cash = None
    if latest_q_col:
        quarter_debt_now, _ = _read_interest_bearing_debt(df_bs_q, latest_q_col)
        quarter_cash = _optional_row_value(df_bs_q, [
            'Tiền và các khoản tương đương tiền', 'Tiền và tương đương tiền',
            'Cash and cash equivalents'
        ], latest_q_col)
        if comparable_q_col:
            quarter_debt_prev, _ = _read_interest_bearing_debt(df_bs_q, comparable_q_col)

    debt_now = quarter_debt_now if quarter_debt_now is not None else latest.get('interest_bearing_debt')
    debt_prev = quarter_debt_prev if quarter_debt_prev is not None else prior.get('interest_bearing_debt')
    if df_is_q is not None and not df_is_q.empty:
        interest_ttm = get_ttm_value(df_is_q, ['Chi phí lãi vay', 'Interest expense'])
        if interest_ttm:
            latest_interest = abs(interest_ttm)
            latest_interest_year = 'TTM'

    average_debt = None
    if debt_now is not None and debt_prev is not None:
        average_debt = (debt_now + debt_prev) / 2
    elif debt_now is not None:
        average_debt = debt_now
    cost_of_debt = latest_interest / average_debt if latest_interest is not None and average_debt and average_debt > 0 else None

    market_equity = _market_cap_to_vnd(market_cap)
    current_cash = quarter_cash if quarter_cash is not None else latest.get('cash')
    shares_estimate = None
    try:
        if market_equity and current_price and float(current_price) > 0:
            shares_estimate = market_equity / float(current_price)
    except (TypeError, ValueError):
        pass

    return {
        'model': 'fcff',
        'status': 'partial',
        'currency': 'VND',
        'amount_unit': 'VND',
        'financial_statement_source': 'Vnstock VCI',
        'history': annual,
        'capital_structure': {
            'market_equity_value': market_equity,
            'interest_bearing_debt': debt_now,
            'debt_as_of_period': latest_q_col if quarter_debt_now is not None else (str(latest.get('year')) if debt_now is not None else None),
            'cash_and_equivalents': current_cash,
            'cash_as_of_period': latest_q_col if quarter_cash is not None else (str(latest.get('year')) if current_cash is not None else None),
            'net_debt': debt_now - current_cash if debt_now is not None and current_cash is not None else None,
            'current_share_price': float(current_price) if current_price is not None and float(current_price) > 0 else None,
            'shares_outstanding_estimate': shares_estimate,
            'shares_estimate_basis': 'market_cap_divided_by_current_price' if shares_estimate is not None else None,
            'interest_expense': latest_interest,
            'interest_expense_year': latest_interest_year,
            'average_interest_bearing_debt': average_debt,
            'cost_of_debt': cost_of_debt,
            'cost_of_debt_basis': 'Lãi vay TTM ÷ nợ vay chịu lãi bình quân' if cost_of_debt is not None else None
        },
        'wacc': {
            'risk_free_rate': None,
            'equity_risk_premium': None,
            'beta': None,
            'cost_of_equity': None,
            'tax_rate': None,
            'equity_weight': None,
            'debt_weight': None,
            'value': None,
            'missing_inputs': ['beta', 'risk_free_rate', 'equity_risk_premium', 'market_equity_value', 'interest_bearing_debt'],
            'status': 'not_calculated'
        },
        'sources': {
            'risk_free_rate': 'HNX Vietnam Government Bond 10Y yield; auto through Vnstock Macro when available, otherwise enter in the report controls',
            'equity_risk_premium': 'Automatically fetched from Damodaran current workbook as Vietnam rating-based total ERP; manual override is optional',
            'beta': 'Calculated from 3-year daily ticker returns against VNINDEX'
        }
    }


def _quote_close_series(symbol):
    """Get a cached daily close series, trying the supported VCI and KBS feeds."""
    from datetime import datetime, timedelta
    import pandas as pd

    now = time.time()
    with _QUOTE_HISTORY_CACHE_LOCK:
        cached = _QUOTE_HISTORY_CACHE.get(symbol)
        if cached and now - cached['fetched_at'] < 3600:
            return cached['series'].copy()

    end = datetime.now().strftime('%Y-%m-%d')
    start = (datetime.now() - timedelta(days=365 * 3 + 10)).strftime('%Y-%m-%d')
    for source in ('VCI', 'KBS'):
        try:
            frame = Quote(source=source, symbol=symbol).history(start=start, end=end, interval='1D')
            if frame is None or frame.empty:
                continue
            columns = {str(col).lower(): col for col in frame.columns}
            date_col = next((columns[key] for key in ('time', 'date', 'trading_date') if key in columns), None)
            price_col = next((columns[key] for key in ('adj_close', 'close', 'close_price') if key in columns), None)
            if date_col is None or price_col is None:
                continue
            series = pd.Series(pd.to_numeric(frame[price_col], errors='coerce').values,
                               index=pd.to_datetime(frame[date_col], errors='coerce').dt.normalize())
            series = series[~series.index.isna()].dropna().groupby(level=0).last().sort_index()
            if len(series) < 2:
                continue
            with _QUOTE_HISTORY_CACHE_LOCK:
                _QUOTE_HISTORY_CACHE[symbol] = {'fetched_at': time.time(), 'series': series}
            return series.copy()
        except Exception as exc:
            print(f'Không lấy được lịch sử giá {symbol} từ {source}: {str(exc)[:120]}')
    return None


def _calculate_market_beta(ticker):
    """Estimate beta from overlapping daily returns; never substitute a fixed beta."""
    try:
        import pandas as pd
        stock = _quote_close_series(ticker)
        market = _quote_close_series('VNINDEX')
        if stock is None or market is None:
            return None
        returns = pd.concat([stock.pct_change(), market.pct_change()], axis=1, join='inner').dropna()
        returns = returns.replace([np.inf, -np.inf], np.nan).dropna()
        if len(returns) < 60 or returns.iloc[:, 1].var() <= 0:
            return None
        beta = returns.iloc[:, 0].cov(returns.iloc[:, 1]) / returns.iloc[:, 1].var()
        return float(beta) if np.isfinite(beta) else None
    except Exception as exc:
        print(f'Không tính được beta cho {ticker}: {str(exc)[:120]}')
        return None


def _fetch_damodaran_erp():
    """Fetch Vietnam's rating-based total ERP from Damodaran's current workbook."""
    import requests
    from io import BytesIO
    from openpyxl import load_workbook
    from datetime import datetime

    cache_key = 'damodaran_vietnam_total_erp'
    now = time.time()
    with _VALUATION_ASSUMPTION_CACHE_LOCK:
        cached = _VALUATION_ASSUMPTION_CACHE.get(cache_key)
        if cached and now - cached['fetched_at'] < (86400 if cached.get('value') is not None else 1800):
            return cached.get('value'), cached.get('as_of')

    try:
        response = requests.get(
            'https://pages.stern.nyu.edu/~adamodar/pc/datasets/ctryprem.xlsx',
            timeout=8
        )
        response.raise_for_status()
        workbook = load_workbook(BytesIO(response.content), read_only=True, data_only=True)
        sheet = workbook['ERPs by country']
        rows = sheet.iter_rows(values_only=True)
        header = None
        data_rows = []
        for row in rows:
            if header is None and row and any(str(value).strip() == 'Country' for value in row if value is not None):
                header = list(row)
                continue
            if header is not None:
                data_rows.append(row)
        country_col = next(i for i, value in enumerate(header) if str(value).strip() == 'Country')
        erp_col = next(i for i, value in enumerate(header) if str(value).strip() == 'Total Equity Risk Premium')
        vietnam_row = next(row for row in data_rows if str(row[country_col]).strip().casefold() == 'vietnam')
        value = float(vietnam_row[erp_col])

        as_of = None
        update_sheet = workbook['ERPs by country']
        update_date = update_sheet.cell(row=2, column=2).value
        if isinstance(update_date, datetime):
            as_of = update_date.date().isoformat()
        elif update_date:
            as_of = str(update_date)

        result = (value, as_of)
    except Exception as exc:
        print(f'Không tải được ERP Damodaran: {str(exc)[:160]}')
        result = (None, None)

    with _VALUATION_ASSUMPTION_CACHE_LOCK:
        _VALUATION_ASSUMPTION_CACHE[cache_key] = {
            'fetched_at': time.time(), 'value': result[0], 'as_of': result[1]
        }
    return result


def _fetch_vn_10y_risk_free_rate():
    """Use Vnstock's Macro route when installed; older versions need manual HNX input."""
    try:
        from vnstock import Macro
        macro = Macro()
        global_macro = getattr(macro, 'global_macro', None) or getattr(macro, 'world', None)
        if global_macro is None:
            return None, None
        frame = global_macro.bond_yield(market='VN', tenor='10Y', length='30D')
        if frame is None or frame.empty:
            return None, None
        columns = {str(col).lower(): col for col in frame.columns}
        value_col = next((columns[key] for key in ('close', 'yield', 'value') if key in columns), None)
        date_col = next((columns[key] for key in ('time', 'date') if key in columns), None)
        if value_col is None:
            return None, None
        values = pd.to_numeric(frame[value_col], errors='coerce').dropna()
        if values.empty:
            return None, None
        value = float(values.iloc[-1])
        if value > 1:
            value /= 100
        as_of = str(frame.iloc[-1][date_col])[:10] if date_col else None
        return (value, as_of) if 0 <= value <= 1 else (None, None)
    except ImportError:
        return None, None
    except Exception as exc:
        print(f'Không tự lấy được lợi suất TPCP Việt Nam 10Y: {str(exc)[:160]}')
        return None, None


def _estimate_historical_fcff_cagr(history, minimum_points=2):
    """Estimate CAGR from valid positive FCFF points, allowing missing years."""
    valid_points = []
    for row in sorted(history or [], key=lambda item: item.get('year') or 0):
        try:
            year = int(row.get('year'))
            fcff = float(row.get('fcff'))
        except (TypeError, ValueError):
            continue
        if np.isfinite(fcff) and fcff > 0:
            valid_points.append({'year': year, 'fcff': fcff})

    if len(valid_points) == 1:
        year = valid_points[0]['year']
        return {
            'rate': 0.0, 'source': 'flat_fcff_fallback',
            'start_year': year, 'end_year': year, 'points': 1
        }
    if len(valid_points) < minimum_points:
        return {
            'rate': None, 'source': 'unavailable',
            'start_year': None, 'end_year': None, 'points': len(valid_points)
        }
    first, last = valid_points[0], valid_points[-1]
    periods = last['year'] - first['year']
    if periods <= 0:
        return {
            'rate': None, 'source': 'unavailable',
            'start_year': None, 'end_year': None, 'points': len(valid_points)
        }
    rate = (last['fcff'] / first['fcff']) ** (1 / periods) - 1
    if not np.isfinite(rate):
        rate = None
    return {
        'rate': rate,
        'source': 'historical_fcff_cagr' if rate is not None else 'unavailable',
        'start_year': first['year'],
        'end_year': last['year'],
        'points': len(valid_points)
    }


def _calculate_wacc_inputs(valuation, ticker, risk_free_rate, equity_risk_premium, tax_rate,
                           forecast_growth_rate=None, terminal_growth_rate=None):
    if not valuation or valuation.get('model') != 'fcff':
        return
    for name, rate in (('forecast_growth_rate', forecast_growth_rate),
                       ('terminal_growth_rate', terminal_growth_rate)):
        if rate is not None and not np.isfinite(rate):
            if name == 'forecast_growth_rate':
                forecast_growth_rate = None
            else:
                terminal_growth_rate = None
    risk_free_as_of = None
    risk_free_source = 'HNX 10Y yield entered manually'
    if risk_free_rate is None:
        risk_free_rate, risk_free_as_of = _fetch_vn_10y_risk_free_rate()
        if risk_free_rate is not None:
            risk_free_source = 'Vnstock Macro, Vietnam Government Bond 10Y'
    else:
        risk_free_source = 'User-provided HNX 10Y override'

    erp_as_of = None
    erp_source = 'Damodaran current country-premium workbook (rating-based total ERP)'
    if equity_risk_premium is None:
        equity_risk_premium, erp_as_of = _fetch_damodaran_erp()
    else:
        erp_source = 'User-provided ERP override'

    if risk_free_rate is not None and not 0 <= risk_free_rate <= 1:
        risk_free_rate = None
    if equity_risk_premium is not None and not 0 <= equity_risk_premium <= 1:
        equity_risk_premium = None
    beta = _calculate_market_beta(ticker)
    capital = valuation.get('capital_structure', {})
    wacc = valuation.get('wacc', {})
    market_equity = capital.get('market_equity_value')
    debt = capital.get('interest_bearing_debt')
    cost_of_debt = capital.get('cost_of_debt')
    usable_tax = tax_rate if tax_rate is not None and 0 <= tax_rate <= 1 else None

    cost_of_equity = None
    if risk_free_rate is not None and equity_risk_premium is not None and beta is not None:
        cost_of_equity = risk_free_rate + beta * equity_risk_premium

    equity_weight = debt_weight = None
    if market_equity is not None and debt is not None and market_equity + debt > 0:
        total_capital = market_equity + debt
        equity_weight = market_equity / total_capital
        debt_weight = debt / total_capital

    value = None
    if equity_weight is not None and cost_of_equity is not None and usable_tax is not None:
        if debt_weight == 0:
            value = cost_of_equity
        elif cost_of_debt is not None:
            value = equity_weight * cost_of_equity + debt_weight * cost_of_debt * (1 - usable_tax)

    missing = []
    for key, item in (
        ('beta', beta), ('risk_free_rate', risk_free_rate),
        ('equity_risk_premium', equity_risk_premium),
        ('market_equity_value', market_equity), ('interest_bearing_debt', debt),
        ('tax_rate', usable_tax)
    ):
        if item is None:
            missing.append(key)
    if debt not in (None, 0) and cost_of_debt is None:
        missing.append('cost_of_debt')

    wacc.update({
        'beta': beta,
        'risk_free_rate': risk_free_rate,
        'equity_risk_premium': equity_risk_premium,
        'cost_of_equity': cost_of_equity,
        'tax_rate': usable_tax,
        'equity_weight': equity_weight,
        'debt_weight': debt_weight,
        'value': value,
        'missing_inputs': missing,
        'status': 'ready' if value is not None else 'partial',
        'tax_rate_basis': 'user_tax_rate_input' if usable_tax is not None else None,
        'risk_free_rate_source': risk_free_source,
        'risk_free_rate_as_of': risk_free_as_of,
        'equity_risk_premium_source': erp_source,
        'equity_risk_premium_as_of': erp_as_of
    })
    valuation['status'] = 'ready' if value is not None else 'partial'

    history = valuation.get('history', [])
    historical_growth = _estimate_historical_fcff_cagr(history)
    historical_growth_rate = historical_growth['rate']
    forecast_growth_source = 'user_input' if forecast_growth_rate is not None else historical_growth['source']
    terminal_growth_source = 'user_input' if terminal_growth_rate is not None else historical_growth['source']
    base_row = next((row for row in reversed(history)
                     if isinstance(row.get('fcff'), (int, float))
                     and np.isfinite(row['fcff']) and row['fcff'] > 0), None)
    base_fcff_assumptions = []
    if base_row is None:
        # Keep a clearly labeled fallback for reports missing only D&A and/or ΔNWC.
        # These inputs are assumed to be zero for this scenario, never written back as historical data.
        for row in reversed(history):
            nopat = row.get('nopat')
            capex = row.get('capex')
            if not all(isinstance(item, (int, float)) and np.isfinite(item) for item in (nopat, capex)):
                continue
            da = row.get('da')
            delta_nwc = row.get('delta_nwc')
            assumptions = []
            if da is None:
                da = 0.0
                assumptions.append('D&A = 0 do thiếu dữ liệu')
            elif not isinstance(da, (int, float)) or not np.isfinite(da):
                continue
            if delta_nwc is None:
                delta_nwc = 0.0
                assumptions.append('ΔNWC = 0 do thiếu dữ liệu')
            elif not isinstance(delta_nwc, (int, float)) or not np.isfinite(delta_nwc):
                continue
            scenario_fcff = float(nopat) + float(da) - float(capex) - float(delta_nwc)
            if scenario_fcff > 0:
                base_row = {**row, 'fcff': scenario_fcff}
                base_fcff_assumptions = assumptions
                break
    if forecast_growth_rate is None:
        forecast_growth_rate = historical_growth_rate
        if forecast_growth_rate is None and base_fcff_assumptions:
            forecast_growth_rate = 0.0
            forecast_growth_source = 'flat_fcff_fallback'
    if terminal_growth_rate is None:
        terminal_growth_rate = historical_growth_rate
        if terminal_growth_rate is None and base_fcff_assumptions:
            terminal_growth_rate = 0.0
            terminal_growth_source = 'flat_fcff_fallback'
    if (terminal_growth_rate is not None and terminal_growth_source == 'historical_fcff_cagr'
            and value is not None and terminal_growth_rate >= value and value > 0):
        terminal_growth_rate = 0.0
        terminal_growth_source = 'flat_terminal_fallback'
    if forecast_growth_source == 'historical_fcff_cagr' and forecast_growth_rate is not None and forecast_growth_rate > 1:
        forecast_growth_rate = 0.0
        forecast_growth_source = 'flat_fcff_fallback'
    latest_history_row = history[-1] if history else {}
    fcff_field_labels = {
        'ebit': 'EBIT / lợi nhuận hoạt động',
        'nopat': 'NOPAT (cần EBIT và thuế suất)',
        'da': 'D&A / khấu hao và phân bổ',
        'capex': 'CapEx / chi đầu tư tài sản cố định',
        'delta_nwc': 'ΔNWC (cần NWC năm hiện tại và năm trước)'
    }
    fcff_missing_keys = set(latest_history_row.get('fcff_missing_inputs', []))
    if 'ebit' in fcff_missing_keys:
        fcff_missing_keys.discard('nopat')
    fcff_missing_components = [
        fcff_field_labels[key] for key in ('ebit', 'nopat', 'da', 'capex', 'delta_nwc')
        if key in fcff_missing_keys
    ]
    dcf = {
        'status': 'not_calculated',
        'forecast_years': 5,
        'forecast_growth_rate': forecast_growth_rate,
        'forecast_growth_rate_source': forecast_growth_source if forecast_growth_rate is not None else 'unavailable',
        'terminal_growth_rate': terminal_growth_rate,
        'terminal_growth_rate_source': terminal_growth_source if terminal_growth_rate is not None else 'unavailable',
        'historical_growth_start_year': historical_growth.get('start_year'),
        'historical_growth_end_year': historical_growth.get('end_year'),
        'historical_growth_points': historical_growth.get('points', 0),
        'growth_method_version': 2,
        'base_fcff': base_row.get('fcff') if base_row else None,
        'base_fcff_year': base_row.get('year') if base_row else None,
        'base_fcff_source': 'zero_missing_inputs_scenario' if base_fcff_assumptions else ('historical_fcff' if base_row else None),
        'base_fcff_assumptions': base_fcff_assumptions,
        'fcff_missing_components': fcff_missing_components,
        'enterprise_value': None,
        'equity_value': None,
        'intrinsic_value_per_share': None,
        'current_share_price': capital.get('current_share_price'),
        'upside': None,
        'missing_inputs': [],
        'message': None
    }
    core_reasons = []
    if forecast_growth_rate is None:
        core_reasons.append('Chưa có năm nào có FCFF dương và đủ đầu vào làm cơ sở; hãy bổ sung dữ liệu FCFF hoặc nhập g 5 năm.')
    elif not -1 < forecast_growth_rate <= 1:
        core_reasons.append('Tốc độ tăng trưởng 5 năm phải lớn hơn -100% và không quá 100%.')
    if terminal_growth_rate is None:
        core_reasons.append('Chưa có FCFF dương hợp lệ để tự tính g dài hạn; hãy bổ sung dữ liệu hoặc nhập g dài hạn.')
    elif not -1 < terminal_growth_rate <= 1:
        core_reasons.append('Tốc độ tăng trưởng dài hạn phải lớn hơn -100% và không quá 100%.')
    if base_row is None:
        if fcff_missing_components:
            core_reasons.append('FCFF gần nhất chưa tính được; thiếu: ' + ', '.join(fcff_missing_components) + '.')
        else:
            core_reasons.append('Không có FCFF lịch sử đầy đủ để làm cơ sở dự phóng; kiểm tra EBIT, D&A, CapEx và ΔNWC.')
    if value is None:
        core_reasons.append('WACC chưa tính được đầy đủ.')
    elif value <= -1:
        core_reasons.append('WACC phải lớn hơn -100%.')
    elif terminal_growth_rate is not None and terminal_growth_rate >= value:
        core_reasons.append('Tăng trưởng dài hạn phải thấp hơn WACC.')
    reasons = list(core_reasons)
    if capital.get('interest_bearing_debt') is None:
        reasons.append('Thiếu số nợ vay chịu lãi để tính giá trị vốn chủ.')
    if capital.get('cash_and_equivalents') is None:
        reasons.append('Thiếu số tiền mặt để tính giá trị vốn chủ.')
    if capital.get('shares_outstanding_estimate') is None:
        reasons.append('Thiếu dữ liệu để ước tính số cổ phiếu lưu hành.')

    dcf['missing_inputs'] = reasons
    if not core_reasons:
        base_fcff = float(base_row['fcff'])
        growth = float(forecast_growth_rate)
        terminal_growth = float(terminal_growth_rate)
        forecast_fcff = [base_fcff * (1 + growth) ** year for year in range(1, 6)]
        discount_rate = float(value)
        pv_forecast = sum(cash_flow / (1 + discount_rate) ** year
                          for year, cash_flow in enumerate(forecast_fcff, start=1))
        terminal_value = forecast_fcff[-1] * (1 + terminal_growth) / (discount_rate - terminal_growth)
        enterprise_value = pv_forecast + terminal_value / (1 + discount_rate) ** 5
        dcf['enterprise_value'] = enterprise_value
        debt = capital.get('interest_bearing_debt')
        cash = capital.get('cash_and_equivalents')
        if debt is not None and cash is not None:
            equity_value = enterprise_value + float(cash) - float(debt)
            dcf['equity_value'] = equity_value
            shares = capital.get('shares_outstanding_estimate')
            if shares is not None and float(shares) > 0:
                dcf['intrinsic_value_per_share'] = equity_value / float(shares)
                current_price = capital.get('current_share_price')
                if current_price is not None and float(current_price) > 0:
                    dcf['upside'] = (dcf['intrinsic_value_per_share'] / float(current_price)) - 1
        dcf['status'] = 'ready' if dcf['intrinsic_value_per_share'] is not None else 'partial'
        notes = []
        if base_fcff_assumptions:
            notes.append('FCFF cơ sở là kịch bản tham khảo từ năm ' + str(base_row.get('year'))
                         + ': ' + '; '.join(base_fcff_assumptions)
                         + '. Không ghi các giả định này thành dữ liệu lịch sử.')
        if historical_growth.get('points', 0) == 1 and (
                forecast_growth_source == 'flat_fcff_fallback' or terminal_growth_source == 'flat_fcff_fallback'):
            notes.append('Chỉ có một năm FCFF dương hợp lệ nên g tự động dùng kịch bản FCFF đi ngang 0%; bạn có thể nhập g để ghi đè.')
        elif base_fcff_assumptions and historical_growth.get('points', 0) == 0:
            notes.append('Chưa có chuỗi FCFF lịch sử đầy đủ nên g mặc định 0% để hiện kịch bản đi ngang; bạn có thể nhập g để ghi đè.')
        elif forecast_growth_source == 'flat_fcff_fallback':
            notes.append('CAGR FCFF lịch sử vượt phạm vi hợp lý nên g 5 năm tự động dùng kịch bản đi ngang 0%; bạn có thể nhập g để ghi đè.')
        if terminal_growth_source == 'flat_terminal_fallback':
            notes.append('CAGR FCFF lịch sử không thấp hơn WACC nên g dài hạn tự động dùng kịch bản 0%; bạn có thể nhập g để ghi đè.')
        if base_row and history and base_row.get('year') != history[-1].get('year') and not base_fcff_assumptions:
            notes.append(f"FCFF cơ sở lấy từ năm {base_row.get('year')} gần nhất có FCFF dương và đủ đầu vào; các năm sau thiếu hoặc không có FCFF dương được bỏ qua.")
        if dcf['status'] == 'partial':
            notes.append('Đã tính EV; thiếu dữ liệu để quy đổi đầy đủ sang giá trị mỗi cổ phiếu.')
        dcf['message'] = ' '.join(notes) or 'Ước tính DCF từ FCFF dương gần nhất và các giả định tăng trưởng; các năm thiếu dữ liệu được bỏ qua.'
    else:
        dcf['message'] = 'Chưa thể tính giá trị nội tại: ' + ' '.join(core_reasons)
    valuation['dcf'] = dcf


def _calculate_bank_residual_income(valuation, ticker, risk_free_rate=None,
                                    equity_risk_premium=None, forecast_growth_rate=None,
                                    terminal_growth_rate=None):
    """Value a bank as book equity plus discounted residual income to shareholders."""
    if not valuation or valuation.get('model') != 'bank_residual_income':
        return

    risk_free_as_of = None
    risk_free_source = 'HNX 10Y yield entered manually'
    if risk_free_rate is None:
        risk_free_rate, risk_free_as_of = _fetch_vn_10y_risk_free_rate()
        risk_free_source = 'Vnstock Macro, Vietnam Government Bond 10Y' if risk_free_rate is not None else 'unavailable'
    else:
        risk_free_source = 'User-provided HNX 10Y override'

    erp_as_of = None
    erp_source = 'Damodaran current country-premium workbook (rating-based total ERP)'
    if equity_risk_premium is None:
        equity_risk_premium, erp_as_of = _fetch_damodaran_erp()
        if equity_risk_premium is None:
            erp_source = 'unavailable'
    else:
        erp_source = 'User-provided ERP override'

    if risk_free_rate is not None and (not np.isfinite(risk_free_rate) or not 0 <= risk_free_rate <= 1):
        risk_free_rate = None
    if equity_risk_premium is not None and (not np.isfinite(equity_risk_premium) or not 0 <= equity_risk_premium <= 1):
        equity_risk_premium = None
    beta = _calculate_market_beta(ticker)
    cost_of_equity = risk_free_rate + beta * equity_risk_premium if (
        risk_free_rate is not None and equity_risk_premium is not None and beta is not None
    ) else None

    capital = valuation.get('capital_structure', {})
    history = sorted(valuation.get('history', []), key=lambda row: row.get('year') or 0)
    book_equity = capital.get('book_equity')
    shares = capital.get('shares_outstanding_estimate')
    current_price = capital.get('current_share_price')
    market_cap = capital.get('market_equity_value')
    book_history = [row for row in history if isinstance(row.get('book_equity'), (int, float))
                    and np.isfinite(row['book_equity']) and row['book_equity'] > 0]
    if book_equity is None or not isinstance(book_equity, (int, float)) or not np.isfinite(book_equity):
        book_equity = book_history[-1]['book_equity'] if book_history else None
        if book_equity is not None:
            capital['book_equity'] = book_equity
            capital['book_equity_as_of'] = str(book_history[-1]['year'])

    historical_book_growth = None
    if len(book_history) >= 2:
        first, last = book_history[0], book_history[-1]
        years_apart = int(last['year']) - int(first['year'])
        if years_apart > 0:
            candidate = (last['book_equity'] / first['book_equity']) ** (1 / years_apart) - 1
            if np.isfinite(candidate) and candidate > -1:
                historical_book_growth = float(candidate)

    if forecast_growth_rate is not None and not np.isfinite(forecast_growth_rate):
        forecast_growth_rate = None
    if terminal_growth_rate is not None and not np.isfinite(terminal_growth_rate):
        terminal_growth_rate = None
    if forecast_growth_rate is not None:
        book_growth = forecast_growth_rate
        book_growth_source = 'user_input'
    elif historical_book_growth is not None and historical_book_growth <= 1:
        book_growth = historical_book_growth
        book_growth_source = 'historical_book_equity_cagr'
    else:
        book_growth = 0.0
        book_growth_source = 'flat_book_growth_fallback'

    stable_growth_fallback = min(0.03, max(0.0, cost_of_equity - 0.01)) if cost_of_equity is not None else 0.03
    if terminal_growth_rate is not None:
        stable_growth = terminal_growth_rate
        stable_growth_source = 'user_input'
    elif historical_book_growth is not None and cost_of_equity is not None and -1 < historical_book_growth < cost_of_equity:
        stable_growth = historical_book_growth
        stable_growth_source = 'historical_book_equity_cagr'
    else:
        stable_growth = stable_growth_fallback
        stable_growth_source = 'stable_growth_fallback'

    valid_roes = [float(row['roe']) for row in history if isinstance(row.get('roe'), (int, float))
                  and np.isfinite(row['roe'])]
    current_roe = capital.get('current_roe')
    if not isinstance(current_roe, (int, float)) or not np.isfinite(current_roe) or current_roe == 0:
        current_roe = valid_roes[-1] if valid_roes else None
    stable_roe = float(np.median(valid_roes[-5:])) if valid_roes else None

    market_pb = None
    if market_cap is not None and book_equity is not None and book_equity > 0:
        market_pb = market_cap / book_equity
    elif capital.get('market_pb') is not None:
        market_pb = capital.get('market_pb')
    book_value_per_share = book_equity / shares if book_equity is not None and shares is not None and shares > 0 else None
    implied_stable_pb = None
    stable_value_per_share = None
    if cost_of_equity is not None and stable_roe is not None and stable_growth < cost_of_equity and stable_roe > stable_growth:
        implied_stable_pb = (stable_roe - stable_growth) / (cost_of_equity - stable_growth)
        if book_value_per_share is not None:
            stable_value_per_share = book_value_per_share * implied_stable_pb

    bank_dcf = {
        'status': 'not_calculated',
        'forecast_years': 5,
        'book_equity': book_equity,
        'book_equity_as_of': capital.get('book_equity_as_of'),
        'book_value_per_share': book_value_per_share,
        'forecast_book_growth': book_growth,
        'forecast_book_growth_source': book_growth_source,
        'terminal_growth_rate': stable_growth,
        'terminal_growth_source': stable_growth_source,
        'historical_book_growth': historical_book_growth,
        'forecast_roe_start': current_roe,
        'stable_roe': stable_roe,
        'cost_of_equity': cost_of_equity,
        'equity_value': None,
        'intrinsic_value_per_share': None,
        'current_share_price': current_price,
        'upside': None,
        'fair_pb_residual_income': None,
        'fair_pb_stable_state': implied_stable_pb,
        'stable_value_per_share': stable_value_per_share,
        'market_pb': market_pb,
        'missing_inputs': [],
        'message': None
    }

    missing = []
    if book_equity is None or book_equity <= 0:
        missing.append('thiếu vốn chủ sở hữu sổ sách dương')
    if shares is None or shares <= 0:
        missing.append('thiếu số cổ phiếu lưu hành ước tính')
    if current_roe is None:
        missing.append('thiếu ROE hiện tại/lịch sử')
    if stable_roe is None:
        missing.append('thiếu dữ liệu ROE để ước tính ROE ổn định')
    if cost_of_equity is None:
        missing.append('thiếu beta, Rf hoặc ERP để tính chi phí vốn chủ')
    elif cost_of_equity <= -1:
        missing.append('chi phí vốn chủ phải lớn hơn -100%')
    if book_growth <= -1 or book_growth > 1:
        missing.append('g vốn chủ 5 năm phải lớn hơn -100% và không quá 100%')
    if stable_growth <= -1 or stable_growth > 1:
        missing.append('g dài hạn phải lớn hơn -100% và không quá 100%')
    elif cost_of_equity is not None and stable_growth >= cost_of_equity:
        missing.append('g dài hạn phải thấp hơn chi phí vốn chủ')

    if not missing:
        equity = float(book_equity)
        present_value_residual_income = 0.0
        for year in range(1, 6):
            year_roe = float(current_roe) + (float(stable_roe) - float(current_roe)) * year / 5
            beginning_book_equity = equity * (1 + float(book_growth)) ** (year - 1)
            residual_income = (year_roe - float(cost_of_equity)) * beginning_book_equity
            present_value_residual_income += residual_income / (1 + float(cost_of_equity)) ** year

        ending_book_equity = equity * (1 + float(book_growth)) ** 5
        terminal_residual_income = (float(stable_roe) - float(cost_of_equity)) * ending_book_equity
        terminal_value = terminal_residual_income / (float(cost_of_equity) - float(stable_growth))
        intrinsic_equity_value = equity + present_value_residual_income + terminal_value / (1 + float(cost_of_equity)) ** 5
        intrinsic_per_share = intrinsic_equity_value / float(shares)
        bank_dcf['equity_value'] = intrinsic_equity_value
        bank_dcf['intrinsic_value_per_share'] = intrinsic_per_share
        bank_dcf['fair_pb_residual_income'] = intrinsic_equity_value / equity
        if current_price is not None and current_price > 0:
            bank_dcf['upside'] = intrinsic_per_share / float(current_price) - 1
        bank_dcf['status'] = 'ready' if bank_dcf['upside'] is not None else 'partial'

    bank_dcf['missing_inputs'] = missing
    notes = ['Định giá lợi nhuận thặng dư: vốn chủ sổ sách + giá trị hiện tại của (ROE − chi phí vốn chủ) × vốn chủ đầu kỳ.']
    if book_growth_source == 'flat_book_growth_fallback':
        notes.append('Không đủ chuỗi vốn chủ để suy ra g 5 năm nên dùng giả định vốn chủ tăng 0%; có thể nhập g để ghi đè.')
    elif book_growth_source == 'historical_book_equity_cagr':
        notes.append('g vốn chủ 5 năm lấy từ CAGR vốn chủ sổ sách lịch sử; đây là đại diện cho tăng trưởng vốn chủ, không phải dự báo lợi nhuận.')
    if stable_growth_source == 'stable_growth_fallback':
        notes.append(f'g dài hạn dùng giả định ổn định {stable_growth:.1%} vì CAGR vốn chủ không phù hợp hoặc không thấp hơn chi phí vốn chủ; có thể nhập để ghi đè.')
    if missing:
        notes.append('Chưa tính được giá trị nội tại: ' + '; '.join(missing) + '.')
    elif bank_dcf['status'] == 'partial':
        notes.append('Đã tính giá trị vốn chủ; chưa có giá thị trường để tính chênh lệch.')
    else:
        notes.append('Giá trị mỗi cổ phiếu là ước tính theo số cổ phiếu từ vốn hóa/giá hiện tại.')
    bank_dcf['message'] = ' '.join(notes)

    valuation['cost_of_equity'] = {
        'beta': beta,
        'risk_free_rate': risk_free_rate,
        'risk_free_rate_source': risk_free_source,
        'risk_free_rate_as_of': risk_free_as_of,
        'equity_risk_premium': equity_risk_premium,
        'equity_risk_premium_source': erp_source,
        'equity_risk_premium_as_of': erp_as_of,
        'value': cost_of_equity
    }
    valuation['bank_valuation'] = bank_dcf
    valuation['status'] = bank_dcf['status']

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
                if val: val = val / 100
                avg_roe_5y += val
                valid_roe_count += 1
        avg_roe_5y = avg_roe_5y / valid_roe_count if valid_roe_count > 0 else roe_ttm

        roa = get_latest_q_value(df_ratio_q, ["ROA bình quân 4 quý", "roa_trailling", "ROAA", "ROA", "sinh lợi trên tổng tài sản"])
        if roa == 0: roa = get_row_value(df_ratio, ["ROAA", "ROA", "sinh lợi trên tổng tài sản"], latest_year_str)
        if roa: roa = roa / 100

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
        if roa: roa = roa / 100
             
        roe = get_latest_q_value(df_ratio_q, ["ROE bình quân 4 quý", "roe_trailling", "ROEA", "ROE", "lợi nhuận trên vốn chủ sở hữu"])
        if roe == 0: roe = get_row_value(df_ratio, ["ROEA", "ROE", "lợi nhuận trên vốn chủ sở hữu"], latest_year_str)
        if roe: roe = roe / 100
             
        nim = get_latest_q_value(df_ratio_q, ["NIM", "lãi thuần", "thu nhập lãi thuần"])
        if nim != 0:
            nim = nim * 4
        else:
            nim = get_row_value(df_ratio, ["NIM", "lãi thuần", "thu nhập lãi thuần"], latest_year_str)
        if nim: nim = nim / 100
            
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
        if cfo_quality_ttm: cfo_quality_ttm = cfo_quality_ttm / 100

        # ED Current (Equity / Debt)
        de_current = get_latest_q_value(df_ratio_q, ["debt_to_equity", "Nợ vay trên Vốn chủ sở hữu"]) if df_ratio_q is not None else 0
        if de_current == 0:
            de_current = get_row_value(df_ratio, ["debt_to_equity", "Nợ vay trên Vốn chủ sở hữu"], latest_year_str)
        if de_current: de_current = de_current / 100
        
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
    import os
    import json
    from datetime import datetime
    import concurrent.futures
    import threading
    
    CACHE_DIR = "cache"
    import urllib.parse
    safe_sector = urllib.parse.quote(sector).replace('%', '_')
    today = datetime.now().strftime("%Y-%m-%d")
    screener_cache_file = os.path.join(CACHE_DIR, f"screener_{safe_sector}_{today}.json")
    partial_cache_file = os.path.join(CACHE_DIR, f"partial_{safe_sector}_{today}.json")
    medians_cache_file = os.path.join(CACHE_DIR, f"medians_{safe_sector}_{today}.json")
    
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
        
    if not force_update and os.path.exists(screener_cache_file):
        try:
            with open(screener_cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass

    tickers = get_tickers_by_sector(sector)
    if not tickers:
        return []
        
    top_tickers = get_top_market_cap(tickers, limit=20)
    
    results = []
    write_lock = threading.Lock()
    
    def update_partial(df_temp, sector_type):
        if df_temp.empty: return
        if sector_type == 'sec':
            median_pb = df_temp['PB'].median()
            if median_pb is None or pd.isna(median_pb) or median_pb < 0.01: median_pb = 0.01
            median_pe = df_temp['PE'].median()
            if median_pe is None or pd.isna(median_pe) or median_pe < 0.01: median_pe = 0.01
            median_roe_ttm = df_temp['ROE_TTM'].median()
            if median_roe_ttm is None or pd.isna(median_roe_ttm) or median_roe_ttm < 0.01: median_roe_ttm = 0.01
            median_roe_5y = df_temp['ROE_5Y'].median()
            if median_roe_5y is None or pd.isna(median_roe_5y) or median_roe_5y < 0.01: median_roe_5y = 0.01
            median_eq = df_temp['Equity_Ratio'].median()
            if median_eq is None or pd.isna(median_eq) or median_eq < 0.01: median_eq = 0.01
            
            if pd.isna(median_pb) or median_pb == 0: median_pb = 1.5
            if pd.isna(median_pe) or median_pe == 0: median_pe = 15.0
            if pd.isna(median_roe_ttm) or median_roe_ttm == 0: median_roe_ttm = 0.10
            if pd.isna(median_roe_5y) or median_roe_5y == 0: median_roe_5y = 0.10
            if pd.isna(median_eq) or median_eq == 0: median_eq = 0.10
                
            df_temp['Score_PB'] = (median_pb / df_temp['PB'].replace(0, np.nan)) * 100
            df_temp['Score_PE'] = (median_pe / df_temp['PE'].replace(0, np.nan)) * 100
            df_temp['Score_ROE_TTM'] = (df_temp['ROE_TTM'] / median_roe_ttm) * 100
            df_temp['Score_ROE_5Y'] = (df_temp['ROE_5Y'] / median_roe_5y) * 100
            df_temp['Score_EQ'] = (df_temp['Equity_Ratio'] / median_eq) * 100
            
            for col in df_temp.columns:
                if col.startswith('Score_'):
                    df_temp[col] = df_temp[col].clip(upper=300)

            df_temp['Total Score'] = (df_temp['Score_PB'] * 0.30) + (df_temp['Score_ROE_TTM'] * 0.20) + (df_temp['Score_ROE_5Y'] * 0.15) + (df_temp['Score_PE'] * 0.20) + (df_temp['Score_EQ'] * 0.15)
        elif sector_type == 'bank':
            median_roa = df_temp['ROA'].median()
            if median_roa is None or pd.isna(median_roa) or median_roa < 0.01: median_roa = 0.01
            median_nim = df_temp['NIM'].median()
            if median_nim is None or pd.isna(median_nim) or median_nim < 0.01: median_nim = 0.01
            median_value = df_temp['Value_Ratio'].median()
            if median_value is None or pd.isna(median_value) or median_value < 0.01: median_value = 0.01
            median_eq = df_temp['Equity_Ratio'].median()
            if median_eq is None or pd.isna(median_eq) or median_eq < 0.01: median_eq = 0.01
            
            if pd.isna(median_roa) or median_roa == 0: median_roa = 0.02
            if pd.isna(median_nim) or median_nim == 0: median_nim = 0.035
            if pd.isna(median_value) or median_value == 0: median_value = 10.0
            if pd.isna(median_eq) or median_eq == 0: median_eq = 0.10
                
            df_temp['Score_ROA'] = (df_temp['ROA'] / median_roa) * 100
            df_temp['Score_NIM'] = (df_temp['NIM'].clip(upper=0.045) / median_nim) * 100
            df_temp['Score_Value'] = (df_temp['Value_Ratio'] / median_value) * 100
            df_temp['Score_EQ'] = (df_temp['Equity_Ratio'] / median_eq) * 100
            
            for col in df_temp.columns:
                if col.startswith('Score_'):
                    df_temp[col] = df_temp[col].clip(upper=300)

            df_temp['Total Score'] = (df_temp['Score_Value'] * 0.30) + (df_temp['Score_EQ'] * 0.25) + (df_temp['Score_ROA'] * 0.25) + (df_temp['Score_NIM'] * 0.20)
        else:
            median_roic = df_temp['ROIC_5Y'].median()
            if median_roic is None or pd.isna(median_roic) or median_roic < 0.01: median_roic = 0.01
            median_roic_ttm = df_temp['ROIC_TTM'].median()
            if median_roic_ttm is None or pd.isna(median_roic_ttm) or median_roic_ttm < 0.01: median_roic_ttm = 0.01
            median_value = df_temp['Value_Ratio'].median()
            if median_value is None or pd.isna(median_value) or median_value < 0.01: median_value = 0.01
            median_cfo_ttm = df_temp['CFO_Quality_TTM'].median()
            if median_cfo_ttm is None or pd.isna(median_cfo_ttm) or median_cfo_ttm < 0.01: median_cfo_ttm = 0.01
            median_ed_curr = df_temp['ED_Current'].median()
            if median_ed_curr is None or pd.isna(median_ed_curr) or median_ed_curr < 0.01: median_ed_curr = 0.01
            
            if pd.isna(median_roic) or median_roic == 0: median_roic = 0.10
            if pd.isna(median_roic_ttm) or median_roic_ttm == 0: median_roic_ttm = 0.10
            if pd.isna(median_value) or median_value == 0: median_value = 10.0
            if pd.isna(median_cfo_ttm) or median_cfo_ttm == 0: median_cfo_ttm = 1.0
            if pd.isna(median_ed_curr) or median_ed_curr == 0: median_ed_curr = 1.0
            
            df_temp['Score_ROIC'] = (df_temp['ROIC_5Y'] / median_roic) * 100
            df_temp['Score_ROIC_TTM'] = (df_temp['ROIC_TTM'] / median_roic_ttm) * 100
            df_temp['Score_Value'] = (df_temp['Value_Ratio'] / median_value) * 100
            
            df_temp['Score_CFO_TTM'] = (df_temp['CFO_Quality_TTM'].clip(upper=3.0) / median_cfo_ttm) * 100
            df_temp.loc[df_temp['CFO_Quality_TTM'] < 0, 'Score_CFO_TTM'] = 0
            
            df_temp['Score_ED_Current'] = (df_temp['ED_Current'] / median_ed_curr) * 100
            
            for col in df_temp.columns:
                if col.startswith('Score_'):
                    df_temp[col] = df_temp[col].clip(upper=300)

            df_temp['Total Score'] = (df_temp['Score_ROIC'] * 0.15) + (df_temp['Score_ROIC_TTM'] * 0.25) + (df_temp['Score_Value'] * 0.20) + (df_temp['Score_CFO_TTM'] * 0.20) + (df_temp['Score_ED_Current'] * 0.20)

        df_temp = df_temp.sort_values(by='Total Score', ascending=False).reset_index(drop=True).fillna(0)
        try:
            with open(partial_cache_file, 'w', encoding='utf-8') as f:
                json.dump(df_temp.to_dict('records'), f, ensure_ascii=False)
        except:
            pass

    def process_ticker(t, s_type, compute_func):
        while USER_PRIORITY_FLAG.is_set():
            time.sleep(1)
        try:
            res = compute_func(t)
            if res:
                with write_lock:
                    results.append(res)
                    update_partial(pd.DataFrame(results), s_type)
        except Exception as e:
            print(f"Loi: {e}")

    if sector.lower() in ['chứng khoán', 'securities', 'dịch vụ tài chính']:
        s_type = 'sec'
        c_func = calculate_engine_securities
    elif sector.lower() in ['ngân hàng', 'banks']:
        s_type = 'bank'
        c_func = calculate_engine_bank
    else:
        s_type = 'other'
        c_func = calculate_engine

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_to_ticker = {executor.submit(process_ticker, t, s_type, c_func): t for t in top_tickers}
        concurrent.futures.wait(future_to_ticker)

    df = pd.DataFrame(results)
    if df.empty:
        return []
        
    if s_type == 'sec':
        median_pb = df['PB'].median()
        if median_pb is None or pd.isna(median_pb) or median_pb < 0.01: median_pb = 0.01
        median_pe = df['PE'].median()
        if median_pe is None or pd.isna(median_pe) or median_pe < 0.01: median_pe = 0.01
        median_roe_ttm = df['ROE_TTM'].median()
        if median_roe_ttm is None or pd.isna(median_roe_ttm) or median_roe_ttm < 0.01: median_roe_ttm = 0.01
        median_roe_5y = df['ROE_5Y'].median()
        if median_roe_5y is None or pd.isna(median_roe_5y) or median_roe_5y < 0.01: median_roe_5y = 0.01
        median_eq = df['Equity_Ratio'].median()
        if median_eq is None or pd.isna(median_eq) or median_eq < 0.01: median_eq = 0.01
        if pd.isna(median_pb) or median_pb == 0: median_pb = 1.5
        if pd.isna(median_pe) or median_pe == 0: median_pe = 15.0
        if pd.isna(median_roe_ttm) or median_roe_ttm == 0: median_roe_ttm = 0.10
        if pd.isna(median_roe_5y) or median_roe_5y == 0: median_roe_5y = 0.10
        if pd.isna(median_eq) or median_eq == 0: median_eq = 0.10
        try:
            with open(medians_cache_file, 'w', encoding='utf-8') as f:
                json.dump({'median_pb': float(median_pb), 'median_pe': float(median_pe), 'median_roe_ttm': float(median_roe_ttm), 'median_roe_5y': float(median_roe_5y), 'median_eq': float(median_eq)}, f)
        except: pass
        df['Score_PB'] = (median_pb / df['PB'].replace(0, np.nan)) * 100
        df['Score_PE'] = (median_pe / df['PE'].replace(0, np.nan)) * 100
        df['Score_ROE_TTM'] = (df['ROE_TTM'] / median_roe_ttm) * 100
        df['Score_ROE_5Y'] = (df['ROE_5Y'] / median_roe_5y) * 100
        df['Score_EQ'] = (df['Equity_Ratio'] / median_eq) * 100
        for col in df.columns:
            if col.startswith('Score_'):
                df[col] = df[col].clip(upper=300)

        df['Total Score'] = (df['Score_PB'] * 0.30) + (df['Score_ROE_TTM'] * 0.20) + (df['Score_ROE_5Y'] * 0.15) + (df['Score_PE'] * 0.20) + (df['Score_EQ'] * 0.15)
        
    elif s_type == 'bank':
        median_roa = df['ROA'].median()
        if median_roa is None or pd.isna(median_roa) or median_roa < 0.01: median_roa = 0.01
        median_nim = df['NIM'].median()
        if median_nim is None or pd.isna(median_nim) or median_nim < 0.01: median_nim = 0.01
        median_value = df['Value_Ratio'].median()
        if median_value is None or pd.isna(median_value) or median_value < 0.01: median_value = 0.01
        median_eq = df['Equity_Ratio'].median()
        if median_eq is None or pd.isna(median_eq) or median_eq < 0.01: median_eq = 0.01
        if pd.isna(median_roa) or median_roa == 0: median_roa = 0.02
        if pd.isna(median_nim) or median_nim == 0: median_nim = 0.035
        if pd.isna(median_value) or median_value == 0: median_value = 10.0
        if pd.isna(median_eq) or median_eq == 0: median_eq = 0.10
        try:
            with open(medians_cache_file, 'w', encoding='utf-8') as f:
                json.dump({'median_roa': float(median_roa), 'median_nim': float(median_nim), 'median_value': float(median_value), 'median_eq': float(median_eq)}, f)
        except: pass
        df['Score_ROA'] = (df['ROA'] / median_roa) * 100
        df['Score_NIM'] = (df['NIM'].clip(upper=0.045) / median_nim) * 100
        df['Score_Value'] = (df['Value_Ratio'] / median_value) * 100
        df['Score_EQ'] = (df['Equity_Ratio'] / median_eq) * 100
        for col in df.columns:
            if col.startswith('Score_'):
                df[col] = df[col].clip(upper=300)

        df['Total Score'] = (df['Score_Value'] * 0.30) + (df['Score_EQ'] * 0.25) + (df['Score_ROA'] * 0.25) + (df['Score_NIM'] * 0.20)
        
    else:
        median_roic = df['ROIC_5Y'].median()
        if median_roic is None or pd.isna(median_roic) or median_roic < 0.01: median_roic = 0.01
        median_roic_ttm = df['ROIC_TTM'].median()
        if median_roic_ttm is None or pd.isna(median_roic_ttm) or median_roic_ttm < 0.01: median_roic_ttm = 0.01
        median_value = df['Value_Ratio'].median()
        if median_value is None or pd.isna(median_value) or median_value < 0.01: median_value = 0.01
        median_cfo_ttm = df['CFO_Quality_TTM'].median()
        if median_cfo_ttm is None or pd.isna(median_cfo_ttm) or median_cfo_ttm < 0.01: median_cfo_ttm = 0.01
        median_ed_curr = df['ED_Current'].median()
        if median_ed_curr is None or pd.isna(median_ed_curr) or median_ed_curr < 0.01: median_ed_curr = 0.01
        if pd.isna(median_roic) or median_roic == 0: median_roic = 0.10
        if pd.isna(median_roic_ttm) or median_roic_ttm == 0: median_roic_ttm = 0.10
        if pd.isna(median_value) or median_value == 0: median_value = 10.0
        if pd.isna(median_cfo_ttm) or median_cfo_ttm == 0: median_cfo_ttm = 1.0
        if pd.isna(median_ed_curr) or median_ed_curr == 0: median_ed_curr = 1.0
        try:
            with open(medians_cache_file, 'w', encoding='utf-8') as f:
                json.dump({'median_roic': float(median_roic), 'median_roic_ttm': float(median_roic_ttm), 'median_value': float(median_value), 'median_cfo_ttm': float(median_cfo_ttm), 'median_ed_curr': float(median_ed_curr)}, f)
        except: pass
        df['Score_ROIC'] = (df['ROIC_5Y'] / median_roic) * 100
        df['Score_ROIC_TTM'] = (df['ROIC_TTM'] / median_roic_ttm) * 100
        df['Score_Value'] = (df['Value_Ratio'] / median_value) * 100
        df['Score_CFO_TTM'] = (df['CFO_Quality_TTM'].clip(upper=3.0) / median_cfo_ttm) * 100
        df.loc[df['CFO_Quality_TTM'] < 0, 'Score_CFO_TTM'] = 0
        df['Score_ED_Current'] = (df['ED_Current'] / median_ed_curr) * 100
        for col in df.columns:
            if col.startswith('Score_'):
                df[col] = df[col].clip(upper=300)

        df['Total Score'] = (df['Score_ROIC'] * 0.15) + (df['Score_ROIC_TTM'] * 0.25) + (df['Score_Value'] * 0.20) + (df['Score_CFO_TTM'] * 0.20) + (df['Score_ED_Current'] * 0.20)

    df = df.sort_values(by='Total Score', ascending=False).reset_index(drop=True).fillna(0)
    final_results = df.to_dict('records')
    try:
        df.to_json(screener_cache_file, orient='records', force_ascii=False)
    except Exception as e:
        print("CACHE ERROR:", e)
        
    # Clean up partial cache when done
    try:
        if os.path.exists(partial_cache_file):
            os.remove(partial_cache_file)
    except:
        pass
        
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
            try:
                df_bs_q = f_bs.balance_sheet(period='quarter')
            except Exception:
                df_bs_q = None
            
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
            bank_valuation_history = []
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
                if roe: roe = roe / 100
                
                roa = get_row_value(df_ratio, ["ROAA", "ROA", "sinh lợi trên tổng tài sản"], ratio_year_str)
                if roa: roa = roa / 100
                
                value_ratio = (roe / pb) if pb and pb > 0 and roe else 0.0

                def _ratio_as_decimal(value):
                    if value is None:
                        return None
                    numeric = float(value)
                    return numeric / 100 if abs(numeric) > 1 else numeric

                roe_raw = _optional_row_value(df_ratio, ["ROE", "lợi nhuận trên vốn chủ sở hữu"], ratio_year_str)
                roa_raw = _optional_row_value(df_ratio, ["ROAA", "ROA", "sinh lợi trên tổng tài sản"], ratio_year_str)
                nim_raw = _optional_row_value(df_ratio, ["NIM", "lãi thuần", "thu nhập lãi thuần"], ratio_year_str)
                book_period_col = _period_column(df_bs, target_year_str) or target_year_str
                book_equity = _optional_row_value(df_bs, [
                    'Vốn chủ sở hữu của cổ đông công ty mẹ', 'Vốn chủ sở hữu',
                    'Tổng vốn chủ sở hữu', 'Total shareholders equity', 'Shareholders equity'
                ], book_period_col)
                npl_raw = _optional_row_value(df_ratio, [
                    'Tỷ lệ nợ xấu', 'Nợ xấu / Tổng dư nợ', 'NPL', 'Non-performing loan ratio'
                ], ratio_year_str)
                car_raw = _optional_row_value(df_ratio, [
                    'Tỷ lệ an toàn vốn', 'CAR', 'Capital adequacy ratio'
                ], ratio_year_str)

                history.append({
                    'year': target_year_str,
                    'roa': float(roa) if roa else 0.0,
                    'nim': float(nim) if nim else 0.0,
                    'pb': float(pb) if pb else 0.0,
                    'ep': float(ep) if ep else 0.0,
                    'roe': float(roe) if roe else 0.0,
                    'value_ratio': float(value_ratio)
                })
                bank_valuation_history.append({
                    'year': int(target_year_str),
                    'book_equity': float(book_equity) if book_equity is not None else None,
                    'roe': _ratio_as_decimal(roe_raw),
                    'roa': _ratio_as_decimal(roa_raw),
                    'nim': _ratio_as_decimal(nim_raw),
                    'npl_ratio': _ratio_as_decimal(npl_raw),
                    'capital_adequacy_ratio': _ratio_as_decimal(car_raw),
                    'pb': float(pb) if pb is not None else None,
                    'pe': float(pe) if pe is not None else None
                })
            
            history.reverse()
            bank_valuation_history.reverse()
            
            try:
                df_ratio_q = Finance(symbol=ticker, source='KBS').ratio(period='quarter')
            except:
                df_ratio_q = None
                
            latest_q_str = ""
            if df_ratio_q is not None and not df_ratio_q.empty:
                latest_q_str = get_latest_quarter_str(df_ratio_q, ["ROE", "P/B"])
            latest_y_str = str(history[-1]['year']) if history else ""
                
            roa_q = get_latest_q_value(df_ratio_q, ["ROA bình quân 4 quý", "roa_trailling", "ROAA", "ROA", "sinh lợi trên tổng tài sản"])
            if roa_q == 0: roa_q = history[-1].get('roa', 0) * 100 if history else 0
            if roa_q: roa_q = _ratio_as_decimal(roa_q)
                
            roe_q = get_latest_q_value(df_ratio_q, ["ROE bình quân 4 quý", "roe_trailling", "ROEA", "ROE", "lợi nhuận trên vốn chủ sở hữu"])
            if roe_q == 0: roe_q = history[-1].get('roe', 0) * 100 if history else 0
            if roe_q: roe_q = _ratio_as_decimal(roe_q)
            
            nim_q = get_latest_q_value(df_ratio_q, ["NIM", "lãi thuần", "thu nhập lãi thuần"])
            if nim_q != 0:
                nim_q = nim_q * 4
                if nim_q: nim_q = nim_q / 100
            else:
                nim_q = history[-1].get('nim', 0) if history else 0
                
            pb_q = get_latest_q_value(df_ratio_q, ["P/B", "giá trị sổ sách (P/B)"])
            if pb_q == 0: pb_q = history[-1].get('pb', 0) if history else 0

            latest_bs_q_col = _quarter_columns(df_bs_q)[0] if df_bs_q is not None and not df_bs_q.empty else None
            current_book_equity = _optional_row_value(df_bs_q, [
                'Vốn chủ sở hữu của cổ đông công ty mẹ', 'Vốn chủ sở hữu',
                'Tổng vốn chủ sở hữu', 'Total shareholders equity', 'Shareholders equity'
            ], latest_bs_q_col) if latest_bs_q_col else None
            current_book_as_of = latest_bs_q_col if current_book_equity is not None else None
            if current_book_equity is None:
                current_book_equity = next((item['book_equity'] for item in reversed(bank_valuation_history)
                                            if item['book_equity'] is not None and item['book_equity'] > 0), None)
                current_book_as_of = str(next((item['year'] for item in reversed(bank_valuation_history)
                                               if item['book_equity'] is not None and item['book_equity'] > 0), '')) or None

            market_equity = _market_cap_to_vnd(market_cap_overview)
            current_price_value = float(current_price) if current_price and float(current_price) > 0 else None
            shares_estimate = market_equity / current_price_value if market_equity is not None and current_price_value else None
            current_market_pb = market_equity / current_book_equity if market_equity is not None and current_book_equity and current_book_equity > 0 else (float(pb_q) if pb_q else None)
            current_roe = float(roe_q) if roe_q else (bank_valuation_history[-1]['roe'] if bank_valuation_history else None)
            
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
                'history': history,
                'valuation_inputs': {
                    'model': 'bank_residual_income',
                    'status': 'partial',
                    'financial_statement_source': 'Vnstock VCI / KBS',
                    'history': bank_valuation_history,
                    'capital_structure': {
                        'book_equity': current_book_equity,
                        'book_equity_as_of': current_book_as_of,
                        'market_equity_value': market_equity,
                        'current_share_price': current_price_value,
                        'shares_outstanding_estimate': shares_estimate,
                        'shares_estimate_basis': 'market_cap_divided_by_current_price' if shares_estimate is not None else None,
                        'market_pb': current_market_pb,
                        'current_roe': current_roe
                    },
                    'cost_of_equity': {},
                    'bank_valuation': {},
                    'message': 'Ngân hàng được định giá theo lợi nhuận thặng dư trên vốn chủ sở hữu; không dùng FCFF/WACC doanh nghiệp thông thường.'
                }
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
                if roe: roe = roe / 100
                
                pb = get_row_value(df_ratio, ["P/B", "giá trị sổ sách (P/B)"], ratio_year_str)
                pe = get_row_value(df_ratio, ["P/E", "thu nhập trên cổ phần (P/E)", "Chỉ số giá thị trường trên thu nhập (P/E)"], ratio_year_str)
                roa = get_row_value(df_ratio, ["ROAA", "ROA", "sinh lợi trên tổng tài sản"], ratio_year_str)
                if roa: roa = roa / 100
                
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
            if roe_ttm: roe_ttm = roe_ttm / 100
            
            roa_q = get_latest_q_value(df_ratio_q, ["ROA bình quân 4 quý", "roa_trailling", "ROAA", "ROA", "sinh lợi trên tổng tài sản"])
            if roa_q == 0: roa_q = history[-1].get('roa', 0) if history else 0
            if roa_q: roa_q = roa_q / 100
            
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
                'history': history,
                'valuation_inputs': {
                    'model': 'sector_specific',
                    'status': 'not_applicable',
                    'message': 'Công ty chứng khoán cần mô hình định giá theo vốn chủ sở hữu và chỉ tiêu ngành; FCFF/NWC và WACC doanh nghiệp thông thường không áp dụng trực tiếp.',
                    'sector_metrics': ['ROE', 'P/B', 'P/E', 'tỷ lệ vốn chủ sở hữu']
                }
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

        if any(label in sector.lower() for label in ('bảo hiểm', 'insurance')):
            valuation_inputs = {
                'model': 'sector_specific',
                'status': 'not_applicable',
                'message': 'Doanh nghiệp bảo hiểm cần mô hình định giá theo vốn chủ sở hữu và dự phòng bảo hiểm; FCFF/NWC doanh nghiệp thông thường không áp dụng trực tiếp.',
                'sector_metrics': ['ROE', 'ROA', 'biên khả năng thanh toán', 'dự phòng nghiệp vụ']
            }
        else:
            valuation_inputs = _build_nonfinancial_valuation_inputs(
                df_is=df_is,
                df_cf=df_cf,
                df_bs=df_bs,
                years_cols=years_cols,
                market_cap=market_cap_overview,
                current_price=current_price,
                tax_rate_fallback=tax_rate_fallback,
                df_is_q=df_is_q,
                df_bs_q=df_bs_q
            )

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
            'history': history,
            'valuation_inputs': valuation_inputs
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
    import urllib.parse
    safe_sector = urllib.parse.quote(sector).replace('%', '_')
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

def get_comparative_report(main_ticker, peers_str="", tax_rate_fallback=0.2,
                           risk_free_rate=None, equity_risk_premium=None,
                           forecast_growth_rate=None, terminal_growth_rate=None):
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
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        future_to_ticker = {executor.submit(get_stock_report, t, tax_rate_fallback): t for t in tickers}
        for future in concurrent.futures.as_completed(future_to_ticker):
            t = future_to_ticker[future]
            try:
                rep = future.result()
                if rep:
                    reports[t] = rep
            except Exception as exc:
                print(f"Loi khi lấy {t}: {exc}")
            
    if main_ticker not in reports:
        return {'status': 'error', 'detail': f'Không tìm thấy dữ liệu cho mã chính {main_ticker}'}

    main_valuation = reports[main_ticker].get('valuation_inputs')
    if main_valuation and main_valuation.get('model') == 'bank_residual_income':
        _calculate_bank_residual_income(
            main_valuation,
            main_ticker,
            risk_free_rate,
            equity_risk_premium,
            forecast_growth_rate,
            terminal_growth_rate
        )
    else:
        _calculate_wacc_inputs(
            main_valuation,
            main_ticker,
            risk_free_rate,
            equity_risk_premium,
            tax_rate_fallback,
            forecast_growth_rate,
            terminal_growth_rate
        )
        
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
            if m_roa is None or m_roa < 0.01: m_roa = 0.01
            m_nim = medians.get('median_nim', 0.035)
            if m_nim is None or m_nim < 0.01: m_nim = 0.01
            m_value = medians.get('median_value', 10.0)
            if m_value is None or m_value < 0.01: m_value = 0.01
            m_eq = medians.get('median_eq', 0.1)
            if m_eq is None or m_eq < 0.01: m_eq = 0.01
            
            df_rank['Score_ROA'] = (df_rank['ROA_Current'] / m_roa) * 100
            df_rank['Score_NIM'] = (df_rank['NIM_Current'].clip(upper=0.045) / m_nim) * 100
            df_rank['Score_Value'] = (df_rank['Value_Ratio_Current'] / m_value) * 100
            df_rank['Score_EQ'] = (df_rank['Equity_Ratio_Current'] / m_eq) * 100
            for col in df_rank.columns:
                if col.startswith('Score_'):
                    df_rank[col] = df_rank[col].clip(upper=300)

            df_rank['Total_Score'] = (df_rank['Score_Value'] * 0.30) + (df_rank['Score_EQ'] * 0.25) + (df_rank['Score_ROA'] * 0.25) + (df_rank['Score_NIM'] * 0.20)
        elif is_securities:
            m_pb = medians.get('median_pb', 1.5)
            if m_pb is None or m_pb < 0.01: m_pb = 0.01
            m_pe = medians.get('median_pe', 15.0)
            if m_pe is None or m_pe < 0.01: m_pe = 0.01
            m_roe = medians.get('median_roe_ttm', 0.1)
            if m_roe is None or m_roe < 0.01: m_roe = 0.01
            m_roe5 = medians.get('median_roe_5y', 0.1)
            if m_roe5 is None or m_roe5 < 0.01: m_roe5 = 0.01
            m_eq = medians.get('median_eq', 0.3)
            if m_eq is None or m_eq < 0.01: m_eq = 0.01
            
            df_rank['Score_PB'] = np.where(df_rank['PB_Current'] > 0, (m_pb / df_rank['PB_Current']) * 100, 0)
            df_rank['Score_PE'] = np.where(df_rank['PE_Current'] > 0, (m_pe / df_rank['PE_Current']) * 100, 0)
            df_rank['Score_ROE_TTM'] = (df_rank['ROE_TTM'] / m_roe) * 100
            df_rank['Score_ROE_5Y'] = (df_rank['ROE_5Y'] / m_roe5) * 100
            df_rank['Score_EQ'] = (df_rank['Equity_Ratio_Current'] / m_eq) * 100
            
            for col in df_rank.columns:
                if col.startswith('Score_'):
                    df_rank[col] = df_rank[col].clip(upper=300)

            df_rank['Total_Score'] = (df_rank['Score_PB'] * 0.30) + (df_rank['Score_PE'] * 0.20) + \
                                     (df_rank['Score_ROE_TTM'] * 0.20) + (df_rank['Score_ROE_5Y'] * 0.15) + \
                                     (df_rank['Score_EQ'] * 0.15)
        else:
            m_roic = medians.get('median_roic', 0.10)
            if m_roic is None or m_roic < 0.01: m_roic = 0.01
            m_roic_ttm = medians.get('median_roic_ttm', 0.10)
            if m_roic_ttm is None or m_roic_ttm < 0.01: m_roic_ttm = 0.01
            m_value = medians.get('median_value', 10.0)
            if m_value is None or m_value < 0.01: m_value = 0.01
            m_cfo = medians.get('median_cfo', 1.0)
            if m_cfo is None or m_cfo < 0.01: m_cfo = 0.01
            m_cfo_ttm = medians.get('median_cfo_ttm', 1.0)
            if m_cfo_ttm is None or m_cfo_ttm < 0.01: m_cfo_ttm = 0.01
            m_de = medians.get('median_de', 1.0)
            if m_de is None or m_de < 0.01: m_de = 0.01
            m_de_curr = medians.get('median_de_curr', 1.0)
            if m_de_curr is None or m_de_curr < 0.01: m_de_curr = 0.01

            df_rank['Score_ROIC'] = (df_rank['ROIC_5Y'] / m_roic) * 100
            df_rank['Score_ROIC_TTM'] = (df_rank['ROIC_TTM'] / m_roic_ttm) * 100
            df_rank['Score_Value'] = (df_rank['Value_Ratio'] / m_value) * 100
            
            df_rank['Score_CFO'] = (df_rank['CFO_Quality'].clip(upper=3.0) / m_cfo) * 100
            df_rank.loc[df_rank['CFO_Quality'] < 0, 'Score_CFO'] = 0
            df_rank['Score_CFO_TTM'] = (df_rank['CFO_Quality_TTM'].clip(upper=3.0) / m_cfo_ttm) * 100
            df_rank.loc[df_rank['CFO_Quality_TTM'] < 0, 'Score_CFO_TTM'] = 0
            
            df_rank['Score_DE'] = np.maximum(0, 2 - (df_rank['DE_5Y'] / m_de)) * 100
            df_rank['Score_DE_Current'] = np.maximum(0, 2 - (df_rank['DE_Current'] / m_de_curr)) * 100
            
            for col in df_rank.columns:
                if col.startswith('Score_'):
                    df_rank[col] = df_rank[col].clip(upper=300)

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

        if obj is None:
            return None
        
        if isinstance(obj, dict):
            return {k: sanitize(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [sanitize(v) for v in obj]
            
        if isinstance(obj, bool):
            return obj
            
        try:
            if pd.isna(obj):
                return None
        except Exception:
            pass
            
        try:
            if isinstance(obj, (float, np.floating)):
                if np.isinf(obj) or np.isnan(obj):
                    return None
                return float(obj)
            elif isinstance(obj, (int, np.integer)):
                return int(obj)
        except Exception:
            pass
            
        return obj
        
    return sanitize(result_dict)
