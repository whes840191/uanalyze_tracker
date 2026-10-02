import os
import requests
from playwright.sync_api import sync_playwright
from datetime import datetime
from zoneinfo import ZoneInfo

# ==========================================
# 參數與環境變數設定
# ==========================================
# 從環境變數讀取 LINE Token，若無則使用預設字串 (請確認已在終端機設定)
LINE_CHANNEL_TOKEN = os.environ.get("LINE_CHANNEL_TOKEN", "你的LINE_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID", "你的LINE_USER_ID")

# 登入頁與目標儀表板
LOGIN_URL = "https://pro.uanalyze.com.tw/login"
TARGET_URL = "https://pro.uanalyze.com.tw/lab/dashboard/45166"

# 我們要追蹤的核心標的清單
TARGET_STOCKS = ["2360 致茂", "8027 鈦昇"]

# 儲存 Cookie 的本地資料夾路徑
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

def fetch_watchlist_with_cookie():
    """載入 Cookie，登入並擷取追蹤標的"""
    extracted_stocks = []
    
    with sync_playwright() as p:
        # 啟動具備狀態記憶的瀏覽器
        browser_context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,  # ★ 第一次測試請保持 False 以便手動登入
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        
        page = browser_context.pages[0]

        try:
            print("前往優分析登入頁面...")
            page.goto(LOGIN_URL)
            
            print("請在彈出的瀏覽器中，使用 Google 帳號完成登入。")
            print("等待登入中 (最多等待 60 秒)...")
            
            # 給予 60 秒的時間讓你手動登入，登入成功後通常會自動跳轉
            # 如果 60 秒內網址包含 dashboard，程式就會繼續
            try:
                page.wait_for_url("**/dashboard/**", timeout=60000)
                print("偵測到登入成功，已進入儀表板！")
            except:
                print("等待時間結束或已經登入，強制導向目標儀表板...")
            
            # 確保前往我們指定的 45166 儀表板
            page.goto(TARGET_URL)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(3000) # 給予右側清單 3 秒的渲染緩衝

            print("開始掃描右側 Dingo 選股清單...")
            for stock in TARGET_STOCKS:
                # 尋找畫面上是否包含該股票文字
                element = page.get_by_text(stock, exact=False)
                
                if element.count() > 0 and element.first.is_visible():
                    extracted_stocks.append(stock)
                    print(f"成功找到追蹤標的：{stock}")
                    
        except Exception as e:
            print(f"執行過程中發生錯誤: {e}")
        finally:
            # 確實關閉瀏覽器以儲存 Cookie 狀態
            browser_context.close()
            
    return extracted_stocks

def main():
    now_tw = datetime.now(ZoneInfo("Asia/Taipei"))
    print(f"--- 啟動優分析 Cookie 追蹤程式 ({now_tw.strftime('%Y-%m-%d')}) ---")
    
    stocks = fetch_watchlist_with_cookie()
    
    if stocks:
        message = f"【優分析追蹤標的狀態 - {now_tw.strftime('%m/%d')}】\n\n目前監控中的核心持股共 {len(stocks)} 檔：\n"
        for stock in stocks:
            message += f"• {stock}\n"
            
        print("\n準備發送以下訊息至 LINE：")
        print(message)
        send_line_message(message)
    else:
        print("今日未能抓取到任何指定的追蹤標的。")

if __name__ == "__main__":
    main()