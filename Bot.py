import json
import telebot
from flask import Flask, request
import threading
from telebot import types
from aliexpress_api import AliexpressApi, models
import re
import os
from urllib.parse import urlparse, parse_qs
import urllib.parse
import requests
from dotenv import load_dotenv

# טעינת משתני סביבה מקובץ .env
load_dotenv()

# אתחול הבוט עם הטוקן
TELEGRAM_TOKEN_BOT = os.getenv('TELEGRAM_BOT_TOKEN')
ALIEXPRESS_API_PUBLIC = os.getenv('ALIEXPRESS_API_PUBLIC')
ALIEXPRESS_API_SECRET = os.getenv('ALIEXPRESS_API_SECRET')

# בדיקה אם משתני הסביבה הנדרשים מוגדרים
if not TELEGRAM_TOKEN_BOT:
    print("❌ שגיאה: משתנה הסביבה TELEGRAM_BOT_TOKEN אינו מוגדר!")
    exit(1)

if not ALIEXPRESS_API_PUBLIC or not ALIEXPRESS_API_SECRET:
    print("❌ שגיאה: משתני הסביבה ALIEXPRESS_API_PUBLIC או ALIEXPRESS_API_SECRET אינם מוגדרים!")
    exit(1)

bot = telebot.TeleBot(TELEGRAM_TOKEN_BOT)

# אתחול ה-API של עליאקספרס
try:
    aliexpress = AliexpressApi(ALIEXPRESS_API_PUBLIC, ALIEXPRESS_API_SECRET,
                               models.Language.HE, models.Currency.ILS, 'telegramBot')
    print("ה-API של AliExpress אותחל בהצלחה.")
except Exception as e:
    print(f"שגיאה באתחול ה-API של AliExpress: {e}")

# הגדרת מקלדות (Keyboards)
keyboardStart = types.InlineKeyboardMarkup(row_width=1)
btn1 = types.InlineKeyboardButton("⭐️ דף בדיקה ואיסוף נקודות יומי ⭐️", url="https://s.click.aliexpress.com/e/_DdwUZVd")
btn2 = types.InlineKeyboardButton("⭐️ הנחת מטבעות על מוצרים בעגלה 🛒⭐️", callback_data='click')
btn3 = types.InlineKeyboardButton("❤️ הצטרפו לערוץ לעוד מבצעים ❤️", url="https://t.me/ShopAliExpressMaroc")
btn4 = types.InlineKeyboardButton("🎬 צפו כיצד הבוט עובד 🎬", url="https://t.me/ShopAliExpressMaroc/9")
btn5 = types.InlineKeyboardButton("💰 הורד את אפليקציית עליאקספרס וקבל בונוס של 5$ 💰", url="https://a.aliexpress.com/_mtV0j3q")
keyboardStart.add(btn1, btn2, btn3, btn4)

keyboard = types.InlineKeyboardMarkup(row_width=1)
btn1 = types.InlineKeyboardButton("⭐️ דף בדיקה ואיסוף נקודות יומי ⭐️", url="https://s.click.aliexpress.com/e/_DdwUZVd")
btn2 = types.InlineKeyboardButton("⭐️ הנחת מטבעות על מוצרים בעגלה 🛒⭐️", callback_data='click')
btn3 = types.InlineKeyboardButton("❤️ הצטרפו לערוץ לעוד מבצעים ❤️", url="https://t.me/ShopAliExpressMaroc")
keyboard.add(btn1, btn2, btn3)

keyboard_games = types.InlineKeyboardMarkup(row_width=1)
btn1 = types.InlineKeyboardButton("⭐️ דף בדיקה ואיסוף נקודות יומי ⭐️", url="https://s.click.aliexpress.com/e/_DdwUZVd")
btn2 = types.InlineKeyboardButton("⭐️ משחק Merge boss ⭐️", url="https://s.click.aliexpress.com/e/_DlCyg5Z")
btn3 = types.InlineKeyboardButton("⭐️ משחק Fantastic Farm ⭐️", url="https://s.click.aliexpress.com/e/_DBBkt9V")
btn4 = types.InlineKeyboardButton("⭐️ משחק היפוך קלפים Flip ⭐️", url="https://s.click.aliexpress.com/e/_DdcXZ2r")
btn5 = types.InlineKeyboardButton("⭐️ משחק GoGo Match ⭐️", url="https://s.click.aliexpress.com/e/_DDs7W5D")
keyboard_games.add(btn1, btn2, btn3, btn4, btn5)

