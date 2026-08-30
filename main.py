from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import quant_screener
import os
from vnstock.core import setup_api_key

# Tự động setup API Key (hoặc dùng key do user cung cấp)
api_key = os.environ.get("VNSTOCK_API_KEY", "vnstock_8ac7b28e7fa8d51e76451f1fd5e43d2f")
if api_key:
    try:
        setup_api_key(api_key)
    except Exception as e:
        print(f"Loi khi setup API Key: {e}")

app = FastAPI(title="Exceptional Trader API")

from fastapi.responses import PlainTextResponse
from starlette.middleware.base import BaseHTTPMiddleware
import traceback

class CatchAllMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        try:
            return await call_next(request)
        except Exception as e:
            return PlainTextResponse(f"SUPER_ERROR: {traceback.format_exc()}", status_code=500)

app.add_middleware(CatchAllMiddleware)

@app.get("/api/sectors")
def get_sectors():
    try:
        sectors = quant_screener.get_available_sectors()
        return {"status": "success", "sectors": sectors}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import BackgroundTasks

@app.get("/api/screener")
def run_screener(sector: str, background_tasks: BackgroundTasks):
    try:
        import os, json
        from datetime import datetime
        safe_sector = "".join([c if c.isalnum() else "_" for c in sector])
        today = datetime.now().strftime("%Y-%m-%d")
        screener_cache_file = os.path.join("cache", f"screener_{safe_sector}_{today}.json")
        
        if os.path.exists(screener_cache_file):
            with open(screener_cache_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
                return {"status": "success", "data": results}
        else:
            # Run in background to prevent Render 100s timeout
            background_tasks.add_task(quant_screener.run_screener_for_sector, sector)
            return {"status": "syncing", "data": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

import json
from pydantic import BaseModel
from typing import Dict, List
import subprocess

@app.get("/api/config/sectors")
def get_config_sectors():
    try:
        if os.path.exists("sectors_config.json"):
            with open("sectors_config.json", "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class SectorConfig(BaseModel):
    config: Dict[str, List[str]]

@app.post("/api/config/sectors")
def update_config_sectors(payload: SectorConfig):
    try:
        cleaned_config = {}
        for group, tickers in payload.config.items():
            if len(tickers) > 20:
                raise HTTPException(status_code=400, detail=f"Nhóm '{group}' vượt quá 20 mã cổ phiếu.")
            cleaned_config[group.strip()] = [t.upper().strip() for t in tickers if t.strip()]
            
        with open("sectors_config.json", "w", encoding="utf-8") as f:
            json.dump(cleaned_config, f, ensure_ascii=False, indent=4)
        return {"status": "success"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/config/sync")
def sync_data():
    try:
        subprocess.Popen(["python", "cron_cache.py"])
        return {"status": "success", "message": "Đã kích hoạt đồng bộ nền."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/report")
def get_report(ticker: str, peers: str = "", taxRate: float = 0.2):
    print(f"API CALL: /api/report?ticker={ticker}&peers={peers}&taxRate={taxRate}")
    try:
        if not ticker:
            return {"status": "error", "detail": "Thiếu mã cổ phiếu."}
        
        ticker = ticker.upper().strip()
        result = quant_screener.get_comparative_report(ticker, peers, tax_rate_fallback=taxRate)
        
        if result.get('status') == 'error':
            return result
            
        import json
        try:
            # Force serialization here to catch any ValueError/TypeError from NaN/Infinity
            # BEFORE it hits FastAPI's internal JSONResponse which causes the 500 string
            safe_json_string = json.dumps(result, allow_nan=False)
            safe_result = json.loads(safe_json_string)
        except Exception as json_err:
            return {"status": "error", "detail": f"Lỗi chuyển đổi dữ liệu (Serialization): {str(json_err)}"}
            
        return {"status": "success", "data": safe_result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Phục vụ index.html mặc định từ thư mục public
@app.get("/")
def read_root():
    return FileResponse("public/index.html")

@app.get("/compare")
def read_compare():
    return FileResponse("public/compare.html")

@app.get("/admin")
def read_admin():
    return FileResponse("public/admin.html")

# Phục vụ các file tĩnh chỉ từ thư mục public (ẩn source code backend)
app.mount("/", StaticFiles(directory="public"), name="static")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
