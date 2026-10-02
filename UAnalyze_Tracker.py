import os
import requests
from playwright.sync_api import sync_playwright
from datetime import datetime
from zoneinfo import ZoneInfo

# ==========================================
# 參數與環境變數設定
# ==========================================
LINE_CHANNEL_TOKEN = os.environ.get("LINE_CHANNEL_TOKEN", "")
LINE_USER_ID = os.environ.get("LINE_USER_ID", "")

# 目標儀表板網址
TARGET_URL = "https://pro.uanalyze.com.tw/lab/dashboard/45166"

# 儲存登入 Cookie 的本地資料夾
USER_DATA_DIR = "./playwright_profile"

def send_line_message(text):
    """發送 LINE 通知"""
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_TOKEN}"
    }
    data = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": text}]
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        print("LINE 通知發送成功！")
    else:
        print(f"LINE 發送失敗: {response.text}")

def fetch_table_stocks():
    """抓取優分析表格中的所有股票與摘要資訊"""
    stock_items = []
    
    with sync_playwright() as p:
        browser_context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,  # 測試時保持 False 以便觀察畫面
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        
        page = browser_context.pages[0]

        try:
            print(f"前往目標網址: {TARGET_URL}")
            page.goto(TARGET_URL)
            
            # 等待頁面與表格資料完全載入
            print("等待表格資料載入中...")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(5000) # 給予 5 秒渲染緩衝

            # 定位表格中的每一列資料 (根據優分析常見的表格結構進行選取)
            # 這裡我們尋找包含股票代號與名稱的列
            rows = page.locator("tr")
            row_count = rows.count()
            print(f"總共掃描到 {row_count} 個表格列...")

            for i in range(row_count):
                row = rows.nth(i)
                text = row.inner_text()
                
                # 過濾並篩選出包含股票資料的列 (可根據畫面上的欄位特徵過濾)
                # 這裡抓取包含具體內容的行
                if text.strip():
                    stock_items.append(text.strip())
                    
        except Exception as e:
            print(f"執行過程中發生錯誤: {e}")
        finally:
            browser_context.close()
            
    return stock_items

def main():
    now_tw = datetime.now(ZoneInfo("Asia/Taipei"))
    print(f"--- 啟動優分析全清單抓取程式 ({now_tw.strftime('%Y-%m-%d %H:%M')}) ---")
    
    items = fetch_table_stocks()
    
    if items:
        # 組合訊息，限制傳送長度避免超過 LINE 單則訊息限制
        message = f"【優分析選股清單更新 - {now_tw.strftime('%m/%d %H:%M')}】\n\n"
        for item in items[:15]:  # 預設取前 15 筆避免字數過多
            message += f"• {item}\n-------------------\n"
            
        print("\n準備發送以下訊息至 LINE：")
        print(message)
        
        if LINE_CHANNEL_TOKEN and LINE_USER_ID:
            send_line_message(message)
        else:
            print("未偵測到 LINE 環境變數，跳過發送。")
    else:
        print("今日未能抓取到任何表格資料。")

if __name__ == "__main__":
    main()