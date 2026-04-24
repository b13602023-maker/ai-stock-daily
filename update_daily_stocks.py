import json
import datetime
import os
import yfinance as yf
import google.generativeai as genai

# 設定你的 AI API Key (這裡以 Google Gemini 為例)
API_KEY = "AIzaSyCjcbrfixWvGmTiTtdZoS2GfvaRY6_5wEY"
genai.configure(api_key=API_KEY)

def fetch_market_summary():
    # 這裡可以串接 FinMind, 證交所 API 或 yfinance 抓取大盤或熱門股數據
    # 為了示範，我們抓取台灣加權指數 (TAIEX) 的近期表現作為 AI 參考背景
    taiex = yf.Ticker("^TWII")
    hist = taiex.history(period="5d")
    return f"近期台股大盤走勢：\n{hist['Close'].to_string()}"

def get_ai_recommendations(market_data):
    # 設定 AI 模型
    model = genai.GenerativeModel('gemini-pro')
    
    # 精準的 Prompt 讓 AI 輸出我們需要的 JSON 格式
    prompt = f"""
    你現在是一位專業的台灣股市分析師。請根據目前的市場趨勢，推薦 3 檔今日值得關注的台灣股票。
    市場參考資料：{market_data}
    
    請務必以嚴格的 JSON 陣列格式輸出，不要包含任何其他文字。格式如下：
    [
        {{
            "symbol": "股票代號",
            "name": "股票名稱",
            "reason": "詳細的推薦理由（基本面、籌碼面或技術面）",
            "entry_timing": "適合進場的時機（例如：開盤走低時、突破月線時）",
            "entry_price": "建議進場價格區間",
            "exit_price": "建議停利/停損價格區間"
        }}
    ]
    """
    
    response = model.generate_content(prompt)
    try:
        # 清理字串並解析 JSON
        result_text = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(result_text)
    except Exception as e:
        print("AI 輸出解析失敗:", e)
        return []

def main():
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    print(f"開始更新 {today_str} 的台股推薦資料...")
    
    market_data = fetch_market_summary()
    recommendations = get_ai_recommendations(market_data)
    
    # 準備存檔的資料結構
    output_data = {
        "date": today_str,
        "recommendations": recommendations
    }
    
    # 將結果存成 JSON 檔案，供前端網頁讀取
    with open('daily_stocks.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
        
    print("資料更新完成，已儲存至 daily_stocks.json")

if __name__ == "__main__":
    main()
