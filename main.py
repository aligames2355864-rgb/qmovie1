import logging
import asyncio
import random
import time
import requests
import json
import os
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# إعداد الـ Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

DATA_FILE = "/root/bot_data.json"

def load_system_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "telegram_id": 601923953,
        "waiting_for": None,
        "accounts": {
            "acc1": {
                "name": "الحساب الأول 1️⃣",
                "sessionid": "",
                "user_id": "",
                "mid": "",
                "datr": "",
                "ig_did": "",
                "target_username": "",
                "is_running": False
            },
            "acc2": {
                "name": "الحساب الثاني 2️⃣",
                "sessionid": "",
                "user_id": "",
                "mid": "",
                "datr": "",
                "ig_did": "",
                "target_username": "",
                "is_running": False
            }
        }
    }

def save_system_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(system_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error saving data: {e}")

system_data = load_system_data()

def create_instagram_session(acc_data):
    session = requests.Session()
    csrf_token = uuid.uuid4().hex
    
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
        'X-IG-App-ID': '936619743392459',
        'X-Requested-With': 'XMLHttpRequest',
        'X-Instagram-AJAX': '1018698994',
        'X-CSRFToken': csrf_token,
        'Referer': 'https://www.instagram.com/accounts/edit/',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': '*/*',
        'Accept-Language': 'ar-SA,ar;q=0.9,en-US;q=0.8,en;q=0.7'
    })
    
    s_id = acc_data.get("sessionid", "")
    u_id = acc_data.get("user_id", "")
    mid = acc_data.get("mid", "")
    datr = acc_data.get("datr", "")
    ig_did = acc_data.get("ig_did", "")

    cookies = {
        'sessionid': s_id,
        'ds_user_id': str(u_id),
        'csrftoken': csrf_token
    }
    if mid: cookies['mid'] = mid
    if datr: cookies['datr'] = datr
    if ig_did: cookies['ig_did'] = ig_did

    session.cookies.update(cookies)
    return session

def get_main_dashboard():
    keyboard = [
        [InlineKeyboardButton("⚙️ إعداد الحساب الأول (1)", callback_data="cfg_acc1"),
         InlineKeyboardButton("⚙️ إعداد الحساب الثاني (2)", callback_data="cfg_acc2")],
        [InlineKeyboardButton("🚀 تشغيل المراقبة للجميع", callback_data="start_all"),
         InlineKeyboardButton("🛑 إيقاف المراقبة للجميع", callback_data="stop_all")],
        [InlineKeyboardButton("📊 عرض حالة الحسابين", callback_data="check_status")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    system_data["telegram_id"] = update.effective_user.id
    save_system_data()
    welcome_msg = (
        "أهلاً بك يا علاوي في أداة التثبيت المحدثة عبر الـ Web API! 🤖🔥\n\n"
        "أدخل بيانات الحساب بصيغة:\n`sessionid:user_id:mid:datr:ig_did`\n\n"
        "اختر من لوحة التحكم للبدء:"
    )
    await update.message.reply_text(welcome_msg, parse_mode="Markdown", reply_markup=get_main_dashboard())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "cfg_acc1":
        system_data["waiting_for"] = "account1_login"
        save_system_data()
        await query.message.reply_text("📝 أرسل بيانات **الحساب الأول** بصيغة:\n`sessionid:user_id:mid:datr:ig_did`", parse_mode="Markdown")

    elif data == "cfg_acc2":
        system_data["waiting_for"] = "account2_login"
        save_system_data()
        await query.message.reply_text("📝 أرسل بيانات **الحساب الثاني** بصيغة:\n`sessionid:user_id:mid:datr:ig_did`", parse_mode="Markdown")

    elif data == "check_status":
        acc1 = system_data["accounts"]["acc1"]
        acc2 = system_data["accounts"]["acc2"]
        st1 = "شغال 🟢" if acc1["is_running"] else "متوقف 🔴"
        st2 = "شغال 🟢" if acc2["is_running"] else "متوقف 🔴"
        status_msg = (
            f"1️⃣ **الحساب الأول:**\n• ID: `{acc1['user_id'] or '---'}`\n• الهدف: `{acc1['target_username'] or '---'}`\n• الحالة: {st1}\n\n"
            f"2️⃣ **الحساب الثاني:**\n• ID: `{acc2['user_id'] or '---'}`\n• الهدف: `{acc2['target_username'] or '---'}`\n• الحالة: {st2}"
        )
        await query.message.reply_text(status_msg, parse_mode="Markdown", reply_markup=get_main_dashboard())

    elif data == "start_all":
        started_any = False
        for acc_key in ["acc1", "acc2"]:
            acc = system_data["accounts"][acc_key]
            if acc["sessionid"] and acc["user_id"] and acc["target_username"] and not acc["is_running"]:
                acc["is_running"] = True
                asyncio.create_task(run_monitor_loop(acc_key, context))
                started_any = True
                await query.message.reply_text(f"✅ تم بدء المراقبة لـ ({acc['name']}) بنجاح!")
        save_system_data()
        if started_any:
            await query.message.reply_text("🚀 العمليات تعمل الآن بالخلفية وبأمان تام.", reply_markup=get_main_dashboard())
        else:
            await query.message.reply_text("⚠️ يرجى التأكد من إدخال الـ SessionID واليوزر المستهدف أولاً!", reply_markup=get_main_dashboard())

    elif data == "stop_all":
        system_data["accounts"]["acc1"]["is_running"] = False
        system_data["accounts"]["acc2"]["is_running"] = False
        save_system_data()
        await query.message.reply_text("🛑 تم إيقاف جميع الحسابات.", reply_markup=get_main_dashboard())

async def handle_text_inputs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    state = system_data["waiting_for"]
    if not state: return

    if state in ["account1_login", "account2_login"]:
        parts = text.split(":")
        if len(parts) >= 2:
            s_id = parts[0].strip()
            u_id = parts[1].strip()
            mid = parts[2].strip() if len(parts) > 2 else ""
            datr = parts[3].strip() if len(parts) > 3 else ""
            ig_did = parts[4].strip() if len(parts) > 4 else ""
            
            acc_key = "acc1" if state == "account1_login" else "acc2"
            system_data["accounts"][acc_key]["sessionid"] = s_id
            system_data["accounts"][acc_key]["user_id"] = u_id
            system_data["accounts"][acc_key]["mid"] = mid
            system_data["accounts"][acc_key]["datr"] = datr
            system_data["accounts"][acc_key]["ig_did"] = ig_did
            
            system_data["waiting_for"] = f"{acc_key}_target"
            save_system_data()
            await update.message.reply_text("✅ تم حفظ الجلسة والكوكيز الكاملة بنجاح! أرسل الآن **اليوزر المستهدف**:")
        else:
            await update.message.reply_text("❌ صيغة خاطئة! أرسل على الأقل: `sessionid:user_id`", parse_mode="Markdown")

    elif state in ["acc1_target", "acc2_target"]:
        acc_key = state.split("_")[0]
        system_data["accounts"][acc_key]["target_username"] = text
        system_data["waiting_for"] = None
        save_system_data()
        await update.message.reply_text(f"🎯 تم ربط الهدف `{text}` بنجاح!", parse_mode="Markdown", reply_markup=get_main_dashboard())

async def run_monitor_loop(acc_key, context: ContextTypes.DEFAULT_TYPE):
    chat_id = system_data["telegram_id"]
    acc = system_data["accounts"][acc_key]

    while acc["is_running"]:
        target = acc["target_username"]
        session = create_instagram_session(acc)
        
        try:
            await asyncio.sleep(random.randint(2, 5))
            
            check_url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={target}"
            res = session.get(check_url)
            
            if res.status_code == 404:
                await context.bot.send_message(
                    chat_id=chat_id, 
                    text=f"🚨 **تنبيه يا علاوي:** اليوزر `{target}` متاح! جاري التثبيت الفوري...", 
                    parse_mode="Markdown"
                )
                
                claim_url = "https://www.instagram.com/api/v1/web/accounts/edit/"
                payload = {
                    "username": target,
                    "first_name": "",
                    "biography": "",
                    "email": "",
                    "phone_number": ""
                }
                
                claim_res = session.post(claim_url, data=payload)
                
                if "<!DOCTYPE html>" in claim_res.text or "<html" in claim_res.text:
                    await context.bot.send_message(
                        chat_id=chat_id, 
                        text=f"⚠️ **الـ SessionID منتهي أو طالب تحقق (Checkpoint)!**\nيرجى تجديد الكوكيز.",
                        parse_mode="Markdown"
                    )
                else:
                    await asyncio.sleep(2)
                    verify_check = session.get(check_url)
                    
                    if verify_check.status_code == 200:
                        await context.bot.send_message(
                            chat_id=chat_id, 
                            text=f"🎉 **كفووو علاوي!** تم تثبيت اليوزر بنجاح صار باسمك: (`{target}`)", 
                            parse_mode="Markdown"
                        )
                        acc["is_running"] = False
                        save_system_data()
                        break
                    else:
                        clean_resp = claim_res.text[:200].replace("`", "").replace("*", "")
                        await context.bot.send_message(
                            chat_id=chat_id, 
                            text=f"❌ **فشل التثبيت من إنستغرام!** (الكود: {claim_res.status_code})\n**الرد:** `{clean_resp}`",
                            parse_mode="Markdown"
                        )

            elif res.status_code == 200:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"🔄 فحص مبدئي: اليوزر `{target}` لا يزال محجوزاً.",
                    parse_mode="Markdown",
                    disable_notification=True
                )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"⚠️ استجابة غير متوقعة من الفحص (رمز الحالة: {res.status_code}).",
                    disable_notification=True
                )

        except Exception as e:
            err_msg = str(e)[:250]
            await context.bot.send_message(chat_id=chat_id, text=f"⚠️ خطأ أثناء العملية: {err_msg}", disable_notification=True)

        base_delay = 10800 
        random_extra = random.randint(300, 1800)
        total_delay = base_delay + random_extra

        waited = 0
        while waited < total_delay and acc["is_running"]:
            await asyncio.sleep(10)
            waited += 10

def main():
    TELEGRAM_BOT_TOKEN = "6355153643:AAE2h_w-Ko7eJamJz5wTj5c6P97MUAVBfXs"
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_inputs))
    print("🤖 بوت التثبيت يعمل الآن بكفاءة تامة باستخدام Requests والكوكيز الكاملة...")
    app.run_polling()

if __name__ == "__main__":
    main()
