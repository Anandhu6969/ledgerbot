from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, Application
from flask import Flask, request, jsonify
import os

# Bot token
TOKEN = "8374430628:AAE1XAOU3Ze9IWZCVibxG1N3XCUkTyZ0lMY"

# Ledgers: chat_id -> ledger
ledgers = {}
profit_percent = 0  # default profit %

# Flask app
app = Flask(__name__)

# Telegram bot setup
bot_app = ApplicationBuilder().token(TOKEN).build()

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "✅ Ledger Bot Activated!\n\n"
        "💡 Usage Guide:\n"
        "• +amount → Record money you gave (loan/investment)\n"
        "• -amount → Record money returned to you\n"
        "• show ledger → View current balance & profit\n"
        "• /setprofit <number> → Update profit %\n"
        "• /reset → Clear your ledger\n"
    )
    await update.message.reply_text(msg)

# /setprofit command
async def set_profit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global profit_percent
    try:
        if len(context.args) == 0:
            await update.message.reply_text("❌ Please provide a profit %. Example: /setprofit 10")
            return
        profit_percent = float(context.args[0])
        await update.message.reply_text(f"✅ Profit % updated to {profit_percent}")
    except ValueError:
        await update.message.reply_text("❌ Invalid number. Example: /setprofit 10")

# /reset command
async def reset_ledger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    ledgers[chat_id] = {"given": [], "repaid": []}
    await update.message.reply_text("🔄 Ledger reset successfully!")

# Handle messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    if chat_id not in ledgers:
        ledgers[chat_id] = {"given": [], "repaid": []}

    if text.startswith("+"):
        try:
            amount = float(text[1:])
            ledgers[chat_id]["given"].append(amount)
            await update.message.reply_text(f"💰 Recorded: You gave {amount}")
        except ValueError:
            await update.message.reply_text("❌ Invalid format. Use +5000")
    elif text.startswith("-"):
        try:
            amount = float(text[1:])
            ledgers[chat_id]["repaid"].append(amount)
            await update.message.reply_text(f"💸 Recorded: {amount} repaid")
        except ValueError:
            await update.message.reply_text("❌ Invalid format. Use -2000")
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
            f"Pending Balance: {pending}\n"
        )
        if pending <= 0:
            msg += "\n✅ Deal Closed!"
        await update.message.reply_text(msg)

# Add handlers
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("setprofit", set_profit))
bot_app.add_handler(CommandHandler("reset", reset_ledger))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Flask route for webhook
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    bot_app.run_update(update)
    return jsonify({"status": "ok"})

# Root route
@app.route("/", methods=["GET"])
def index():
    return "Bot is running!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