# פונקציה לקבלת שער חליפין מ-USD ל-ILS
def get_usd_to_local_rate():
    try:
        response = requests.get('https://api.exchangerate-api.com/v4/latest/USD')
        data = response.json()
        return data['rates']['ILS']
    except Exception as e:
        print(f"שגיאה בהבאת שער החליפין: {e}")
        return None

# פונקציה למעקב אחרי הפניות (Redirects) וקבלת ה-URL הסופי
def resolve_full_redirect_chain(link):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    }
    try:
        session_req = requests.Session()
        response = session_req.get(link, allow_redirects=True, timeout=10, headers=headers)
        final_url = response.url
        print(f"🔗 קישור שפוענח: {link} -> {final_url}")
        
        if "star.aliexpress.com" in final_url:
            parsed_url = urlparse(final_url)
            params = parse_qs(parsed_url.query)
            if 'redirectUrl' in params:
                return params['redirectUrl'][0]
        return final_url
    except requests.RequestException as e:
        print(f"❌ שגיאה בפענוח שרשרת ההפניות עבור הקישור {link}: {e}")
        return link

# פונקציה לחילוץ מזהה המוצר (Product ID) מהקישור
def extract_product_id(link):
    print(f"🔍 מחלץ מזהה מוצר מתוך: {link}")
    resolved_link = resolve_full_redirect_chain(link)
    
    product_id_pattern = r'/item/(\d+)\.html'
    match = re.search(product_id_pattern, resolved_link)
    if match:
        return match.group(1)
    
    coin_page_pattern = r'productIds=(\d+)'
    coin_match = re.search(coin_page_pattern, resolved_link)
    if coin_match:
        return coin_match.group(1)
    
    product_id_pattern_alt = r'(\d{13,})'
    match_alt = re.search(product_id_pattern_alt, resolved_link)
    if match_alt:
        return match_alt.group(1)
    
    return None

def generate_coin_affiliate_link(product_id):
    try:
        coin_index_url = f"https://m.aliexpress.com/p/coin-index/index.html?_immersiveMode=true&from=syicon&productIds={product_id}"
        affiliate_link = aliexpress.get_affiliate_links(coin_index_url)
        return affiliate_link[0].promotion_link
    except Exception as e:
        print(f"❌ שגיאה ביצירת קישור שותפים מטבעות: {e}")
        return None

def generate_bundle_affiliate_link(product_id, original_link):
    try:
        bundle_url = f'https://star.aliexpress.com/share/share.htm?platform=AE&businessType=ProductDetail&redirectUrl={original_link}?sourceType=560&aff_fcid='
        affiliate_link = aliexpress.get_affiliate_links(bundle_url)
        return affiliate_link[0].promotion_link
    except Exception as e:
        print(f"❌ שגיאה ביצירת קישור שותפים באנדל: {e}")
        return None

@bot.message_handler(commands=['start'])
def welcome_user(message):
    bot.send_message(
        message.chat.id,
        "ברוכים הבאים👋 \n" 
        "אני בוט עלי אקספרס! העתיקו את קישור המוצר והדبيקו אותו כאן 👇 ותקבלו את כל הצעות המחיר הזולות ביותר 🔥",
        reply_markup=keyboardStart)

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    try:
        print(f"הודעה התקבלה: {message.text}")
        link = extract_link(message.text)
        sent_message = bot.send_message(message.chat.id, 'אנא המתן רגע, מכין את המבצעים עבורך ⏳')
        message_id = sent_message.message_id
        if link and "aliexpress.com" in link and not ("p/shoppingcart" in message.text.lower()):
            if "availableProductShopcartIds".lower() in message.text.lower():
                get_affiliate_shopcart_link(link, message)
                return
            get_affiliate_links(message, message_id, link)
        else:
            bot.delete_message(message.chat.id, message_id)
            bot.send_message(message.chat.id, "הקישור אינו תקין! ודא שזהו קישור למוצר ונסה שנית.\n"
                                              "אנא שלח את <b>הקישור בלבד</b> ללא כותרת או טקסט נוסף.",
                             parse_mode='HTML')
    except Exception as e:
        print(f"שגיאה בהנדלר echo_all: {e}")

