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
    print("אנא הגדר את משתנה הסביבה או צור קובץ .env עם הטוקן של הבוט שלך.")
    exit(1)

if not ALIEXPRESS_API_PUBLIC or not ALIEXPRESS_API_SECRET:
    print("❌ שגיאה: משתני הסביבה ALIEXPRESS_API_PUBLIC ו-ALIEXPRESS_API_SECRET אינם מוגדרים!")
    print("אנא הגדר את משתני הסביבה או צור קובץ .env עם פרטי ה-API שלך.")
    exit(1)

bot = telebot.TeleBot(TELEGRAM_TOKEN_BOT)

# אתחול AliExpress API (מוגדר לעברית ולמטבע אירו כבסיס לפני המרה)
try:
    aliexpress = AliexpressApi(ALIEXPRESS_API_PUBLIC, ALIEXPRESS_API_SECRET,
                               models.Language.HE, models.Currency.EUR, 'telegramBot')
    print("AliExpress API אותחל בהצלחה.")
except Exception as e:
    print(f"שגיאה באתחול AliExpress API: {e}")

# הגדרת מקלדות (כפתורי Inline) בעברית
keyboardStart = types.InlineKeyboardMarkup(row_width=1)
btn1 = types.InlineKeyboardButton("⭐️ דף בדיקה ואיסוף נקודות יומי ⭐️", url="https://s.click.aliexpress.com/e/_DdwUZVd")
btn2 = types.InlineKeyboardButton("⭐️ הנחת מטבעות על מוצרים בעגלה 🛒⭐️", callback_data='click')
btn3 = types.InlineKeyboardButton("❤️ הצטרפו לערוץ לעוד מבצעים ❤️", url="https://t.me/ShopAliExpressMaroc")
btn4 = types.InlineKeyboardButton("🎬 צפו כיצד הבוט עובד 🎬", url="https://t.me/ShopAliExpressMaroc/9")
btn5 = types.InlineKeyboardButton("💰 הורד את אפליקציית Aliexpress כאן וקבל בונוס של 5$ 💰", url="https://a.aliexpress.com/_mtV0j3q")
keyboardStart.add(btn1, btn2, btn3, btn4)

keyboard = types.InlineKeyboardMarkup(row_width=1)
btn1 = types.InlineKeyboardButton("⭐️ דף בדיקה ואיסוף נקודות יומי ⭐️", url="https://s.click.aliexpress.com/e/_DdwUZVd")
btn2 = types.InlineKeyboardButton("⭐️ הנחת מטבעות על מוצרים בעגלה 🛒⭐️", callback_data='click')
btn3 = types.InlineKeyboardButton("❤️ הצטרפו לערוץ לעוד מבצעים ❤️", url="https://t.me/ShopAliExpressMaroc")
keyboard.add(btn1, btn2, btn3)

keyboard_games = types.InlineKeyboardMarkup(row_width=1)
btn1 = types.InlineKeyboardButton("⭐️ דף בדיקה ואיסוף נקודות יומי ⭐️", url="https://s.click.aliexpress.com/e/_DdwUZVd")
btn2 = types.InlineKeyboardButton("⭐️ משחק Merge Boss ⭐️", url="https://s.click.aliexpress.com/e/_DlCyg5Z")
btn3 = types.InlineKeyboardButton("⭐️ משחק החווה (Fantastic Farm) ⭐️", url="https://s.click.aliexpress.com/e/_DBBkt9V")
btn4 = types.InlineKeyboardButton("⭐️ משחק היפוך קלפים Flip ⭐️", url="https://s.click.aliexpress.com/e/_DdcXZ2r")
btn5 = types.InlineKeyboardButton("⭐️ משחק GoGo Match ⭐️", url="https://s.click.aliexpress.com/e/_DDs7W5D")
keyboard_games.add(btn1, btn2, btn3, btn4, btn5)

# פונקציה לקבלת שער חליפין מ-USD ל-ILS (שקלים)
def get_usd_to_ils_rate():
    try:
        response = requests.get('https://api.exchangerate-api.com/v4/latest/USD')
        data = response.json()
        return data['rates']['ILS']
    except Exception as e:
        print(f"שגיאה בקבלת שער חליפין: {e}")
        return None

