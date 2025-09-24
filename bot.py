# bot.py
import os
import asyncio
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from google.cloud import firestore

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment vars
TOKEN = os.environ.get("BOT_TOKEN")
CLOUD_RUN_URL = os.environ.get("CLOUD_RUN_URL")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is missing")
if not CLOUD_RUN_URL:
    raise RuntimeError("CLOUD_RUN_URL environment variable is missing")

# Firestore client (uses Cloud Run default credentials)
db = firestore.Client()

# Helpers
def _doc_ref(chat_id: int):
    return db.collection("ledgers").document(str(chat_id))

# Transactional append to a list field (given/repaid)
@firestore.transactional
def _txn_append(transaction, doc_ref, field, value):
    snapshot = doc_ref.get(transaction=transaction)
    data = snapshot.to_dict() if snapshot.exists else {}
    arr = list(data.get(field, []))
    arr.append(value)
    transaction.set(doc_ref, {field: arr}, merge=True)

async def append_field(chat_id: int, field: str, value: float):
    """Append value to a list field in a transaction (async wrapper)."""
    doc_ref = _doc_ref(chat_id)
    transaction = db.transaction()
    # run the transactional function inside a thread to avoid blocking asyncio loop
    await asyncio.to_thread(_txn_append, transaction, doc_ref, field, value)

async def set_profit_percent(chat_id: int, percent: float):
    doc_ref = _doc_ref(chat_id)
    await asyncio.to_thread(doc_ref.set, {"profit_percent": float(percent)}, True)  # merge=True

async def get_ledger(chat_id: int):
    doc_ref = _doc_ref(chat_id)
    snapshot = await asyncio.to_thread(doc_ref.get)
    if not snapshot.exists:
        return {"given": [], "repaid": [], "profit_percent": 0.0}
    data = snapshot.to_dict()
    return {
        "given": data.get("given", []),
        "repaid": data.get("repaid", []),
        "profit_percent": float(data.get("profit_percent", 0.0))
    }

async def reset_ledger_db(chat_id: int):
    doc_ref = _doc_ref(chat_id)
    await asyncio.to_thread(doc_ref.set, {"given": [], "repaid": [], "profit_percent": 0.0}, True)

# Create Telegram app
bot_app = ApplicationBuilder().token(TOKEN).build()

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "✅ Ledger Bot Activated!\n\n"
        "💡 Usage Guide:\n"
        "• +amount → Record money you gave\n"
        "• -amount → Record money returned\n"
        "• show ledger → View balance & profit\n"
        "• /setprofit <number> → Update profit %\n"
        "• /reset → Clear ledger\n"
    )
    await update.message.reply_text(msg)

# /setprofit
async def set_profit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        if len(context.args) == 0:
            await update.message.reply_text("❌ Please provide a profit %. Example: /setprofit 10")
            return
        percent = float(context.args[0])
        await set_profit_percent(chat_id, percent)
        await update.message.reply_text(f"✅ Profit % set to {percent}")
    except ValueError:
        await update.message.reply_text("❌ Invalid number. Example: /setprofit 10")
    except Exception as e:
        logger.exception("Error in set_profit")
        await update.message.reply_text("❌ Something went wrong while setting profit.")

# /reset
async def reset_ledger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        await reset_ledger_db(chat_id)
        await update.message.reply_text("🔄 Ledger reset successfully.")
    except Exception:
        logger.exception("Error in reset_ledger")
        await update.message.reply_text("❌ Something went wrong while resetting ledger.")

# handle messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        text = update.message.text.strip()

        # plus => given
        if text.startswith("+"):
            try:
                amount = float(text[1:])
                await append_field(chat_id, "given", amount)
                await update.message.reply_text(f"💰 Recorded: +{amount}")
            except ValueError:
                await update.message.reply_text("❌ Invalid format. Use +5000")
            return

        # minus => repaid
        if text.startswith("-"):
            try:
                amount = float(text[1:])
                await append_field(chat_id, "repaid", amount)
                await update.message.reply_text(f"💸 Recorded: -{amount}")
            except ValueError:
                await update.message.reply_text("❌ Invalid format. Use -2000")
            return

        # show ledger
        if text.lower() == "show ledger":
            data = await get_ledger(chat_id)
            total_given = sum(map(float, data["given"]))
            total_repaid = sum(map(float, data["repaid"]))
            profit_percent = float(data["profit_percent"])
            profit_amount = (total_given * profit_percent) / 100
            expected_return = total_given + profit_amount
            pending = expected_return - total_repaid

            msg = (
                f"📒 Ledger Report\n\n"
                f"Total Given: {total_given}\n"
                f"Profit %: {profit_percent}\n"
                f"Profit Amount: {profit_amount}\n"
                f"Expected Return: {expected_return}\n"
                f"Total Repaid: {total_repaid}\n"
                f"Pending: {pending}\n"
            )
            if pending <= 0:
                msg += "\n✅ Deal Closed!"
            await update.message.reply_text(msg)
            return

        # fallback
        await update.message.reply_text("❓ Unrecognized command. Use +amount, -amount, or 'show ledger'.")
    except Exception:
        logger.exception("Error in handle_message")
        await update.message.reply_text("❌ Something went wrong while handling your message.")

# register handlers
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("setprofit", set_profit))
bot_app.add_handler(CommandHandler("reset", reset_ledger))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Run webhook server for Cloud Run
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    bot_app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=f"{CLOUD_RUN_URL}/{TOKEN}"
    )
