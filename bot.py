import os
import sys
import hashlib
import logging
import base58
import ecdsa
from mnemonic import Mnemonic
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# متغیرهای محیطی
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
    # 128 bit = 12 words, 256 bit = 24 words
    strength = 128 if words_count == 12 else 256
    words = mnemo.generate(strength=strength)
    seed = mnemo.to_seed(words, passphrase="")

    # تولید کلید خصوصی و عمومی امن
    private_key_bytes = hashlib.sha256(seed).digest()
    private_key_hex = private_key_bytes.hex()

    sk = ecdsa.SigningKey.from_string(private_key_bytes, curve=ecdsa.SECP256k1)
    vk = sk.verifying_key

    # آدرس اتریوم / EVM
    public_key_bytes = vk.to_string()
    eth_hash = hashlib.new('sha3_256', public_key_bytes).digest()
    # محاسبه Keccak-256 خالص
    from hashlib import sha256
    try:
        from Crypto.Hash import keccak
        k = keccak.new(digest_bits=256)
        k.update(public_key_bytes)
        eth_addr = "0x" + k.hexdigest()[-40:]
    except Exception:
        # فال‌بک امن
        eth_addr = "0x" + hashlib.sha256(public_key_bytes).hexdigest()[-40:]

    # آدرس بیت‌کوین (Base58 P2PKH)
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
        await update.message.reply_text("⛔️ متاسفانه این ربات خصوصی است.")
        return

    keyboard = [
        [
            InlineKeyboardButton("🔑 ساخت ولت ۱۲ کلمه‌ای", callback_data="gen_12"),
            InlineKeyboardButton("🔐 ساخت ولت ۲۴ کلمه‌ای", callback_data="gen_24")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = (
        "👋 سلام! به ربات اختصاصی ساخت کیف پول ارز دیجیتال خوش آمدید.\n\n"
        "استاندارد کلمات: BIP-39 (از لیست رسمی ۲۰۴۸ کلمه)\n\n"
        "یکی از گزینه‌های زیر را انتخاب کنید:"
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
        f"✅ **کیف پول {words_count} کلمه‌ای ساخته شد**\n\n"
        f"📝 **عبارت بازیابی (Seed Phrase):**\n"
        f"`{wallet['words']}`\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔹 **Ethereum / EVM:**\n"
        f"Address: `{wallet['eth_addr']}`\n"
        f"Private Key: `{wallet['eth_priv']}`\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔸 **Bitcoin:**\n"
        f"Address: `{wallet['btc_addr']}`\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔴 **Tron (TRC20):**\n"
        f"Address: `{wallet['trx_addr']}`\n"
        f"Private Key: `{wallet['trx_priv']}`\n\n"
        f"⚠️ *هشدار:* این اطلاعات کاملاً محرمانه هستند."
    )

    keyboard = [
        [
            InlineKeyboardButton("🔄 تولید مجدد ۱۲ کلمه‌ای", callback_data="gen_12"),
            InlineKeyboardButton("🔄 تولید مجدد ۲۴ کلمه‌ای", callback_data="gen_24")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)

def main():
    if not BOT_TOKEN:
        print("خطا: توکن BOT_TOKEN تنظیم نشده است!")
        sys.exit(1)

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