def extract_link(text):
    link_pattern = r'(https?://[^\s<>"\'“]+)'
    links = re.findall(link_pattern, text)
    if links:
        return links[0]
    return None

def get_affiliate_links(message, message_id, link):
    try:
        resolved_link = resolve_full_redirect_chain(link)
        if not resolved_link:
            bot.delete_message(message.chat.id, message_id)
            bot.send_message(message.chat.id, "❌ לא הצלחתי לפענח את הקישור! وדא שהוא תקין ונסה שוב.")
            return

        product_id = extract_product_id(resolved_link)
        if not product_id:
            bot.delete_message(message.chat.id, message_id)
            bot.send_message(message.chat.id, "❌ לא הצלחתי לחלץ את מזהه המוצר מהקישור.")
            return

        coin_affiliate_link = generate_coin_affiliate_link(product_id)
        bundle_affiliate_link = generate_bundle_affiliate_link(product_id, resolved_link)
        
        super_links = aliexpress.get_affiliate_links(
            f'https://star.aliexpress.com/share/share.htm?platform=AE&businessType=ProductDetail&redirectUrl={resolved_link}?sourceType=562&aff_fcid='
        )[0].promotion_link

        limit_links = aliexpress.get_affiliate_links(
            f'https://star.aliexpress.com/share/share.htm?platform=AE&businessType=ProductDetail&redirectUrl={resolved_link}?sourceType=561&aff_fcid='
        )[0].promotion_link

        try:
            product_details = aliexpress.get_products_details([
                product_id
            ], fields=["target_sale_price", "product_title", "product_main_image_url"])
            
            if product_details and len(product_details) > 0:
                # ניקוי המחיר מכל תו שאינו מספר או נקודה כדי למנוע קריסת float()
                raw_price = str(product_details[0].target_sale_price)
                cleaned_price = re.sub(r'[^\d.]', '', raw_price)
                price_pro = float(cleaned_price) if cleaned_price else 0.0
                
                title_link = product_details[0].product_title
                img_link = product_details[0].product_main_image_url
                
                exchange_rate = get_usd_to_local_rate()
                if exchange_rate:
                    price_pro_local = price_pro * exchange_rate
                    currency_suffix = "ש\"ח"
                else:
                    price_pro_local = price_pro
                    currency_suffix = "USD"
                
                bot.delete_message(message.chat.id, message_id)
                
                message_text = (
                    f" \n🛒 המוצר שלך הוא: 🔥 \n"
                    f" {title_link} 🛍 \n"
                    f" מחיר המוצר: "
                    f" {price_pro:.2f} דולר 💵 / {price_pro_local:.2f} {currency_suffix} 💵\n"
                    " \n השווה מחירים וקנה חכם 🔥 \n"
                )
                
                if coin_affiliate_link:
                    message_text += f"💰 מבצע מטבעות (מחיר סופי בקופה):\nקישור: {coin_affiliate_link} \n"
                if bundle_affiliate_link:
                    message_text += f"📦 מבצע באנדל (חבילות ומבצעים):\nקישור: {bundle_affiliate_link} \n"
                
                message_text += f"💎 מבצע סופר:\nקישור: {super_links} \n🔥 מבצע מוגבל:\nקישור: {limit_links} \n\n#AliExpressSaverBot ✅"
                
                bot.send_photo(message.chat.id, img_link, caption=message_text, reply_markup=keyboard)
            else:
                raise Exception("Product details empty")
        except Exception as e:
            print(f"שגיאה בהבאת פרטי מוצר, שולח פלבאק: {e}")
            bot.delete_message(message.chat.id, message_id)
            message_text = "השווה מחירים וקנה חכם 🔥 \n"
            if coin_affiliate_link:
                message_text += f"💰 מבצע מטבעות:\nקישור: {coin_affiliate_link} \n"
            if bundle_affiliate_link:
                message_text += f"📦 מבצע באנדל:\nקישור: {bundle_affiliate_link} \n"
            message_text += f"💎 מבצע סופר:\nקישור: {super_links} \n🔥 מבצע מוגבל:\nקישור: {limit_links} \n\n#AliExpressSaverBot ✅"
            bot.send_message(message.chat.id, message_text, reply_markup=keyboard)
    except Exception as e:
        print(f"שגיאה כללית ב-get_affiliate_links: {e}")
        bot.send_message(message.chat.id, "התרחسة שגיאה 🤷🏻‍♂️")

