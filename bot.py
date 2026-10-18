import os
import sys
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from bip_utils import (
    Bip39MnemonicGenerator, Bip39SeedGenerator, Bip39WordsNum,
    Bip44, Bip44Coins, Bip44Changes, Bip84, Bip84Coins
)

# خواندن امن توکن از متغیرهای محیطی
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

def generate_crypto_wallet(words_count: int):
    num_words = Bip39WordsNum.WORDS_NUM_12 if words_count == 12 else Bip39WordsNum.WORDS_NUM_24
    mnemonic = Bip39MnemonicGenerator().FromWordsNumber(num_words)
    seed_bytes = Bip39SeedGenerator(mnemonic).Generate()

    # اتریوم و شبکه‌های EVM
    bip44_eth = Bip44.FromSeed(seed_bytes, Bip44Coins.ETHEREUM)
    eth_acc = bip44_eth.Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)
    eth_address = eth_acc.PublicKey().ToAddress()
    eth_priv = eth_acc.PrivateKey().Raw().ToHex()

    # بیت‌کوین سگویت Native SegWit (bc1)
    bip84_btc = Bip84.FromSeed(seed_bytes, Bip84Coins.BITCOIN)
    btc_acc = bip84_btc.Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)
    btc_address = btc_acc.PublicKey().ToAddress()
    btc_priv = btc_acc.PrivateKey().ToWif()

    # ترون TRC20
    bip44_trx = Bip44.FromSeed(seed_bytes, Bip44Coins.TRON)
    trx_acc = bip44_trx.Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)
    trx_address = trx_acc.PublicKey().ToAddress()
    trx_priv = trx_acc.PrivateKey().Raw().ToHex()

    return {
        "mnemonic": mnemonic,
        "eth_addr": eth_address,
        "eth_priv": eth_priv,
        "btc_addr": btc_address,
        "btc_priv": btc_priv,
        "trx_addr": trx_address,
        "trx_priv": trx_priv
    }

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("🔑 تولید ولت ۱۲ کلمه‌ای", callback_data="gen_12"),
            InlineKeyboardButton("🔐 تولید ولت ۲۴ کلمه‌ای", callback_data="gen_24")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = (
        "👋 سلام! به ربات ساخت کیف پول بر پایه استاندارد BIP-39 / BIP-44 خوش آمدید.\n\n"
        "این ربات آدرس‌های کاملاً معتبر و هماهنگ با کیف‌پول‌های رسمی تولید می‌کند.\n\n"
        "یکی از گزینه‌های زیر را انتخاب کنید:"
    )
    await update.message.reply_text(text, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    words_count = 12 if query.data == "gen_12" else 24
    wallet = generate_crypto_wallet(words_count)

    text = (
        f"✅ **کیف پول {words_count} کلمه‌ای ساخته شد**\n\n"
        f"📝 **عبارت بازیابی (Seed Phrase):**\n"
        f"`{wallet['mnemonic']}`\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔹 **Ethereum / BSC / Polygon (EVM):**\n"
        f"Address:\n`{wallet['eth_addr']}`\n"
        f"Private Key:\n`{wallet['eth_priv']}`\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔸 **Bitcoin (Native SegWit - bech32):**\n"
        f"Address:\n`{wallet['btc_addr']}`\n"
        f"Private Key (WIF):\n`{wallet['btc_priv']}`\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔴 **Tron (TRC20):**\n"
        f"Address:\n`{wallet['trx_addr']}`\n"
        f"Private Key:\n`{wallet['trx_priv']}`\n\n"
        f"⚠️ *هشدار:* این اطلاعات را در جای امن نگهداری کنید."
    )

    keyboard = [
        [
            InlineKeyboardButton("🔄 ساخت مجدد ۱۲ کلمه‌ای", callback_data="gen_12"),
            InlineKeyboardButton("🔄 ساخت مجدد ۲۴ کلمه‌ای", callback_data="gen_24")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)

def main():
    if not BOT_TOKEN:
        print("خطا: مقدار BOT_TOKEN در متغیرهای محیطی یافت نشد!")
        sys.exit(1)

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
