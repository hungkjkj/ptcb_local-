import time
from datetime import datetime, timedelta
import quant_screener

def run_cache():
    import json
    import os
    sectors = ["Ngân hàng", "Chứng khoán", "Bán lẻ", "Công nghệ thông tin", "Xây dựng và Vật liệu"]
    try:
        if os.path.exists("sectors_config.json"):
            with open("sectors_config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
                if config:
                    sectors = list(config.keys())
    except:
        pass
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Bắt đầu tiến trình tạo cache tự động cho các ngành: {sectors}...")
    for s in sectors:
        print(f"  -> Đang cache dữ liệu ngành: {s}...")
        try:
            quant_screener.run_screener_for_sector(s, force_update=True)
            print(f"  -> Xong {s}. Nghỉ 60 giây để tránh Rate Limit...")
            time.sleep(60)
        except Exception as e:
            print(f"  -> Lỗi khi cache {s}: {e}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Tiến trình tạo cache hoàn tất.")

def main():
    print("Khởi động Cron Cache...")
    run_cache()
    print("Đã chạy xong! Script sẽ thoát. (Thích hợp chạy qua Render Cron Job hoặc Windows Task Scheduler)")

if __name__ == "__main__":
    main()