def build_shopcart_link(link):
    parsed_url = urlparse(link)
    params = parse_qs(parsed_url.query)
    shop_cart_link = "https://www.aliexpress.com/p/trade/confirm.html?"
    shop_cart_params = {
        "availableProductShopcartIds": ",".join(params.get("availableProductShopcartIds", [])),
        "extraParams": json.dumps({"channelInfo": {"sourceType": "620"}}, separators=(',', ':'))
    }
    return shop_cart_link + urllib.parse.urlencode(shop_cart_params)

def get_affiliate_shopcart_link(link, message):
    try:
        shopcart_link = build_shopcart_link(link)
        affiliate_link = aliexpress.get_affiliate_links(shopcart_link)[0].promotion_link
        text2 = f"זהו קישור ההנחה לעגלת הקניות שלך \n{str(affiliate_link)}"
        img_link3 = "https://i.postimg.cc/1Xrk1RJP/Copy-of-Basket-aliexpress-telegram.png"
        bot.send_photo(message.chat.id, img_link3, caption=text2)
    except Exception as e:
        print(f"שגיאה ב-get_affiliate_shopcart_link: {e}")
        bot.send_message(message.chat.id, "התרחשה שגיאה 🤷🏻‍♂️")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    try:
        if call.data == 'click':
            link = 'https://www.aliexpress.com/p/shoppingcart/index.html?'
            get_affiliate_shopcart_link(link, call.message)
        else:
            img_link2 = "https://i.postimg.cc/VvmhgQ1h/Basket-aliexpress-telegram.png"
            bot.send_photo(call.message.chat.id, img_link2,
                           caption="קישורים למשחקי איסוף מטבעות. היכנסו אליהם מדי יום לקבלת מקסימום מטבעות 👇",
                           reply_markup=keyboard_games)
    except Exception as e:
        print(f"שגיאה ב-handle_callback_query: {e}")

# אפליקציית Flask לניהול Webhook וחיבור הפורט של Render
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == 'POST':
        json_str = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return 'OK', 200

def run_flask():
    # פתרון קריטי ל-Render: שימוש בפורט הדינמי שהמערכת מקצה
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    webhook_url = os.getenv('WEBHOOK_URL')
    
    if webhook_url:
        print("🚀 מפעיל את הבוט במצב Webhook...")
        threading.Thread(target=run_flask).start()
        try:
            bot.remove_webhook()
            bot.set_webhook(url=webhook_url)
            print(f"✅ ה-Webhook הוגדר לכתובת: {webhook_url}")
        except Exception as e:
            print(f"❌ שגיאה בהגדרת ה-Webhook: {e}")
    else:
        print("🚀 מפעיל את הבוט במצב Polling (פיתוח)...")
        try:
            bot.remove_webhook()
            bot.infinity_polling(none_stop=True, timeout=10, long_polling_timeout=5)
        except Exception as e:
            print(f"❌ שגיאה במצב Polling: {e}")