# פונקציה למעקב אחר הפניות וקבלת ה-URL הסופי
def resolve_full_redirect_chain(link):
    """Resolve all redirects to get the final URL"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/58.0.3029.110 Safari/537.36'
    }
    try:
        session_req = requests.Session()
        response = session_req.get(link, allow_redirects=True, timeout=10, headers=headers)
        final_url = response.url
        print(f"🔗 Resolved URL: {link} -> {final_url}")
        
        if "star.aliexpress.com" in final_url:
            parsed_url = urlparse(final_url)
            params = parse_qs(parsed_url.query)
            if 'redirectUrl' in params:
                redirect_url = params['redirectUrl'][0]
                print(f"🔗 Found redirectUrl: {redirect_url}")
                return redirect_url
        
        if "aliexpress.com/item" in final_url:
            return final_url
        elif "p/coin-index" in final_url:
            return final_url
        else:
            return final_url
    except requests.RequestException as e:
        print(f"❌ Error resolving redirect chain for link {link}: {e}")
        return link

# פונקציה לחילוץ מזהה מוצר מהקישור
def extract_product_id(link):
    """Extract product ID from AliExpress link (handles redirected/shortened links)"""
    print(f"🔍 Extracting product ID from: {link}")
    
    resolved_link = resolve_full_redirect_chain(link)
    print(f"🔗 Using resolved link: {resolved_link}")
    
    product_id_pattern = r'/item/(\d+)\.html'
    match = re.search(product_id_pattern, resolved_link)
    if match:
        print(f"✅ Extracted product ID (standard): {match.group(1)}")
        return match.group(1)
    
    coin_page_pattern = r'productIds=(\d+)'
    coin_match = re.search(coin_page_pattern, resolved_link)
    if coin_match:
        print(f"✅ Extracted product ID (coin-index): {coin_match.group(1)}")
        return coin_match.group(1)
    
    product_id_pattern_alt = r'(\d{13,})'
    match_alt = re.search(product_id_pattern_alt, resolved_link)
    if match_alt:
        print(f"✅ Extracted product ID (long format): {match_alt.group(1)}")
        return match_alt.group(1)
    
    print(f"❌ Could not extract product ID from: {resolved_link}")
    return None

# יצירת קישור שותפים מבוסס מטבעות מתוקן (ערוץ 620) שלא נזרק לעמוד הראשי
def generate_coin_affiliate_link(product_id):
    """Generate affiliate link using coin-index system for 620 channel"""
    try:
        standard_product_url = f"https://www.aliexpress.com/item/{product_id}.html"
        affiliate_link_data = aliexpress.get_affiliate_links(standard_product_url)
        
        if not affiliate_link_data or len(affiliate_link_data) == 0:
            return None
            
        base_affiliate_link = affiliate_link_data[0].promotion_link
        separator = "&" if "?" in base_affiliate_link else "?"
        coin_affiliate_link = f"{base_affiliate_link}{separator}sourceType=620&_immersiveMode=true&from=syicon"
        
        return coin_affiliate_link
    except Exception as e:
        print(f"❌ Error generating coin affiliate link for product {product_id}: {e}")
        return None

# יצירת קישור שותפים מבוסס חבילה (ערוץ 560)
def generate_bundle_affiliate_link(product_id, original_link):
    """Generate affiliate link using bundle system for 560 channel"""
    try:
        bundle_url = f'https://star.aliexpress.com/share/share.htm?platform=AE&businessType=ProductDetail&redirectUrl={original_link}?sourceType=560&aff_fcid='
        affiliate_link = aliexpress.get_affiliate_links(bundle_url)
        return affiliate_link[0].promotion_link
    except Exception as e:
        print(f"❌ Error generating bundle affiliate link for product {product_id}: {e}")
        return None

# פקודות והודעות בוט בעברית
@bot.message_handler(commands=['start'])
def welcome_user(message):
    print("Handling /start command")
    bot.send_message(
        message.chat.id,
        "ברוכים הבאים 👋 \n" 
        "אני בוט אליאקספרס שמסייע בהורדת מחירים ומציאת הדילים הטובים ביותר! העתיקו את קישור המוצר והדביקו אותו כאן 👇 ותקבלו את כל ההצעות הזולות ביותר למוצר 🔥",
        reply_markup=keyboardStart)

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    try:
        print(f"Message received: {message.text}")
        link = extract_link(message.text)
        sent_message = bot.send_message(message.chat.id, 'אנא המתינו רגע, המבצעים בדרך אליכם... ⏳')
        message_id = sent_message.message_id
        if link and "aliexpress.com" in link and not ("p/shoppingcart" in message.text.lower()):
            if "availableProductShopcartIds".lower() in message.text.lower():
                get_affiliate_shopcart_link(link, message)
                return
            get_affiliate_links(message, message_id, link)
        else:
            bot.delete_message(message.chat.id, message_id)
            bot.send_message(message.chat.id, "הקישור אינו תקין! ודא שמדובר בקישור למוצר ונסה שנית.\n"
                                             "שלח את <b>הקישור בלבד</b> ללא כותרת או טקסט נוסף.",
                             parse_mode='HTML')
    except Exception as e:
        print(f"Error in echo_all handler: {e}")

def extract_link(text):
    link_pattern = r'https?://\S+|www\.\S+'
    links = re.findall(link_pattern, text)
    if links:
        print(f"Extracted link: {links[0]}")
        return links[0]
    return None

def get_affiliate_links(message, message_id, link):
    try:
        resolved_link = resolve_full_redirect_chain(link)
        if not resolved_link:
            bot.delete_message(message.chat.id, message_id)
            bot.send_message(message.chat.id, "❌ לא הצלחתי לפענח את הקישור! בדוק את הקישור ונסה שנית.")
            return

        product_id = extract_product_id(resolved_link)
        if not product_id:
            bot.delete_message(message.chat.id, message_id)
            bot.send_message(message.chat.id, "❌ לא הצלחתי לחלץ את מזהה המוצר (Product ID) מהקישור.")
            return

        coin_affiliate_link = generate_coin_affiliate_link(product_id)
        bundle_affiliate_link = generate_bundle_affiliate_link(product_id, resolved_link)
        
        super_links = aliexpress.get_affiliate_links(
            f'https://star.aliexpress.com/share/share.htm?platform=AE&businessType=ProductDetail&redirectUrl={resolved_link}?sourceType=562&aff_fcid='
        )
        super_links = super_links[0].promotion_link

        limit_links = aliexpress.get_affiliate_links(
            f'https://star.aliexpress.com/share/share.htm?platform=AE&businessType=ProductDetail&redirectUrl={resolved_link}?sourceType=561&aff_fcid='
        )
        limit_links = limit_links[0].promotion_link

        try:
            product_details = aliexpress.get_products_details([
                product_id
            ], fields=["target_sale_price", "product_title", "product_main_image_url"])
            
            if product_details and len(product_details) > 0:
                print(f"Product details object: {json.dumps(product_details[0].__dict__, indent=2, ensure_ascii=False)}")
                price_pro = float(product_details[0].target_sale_price)
                title_link = product_details[0].product_title
                img_link = product_details[0].product_main_image_url
                
                exchange_rate = get_usd_to_ils_rate()
                if exchange_rate:
                    price_pro_ils = price_pro * exchange_rate
                else:
                    price_pro_ils = price_pro
                
                print(f"Product details: {title_link}, {price_pro}, {img_link}")
                bot.delete_message(message.chat.id, message_id)
                
                message_text = (
                    f" \n🛒 המוצר שלך: 🔥 \n"
                    f" {title_link} 🛍 \n"
                    f" מחיר המוצר: "
                    f" {price_pro:.2f} דולר 💵 / {price_pro_ils:.2f} ש\"ח 💵\n"
                    " \n השוו בין המחירים וקנו חכם 🔥 \n"
                )
                
                if coin_affiliate_link:
                    message_text += (
                        "💰 מבצע מטבעות (המחיר הסופי מופיע בתשלום): \n"
                        f"קישור: {coin_affiliate_link} \n"
                    )
                
                if bundle_affiliate_link:
                    message_text += (
                        "📦 דיל חבילה (מבצעים מגוונים): \n"
                        f"קישור: {bundle_affiliate_link} \n"
                    )
                
                message_text += (
                    f"💎 מבצע סופר (Super Deal): \n"
                    f"קישור: {super_links} \n"
                    f"🔥 הצעה מוגבלת בזמן: \n"
                    f"קישור: {limit_links} \n\n"
                    "#AliExpressSaverBot ✅"
                )
                
                bot.send_photo(message.chat.id,
                               img_link,
                               caption=message_text,
                               reply_markup=keyboard)
            else:
                bot.delete_message(message.chat.id, message_id)
                message_text = "השוו בין המחירים וקנו חכם 🔥 \n"
                
                if coin_affiliate_link:
                    message_text += (
                        "💰 מבצע מטבעות (המחיר הסופי מופיע בתשלום): \n"
                        f"קישור: {coin_affiliate_link} \n"
                    )
                
                if bundle_affiliate_link:
                    message_text += (
                        "📦 דיל חבילה (מבצעים מגוונים): \n"
                        f"קישור: {bundle_affiliate_link} \n"
                    )
                
                message_text += (
                    f"💎 מבצע סופר (Super Deal): \n"
                    f"קישור: {super_links} \n"
                    f"🔥 הצעה מוגבלת בזמן: \n"
                    f"קישור: {limit_links} \n\n"
                    "#AliExpressSaverBot ✅"
                )
                
                bot.send_message(message.chat.id, message_text, reply_markup=keyboard)
        except Exception as e:
            print(f"Error in get_affiliate_links inner try: {e}")
            bot.delete_message(message.chat.id, message_id)
            
            message_text = "השוו בין המחירים וקנו חכם 🔥 \n"
            
            if coin_affiliate_link:
                message_text += (
                    "💰 מבצע מטבעות (המחיר הסופי מופיע בתשלום): \n"
                    f"קישור: {coin_affiliate_link} \n"
                )
            
            if bundle_affiliate_link:
                message_text += (
                    "📦 דיל חבילה (מבצעים מגוונים): \n"
                    f"קישור: {bundle_affiliate_link} \n"
                )
            
            message_text += (
                f"💎 מבצע סופר (Super Deal): \n"
                f"קישור: {super_links} \n"
                f"🔥 הצעה מוגבלת בזמן: \n"
                f"קישור: {limit_links} \n\n"
                "#AliExpressSaverBot ✅"
            )
            
            bot.send_message(message.chat.id, message_text, reply_markup=keyboard)
    except Exception as e:
        print(f"Error in get_affiliate_links: {e}")
        bot.send_message(message.chat.id, "אופס, משהו השתבש... 🤷🏻‍♂️")

def build_shopcart_link(link):
    params = get_url_params(link)
    shop_cart_link = "https://www.aliexpress.com/p/trade/confirm.html?"
    shop_cart_params = {
        "availableProductShopcartIds": ",".join(params["availableProductShopcartIds"]),
        "extraParams": json.dumps({"channelInfo": {"sourceType": "620"}}, separators=(',', ':'))
    }
    return create_query_string_url(link=shop_cart_link, params=shop_cart_params)

def get_url_params(link):
    parsed_url = urlparse(link)
    params = parse_qs(parsed_url.query)
    return params

def create_query_string_url(link, params):
    return link + urllib.parse.urlencode(params)

def get_affiliate_shopcart_link(link, message):
    try:
        shopcart_link = build_shopcart_link(link)
        affiliate_link = aliexpress.get_affiliate_links(shopcart_link)[0].promotion_link
        text2 = f"הנה קישור להנחת העגלה שלך: \n{str(affiliate_link)}"
        img_link3 = "https://i.postimg.cc/1Xrk1RJP/Copy-of-Basket-aliexpress-telegram.png"
        bot.send_photo(message.chat.id, img_link3, caption=text2)
    except Exception as e:
        print(f"Error in get_affiliate_shopcart_link: {e}")
        bot.send_message(message.chat.id, "אופס, משהו השתבש... 🤷🏻‍♂️")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    try:
        print(f"Callback query received: {call.data}")
        if call.data == 'click':
            link = 'https://www.aliexpress.com/p/shoppingcart/index.html?'
            get_affiliate_shopcart_link(link, call.message)
        else:
            bot.send_message(call.message.chat.id, "..")
            img_link2 = "https://i.postimg.cc/VvmhgQ1h/Basket-aliexpress-telegram.png"
            bot.send_photo(call.message.chat.id,
                           img_link2,
                           caption="קישורים למשחקי איסוף מטבעות כדי להוזיל את מחיר המוצרים. היכנסו מדי יום כדי לאסוף את כמות המטבעות המקסימלית! 👇",
                           reply_markup=keyboard_games)
    except Exception as e:
        print(f"Error in handle_callback_query: {e}")

# אפליקציית Flask לניהול Webhook
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == 'POST':
        json_str = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return 'OK', 200

def run_flask():
    app.run(host='0.0.0.0', port=10000)

if __name__ == "__main__":
    webhook_url = os.getenv('WEBHOOK_URL')
    
    if webhook_url:
        # מצב פרודקשן: שימוש ב-Webhook
        print("🚀 מפעיל את הבוט במצב Webhook...")
        threading.Thread(target=run_flask).start()
        try:
            bot.remove_webhook()
            bot.set_webhook(url=webhook_url)
            print(f"✅ Webhook נקבע לכתובת: {webhook_url}")
        except Exception as e:
            print(f"❌ שגיאה בהגדרת Webhook: {e}")
    else:
        # מצב פיתוח: שימוש ב-Polling
        print("🚀 מפעיל את הבוט במצב Polling (פיתוח)...")
        try:
            bot.remove_webhook()
            print("✅ Webhooks קודמים הוסרו")
            
            print("🔄 הבוט רץ... לחץ על Ctrl+C לעצירה.")
            bot.infinity_polling(none_stop=True, timeout=10, long_polling_timeout=5)
        except KeyboardInterrupt:
            print("\n👋 הבוט נעצר על ידי המשתמש.")
        except Exception as e:
            print(f"❌ שגיאה במצב Polling: {e}")
