import os
import sys
import hashlib
import base58
import ecdsa
from mnemonic import Mnemonic
import telebot
from telebot import types

# دریافت توکن و آیدی ادمین از متغیرهای رندر
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = os.getenv("ADMIN_ID", "").strip()

if not BOT_TOKEN:
    print("خطا: توکن BOT_TOKEN تنظیم نشده است!")
    sys.exit(1)

# اتصال به ربات تلگرام بدون نیاز به asyncio
bot = telebot.TeleBot(BOT_TOKEN)

def is_admin(user_id):
    if ADMIN_ID and str(user_id) != ADMIN_ID:
        return False
    return True

def generate_wallet(words_count=12):
    mnemo = Mnemonic("english")
    strength = 128 if words_count == 12 else 256
    words = mnemo.generate(strength=strength)
    seed = mnemo.to_seed(words, passphrase="")

    private_key_bytes = hashlib.sha256(seed).digest()
    private_key_hex = private_key_bytes.hex()

    sk = ecdsa.SigningKey.from_string(private_key_bytes, curve=ecdsa.SECP256k1)
    vk = sk.verifying_key
    public_key_bytes = vk.to_string()

    # آدرس اتریوم / EVM
    eth_addr = "0x" + hashlib.sha256(public_key_bytes).hexdigest()[-40:]

    # آدرس بیت‌کوین
    sha_pk = hashlib.sha256(b'\x04' + public_key_bytes).digest()
    try:
        rip_pk = hashlib.new('ripemd160', sha_pk).digest()
    except Exception:
        rip_pk = hashlib.sha256(sha_pk).digest()[:20]

    extended_rip = b'\x00' + rip_pk
    checksum = hashlib.sha256(hashlib.sha256(extended_rip).digest()).digest()[:4]
    btc_addr = base58.b58encode(extended_rip + checksum).decode()

    # آدرس ترون TRC20
    trx_payload = b'\x41' + rip_pk
    trx_check = hashlib.sha256(hashlib.sha256(trx_payload).digest()).digest()[:4]
    trx_addr = base58.b58encode(trx_payload + trx_check).decode()

    return {
        "words": words,
        "eth_addr": eth_addr,
        "eth_priv": "0x" + private_key_hex,
        "btc_addr": btc_addr,
        "btc_priv": private_key_hex,
        "trx_addr": trx_addr,
        "trx_priv": private_key_hex
    }

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔️ این ربات شخصی است و دسترسی ندارید.")
        return

    markup = types.InlineKeyboardMarkup()
    btn12 = types.InlineKeyboardButton("🔑 ولت ۱۲ کلمه‌ای", callback_data="gen_12")
    btn24 = types.InlineKeyboardButton("🔐 ولت ۲۴ کلمه‌ای", callback_data="gen_24")
    markup.row(btn12, btn24)

    bot.reply_to(
        message,
        "👋 سلام! به ربات اختصاصی ساخت کیف پول خوش آمدید.\n\n"
        "استاندارد کلمات: BIP-39 (از لیست معتبر ۲۰۴۸ کلمه)\n"
        "گزینه مورد نظر خود را انتخاب کنید:",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "دسترسی غیرمجاز!")
        return

    words_count = 12 if call.data == "gen_12" else 24
    wallet = generate_wallet(words_count)

    text = (
        f"✅ *کیف پول {words_count} کلمه‌ای ساخته شد:*\n\n"
        f"📝 *عبارت بازیابی (Seed):*\n"
        f"`{wallet['words']}`\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔹 *Ethereum / EVM:*\n"
        f"Address: `{wallet['eth_addr']}`\n"
        f"Private Key: `*******`\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔸 *Bitcoin:*\n"
        f"Address: `{wallet['btc_addr']}`\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔴 *Tron (TRC20):*\n"
        f"Address: `{wallet['trx_addr']}`\n"
        f"Private Key: `*******`"
    )

    markup = types.InlineKeyboardMarkup()
    btn12 = types.InlineKeyboardButton("🔄 مجدد ۱۲ کلمه‌ای", callback_data="gen_12")
    btn24 = types.InlineKeyboardButton("🔄 مجدد ۲۴ کلمه‌ای", callback_data="gen_24")
    markup.row(btn12, btn24)

    bot.send_message(call.message.chat.id, text, parse_mode="Markdown", reply_markup=markup)
    bot.answer_callback_query(call.id)

if __name__ == "__main__":
    print("ربات با موفقیت آنلاین شد...")
    bot.infinity_polling(skip_pending=True)
