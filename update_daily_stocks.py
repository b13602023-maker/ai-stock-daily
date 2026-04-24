import os
import json
import yfinance as yf
import google.generativeai as genai
from datetime import datetime

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

def get_real_stock_data(symbol):
    """抓取真實股價，並自動過濾多餘的 .TW"""
    try:
        # 防呆機制 1：強制把 AI 給的 .TW 或 .TWO 拔掉，確保代號乾淨
        clean_symbol = str(symbol).replace('.TW', '').replace('.TWO', '').strip()
        ticker = yf.Ticker(f"{clean_symbol}.TW")
        info = ticker.info
        
        # 抓取最新價格
        current_price = info.get('regularMarketPrice') or info.get('currentPrice')
        if not current_price:
            hist = ticker.history(period="1d")
            if not hist.empty:
                current_price = hist['Close'].iloc[-1]
            else:
                return None
        
        return {
            "price": round(current_price, 2),
            "link": f"https://tw.stock.yahoo.com/quote/{clean_symbol}.TW"
        }
    except Exception as e:
        print(f"❌ 抓取 {symbol} 股價失敗: {e}")
        return None

def get_ai_recommendations(market_data):
    valid_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    chosen_model = next((m for m in valid_models if 'flash' in m), valid_models[0])
    model = genai.GenerativeModel(chosen_model.replace('models/', ''))
    
    # 防呆機制 2：給 AI 最嚴格的範例，禁止它亂加東西
    prompt = f"""
    市場狀況：{market_data}
    請推薦 3 檔台灣股票，包含：一檔低價股(<50)、一檔中價股(50-150)、一檔高價股(>150)。
    
    絕對只能輸出 JSON 陣列，不要任何標記或文字！範例如下：
    [
        {{"symbol": "2330", "name": "台積電", "type": "高價股", "reason": "理由"}},
        {{"symbol": "2308", "name": "台達電", "type": "中價股", "reason": "理由"}},
        {{"symbol": "2884", "name": "玉山金", "type": "低價股", "reason": "理由"}}
    ]
    注意：symbol 只能是數字，絕對不要加上 .TW！
    """
    
    print("⏳ 正在等待 AI 回應...")
    response = model.generate_content(prompt)
    print("🤖 AI 原始回應：\n", response.text)
    
    try:
        clean_text = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(clean_text)
    except Exception as e:
        print("❌ JSON 解析失敗:", e)
        return []

def main():
    # 抓取大盤資訊
    try:
        twii = yf.Ticker("^TWII").history(period="1d")
        market_info = f"今日台盤指數: {twii['Close'].iloc[-1]:.2f}"
    except:
        market_info = "無法取得今日大盤資訊"

    # AI 選股
    recommendations = get_ai_recommendations(market_info)
    
    # 結合真實數據
    final_data = []
    for item in recommendations:
        real_info = get_real_stock_data(item.get('symbol', ''))
        if real_info:
            item['current_price'] = real_info['price']
            item['url'] = real_info['link']
            item['tp'] = round(real_info['price'] * 1.1, 2)
            item['sl'] = round(real_info['price'] * 0.95, 2)
            final_data.append(item)
        else:
            print(f"⚠️ 略過 {item.get('name')}: 找不到真實股價")

    # 儲存
    output = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "stocks": final_data
    }
    
    with open('daily_stocks.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=4)
    print(f"✅ 成功儲存了 {len(final_data)} 檔股票資料！")

if __name__ == "__main__":
    main()
