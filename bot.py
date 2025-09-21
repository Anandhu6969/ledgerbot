from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Replace this with your actual bot token
TOKEN = "8374430628:AAE1XAOU3Ze9IWZCVibxG1N3XCUkTyZ0lMY"

# Ledgers: chat_id -> ledger
ledgers = {}
profit_percent = 0  # default profit %

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

# Handle messages (+amount, -amount, show ledger)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    # Ensure ledger exists
    if chat_id not in ledgers:
        ledgers[chat_id] = {"given": [], "repaid": []}

    # Record money given
    if text.startswith("+"):
        try:
            amount = float(text[1:])
            ledgers[chat_id]["given"].append(amount)
            await update.message.reply_text(f"💰 Recorded: You gave {amount}")
        except ValueError:
            await update.message.reply_text("❌ Invalid format. Use +5000")

    # Record money repaid
    elif text.startswith("-"):
        try:
            amount = float(text[1:])
            ledgers[chat_id]["repaid"].append(amount)
            await update.message.reply_text(f"💸 Recorded: {amount} repaid")
        except ValueError:
            await update.message.reply_text("❌ Invalid format. Use -2000")

    # Show ledger
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

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setprofit", set_profit))
    app.add_handler(CommandHandler("reset", reset_ledger))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Ledger Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
