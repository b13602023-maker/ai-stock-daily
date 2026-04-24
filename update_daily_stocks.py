import os
import json
import yfinance as yf
import google.generativeai as genai
from datetime import datetime

# 設定 API Key
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

def get_real_stock_data(symbol):
    """使用 yfinance 抓取真實股價與連結"""
    try:
        ticker = yf.Ticker(f"{symbol}.TW")
        info = ticker.info
        # 抓取最新收盤價或現價
        current_price = info.get('regularMarketPrice') or info.get('currentPrice')
        if not current_price:
            # 備用方案：抓取歷史紀錄最後一筆
            hist = ticker.history(period="1d")
            current_price = hist['Close'].iloc[-1]
        
        return {
            "price": round(current_price, 2),
            "link": f"https://tw.stock.yahoo.com/quote/{symbol}.TW"
        }
    except:
        return None

def get_ai_recommendations(market_data):
    valid_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    chosen_model = next((m for m in valid_models if 'flash' in m), valid_models[0])
    model = genai.GenerativeModel(chosen_model.replace('models/', ''))
    
    # 修改 Prompt：要求 AI 推薦不同價位的股票代號
    prompt = f"""
    市場狀況：{market_data}
    請根據以上資訊，推薦 3 檔台灣股票，必須包含：
    1. 一檔低價股 (50元以下)
    2. 一檔中價股 (50-150元)
    3. 一檔高價股 (150元以上)
    
    請僅輸出 JSON 格式，不要包含解釋文字。格式如下：
    [
        {{"symbol": "代號", "name": "名稱", "type": "低價股", "reason": "理由"}},
        {{"symbol": "代號", "name": "名稱", "type": "中價股", "reason": "理由"}},
        {{"symbol": "代號", "name": "名稱", "type": "高價股", "reason": "理由"}}
    ]
    """
    
    response = model.generate_content(prompt)
    try:
        return json.loads(response.text.strip().replace('```json', '').replace('```', ''))
    except:
        return []

def main():
    # 1. 抓取大盤資訊
    twii = yf.Ticker("^TWII").history(period="1d")
    market_info = f"今日台盤指數: {twii['Close'].iloc[-1]:.2 dream}"
    
    # 2. 讓 AI 選股 (只拿代號與理由)
    recommendations = get_ai_recommendations(market_info)
    
    final_data = []
    # 3. 針對 AI 選出的股票，抓取「真實數據」
    for item in recommendations:
        real_info = get_real_stock_data(item['symbol'])
        if real_info:
            # 結合 AI 的理由與真實的價格/連結
            item['current_price'] = real_info['price']
            item['url'] = real_info['link']
            # 自動計算停利停損 (真實價格的 +10% 和 -5%)
            item['tp'] = round(real_info['price'] * 1.1, 2)
            item['sl'] = round(real_info['price'] * 0.95, 2)
            final_data.append(item)

    # 4. 儲存結果
    output = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "stocks": final_data
    }
    
    with open('daily_stocks.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=4)
    print("✅ 資料更新成功，包含真實股價與連結！")

if __name__ == "__main__":
    main()
