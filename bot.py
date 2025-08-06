# Llamie Telegram Bot
# This bot is designed to interact with ollama local API

import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from ollama import AsyncClient

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OLLAMA_MODEL = "gemma3n:e4b"
ollama_client = AsyncClient(host='http://188.134.71.7:11434')

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set. Please set it in your .env file.")

# In-memory context: {chat_id: [msg1, msg2, ...]}
chat_context = {}
MAX_CONTEXT = 10

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="👋 Hello! I am Llamie Bot. How can I assist you today?")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    chat_context.pop(chat_id, None)
    await context.bot.send_message(chat_id=chat_id, text="🔄 Context reset! Ready for a fresh start.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_message = update.message.text
    
    # Get bot info from context
    bot_info = await context.bot.get_me()
    
    # Check if this is a reply to the bot's message
    is_reply_to_bot = (update.message.reply_to_message and 
                      update.message.reply_to_message.from_user.id == bot_info.id)
    
    # Check if the bot is mentioned by username
    is_mentioned = "@OllamieBot" in user_message
    
    # Only respond if it's a reply to bot or bot is mentioned
    if not (is_reply_to_bot or is_mentioned):
        return
    
    # Remove the mention from the message if present
    if is_mentioned:
        user_message = user_message.replace("@OllamieBot", "").strip()
        if not user_message:  # If message is empty after removing mention
            await context.bot.send_message(chat_id=chat_id, text="👋 How can I help you?")
            return
    
    # Update context
    history = chat_context.get(chat_id, [])
    history.append({"role": "user", "content": user_message})
    # Keep only last MAX_CONTEXT messages
    history = history[-MAX_CONTEXT:]
    chat_context[chat_id] = history

    # Prepare messages for ollama
    ollama_messages = []
    for msg in history:
        ollama_messages.append({"role": msg["role"], "content": msg["content"]})

    try:
        response = await ollama_client.chat(model=OLLAMA_MODEL, messages=ollama_messages)
        bot_reply = response['message']['content']
        # Add bot reply to context
        history.append({"role": "assistant", "content": bot_reply})
        chat_context[chat_id] = history[-MAX_CONTEXT:]
        await context.bot.send_message(chat_id=chat_id, text=f"🤖 {bot_reply}")
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Error: {e}")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    print("🚀 Llamie Bot is running!")
    
    app.run_polling()

if __name__ == "__main__":
    main()
    