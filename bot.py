import os
import sys
import hashlib
import logging
import asyncio
import base58
import ecdsa
from mnemonic import Mnemonic
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# دریافت توکن و آیدی ادمین از متغیرهای رندر
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

def is_admin(user_id: int) -> bool:
    if ADMIN_ID and str(user_id) != str(ADMIN_ID).strip():
        return False
    return True

def generate_wallet(words_count: int = 12):
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
    rip_pk = hashlib.new('ripemd160', sha_pk).digest()
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

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔️ دسترسی غیرمجاز است.")
        return

    keyboard = [
        [
            InlineKeyboardButton("🔑 ساخت ولت ۱۲ کلمه‌ای", callback_data="gen_12"),
            InlineKeyboardButton("🔐 ساخت ولت ۲۴ کلمه‌ای", callback_data="gen_24")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = (
        "👋 سلام! به ربات اختصاصی ساخت کیف پول خوش آمدید.\n\n"
        "برای تولید ولت معتبر روی دکمه‌های زیر بزنید:"
    )
    await update.message.reply_text(text, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        return

    words_count = 12 if query.data == "gen_12" else 24
    wallet = generate_wallet(words_count)

    text = (
        f"✅ **کیف پول {words_count} کلمه‌ای:**\n\n"
        f"📝 **عبارت بازیابی:**\n"
        f"`{wallet['words']}`\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔹 **Ethereum / EVM:**\n"
        f"Address: `{wallet['eth_addr']}`\n"
        f"Private Key: `*******`\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔸 **Bitcoin:**\n"
        f"Address: `{wallet['btc_addr']}`\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔴 **Tron (TRC20):**\n"
        f"Address: `{wallet['trx_addr']}`\n"
        f"Private Key: `*******`"
    )

    keyboard = [
        [
            InlineKeyboardButton("🔄 مجدد ۱۲ کلمه‌ای", callback_data="gen_12"),
            InlineKeyboardButton("🔄 مجدد ۲۴ کلمه‌ای", callback_data="gen_24")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)

async def main_async():
    if not BOT_TOKEN:
        print("خطا: BOT_TOKEN تنظیم نشده است!")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("ربات با موفقیت فعال شد و آماده دریافت پیام است...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    # زنده نگه داشتن لوپ ربات
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main_async())
    except (KeyboardInterrupt, SystemExit):
        pass
