from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ContextTypes
)
import os

TOKEN = os.environ.get("BOT_TOKEN")
CLOUD_RUN_URL = os.environ.get("CLOUD_RUN_URL")

ledgers = {}
profit_percent = 0

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
    global profit_percent
    try:
        if len(context.args) == 0:
            await update.message.reply_text("❌ Example: /setprofit 10")
            return
        profit_percent = float(context.args[0])
        await update.message.reply_text(f"✅ Profit % set to {profit_percent}")
    except ValueError:
        await update.message.reply_text("❌ Invalid number.")

# /reset
async def reset_ledger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    ledgers[chat_id] = {"given": [], "repaid": []}
    await update.message.reply_text("🔄 Ledger reset.")

# Messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    if chat_id not in ledgers:
        ledgers[chat_id] = {"given": [], "repaid": []}

    if text.startswith("+"):
        try:
            amount = float(text[1:])
            ledgers[chat_id]["given"].append(amount)
            await update.message.reply_text(f"💰 Recorded: +{amount}")
        except ValueError:
            await update.message.reply_text("❌ Use +5000")
    elif text.startswith("-"):
        try:
            amount = float(text[1:])
            ledgers[chat_id]["repaid"].append(amount)
            await update.message.reply_text(f"💸 Recorded: -{amount}")
        except ValueError:
            await update.message.reply_text("❌ Use -2000")
    elif text.lower() == "show ledger":
        total_given = sum(ledgers[chat_id]["given"])
        total_repaid = sum(ledgers[chat_id]["repaid"])
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

# Handlers
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("setprofit", set_profit))
bot_app.add_handler(CommandHandler("reset", reset_ledger))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    cloud_run_url = os.environ["CLOUD_RUN_URL"]
    bot_app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=f"{cloud_run_url}/{TOKEN}"
    )

