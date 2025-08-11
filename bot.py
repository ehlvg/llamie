# Llamie Telegram Bot
# This bot is designed to interact with ollama local API

import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from ollama import AsyncClient, Client

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OLLAMA_MODEL = "gpt-oss:120b"
SYSTEM_PROMPT = 'You are chatting in a messaging app. Your name is Anfisa. You respond shortly, with no formatting, elaboration, extra fluff, tables, just an SMS-like one-two paragraph (maximum) responses. Be casual, natural, you can include a bit of emojis sometimes.'
ollama_client = AsyncClient(host='https://ollama.com', headers={'Authorization': '' + os.getenv("OLLAMIE_TOKEN")})
print('' + os.getenv("OLLAMIE_TOKEN"))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set. Please set it in your .env file.")

# In-memory context: {chat_id: [msg1, msg2, ...]}
chat_context = {
}
MAX_CONTEXT = 10

def get_system_message():
    """Returns the system message that should always be first"""
    return {"role": "system", "content": SYSTEM_PROMPT}

def ensure_system_prompt_in_context(chat_id):
    """Ensures the system prompt is always the first message in context"""
    if chat_id not in chat_context:
        chat_context[chat_id] = [get_system_message()]
    elif not chat_context[chat_id] or chat_context[chat_id][0]["role"] != "system":
        # If no system message or it's not first, add it
        chat_context[chat_id].insert(0, get_system_message())

def trim_context(chat_id):
    """Trims context while preserving system message"""
    if chat_id not in chat_context:
        return
    
    messages = chat_context[chat_id]
    if len(messages) <= MAX_CONTEXT:
        return
    
    # Always keep system message (first) and trim the middle, keeping recent messages
    system_msg = messages[0] if messages and messages[0]["role"] == "system" else get_system_message()
    recent_messages = messages[-(MAX_CONTEXT-1):]  # Keep last MAX_CONTEXT-1 messages
    
    chat_context[chat_id] = [system_msg] + recent_messages

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    ensure_system_prompt_in_context(chat_id)
    await context.bot.send_message(chat_id=chat_id, text="👋 Hello! I am Llamie Bot. How can I assist you today?")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    chat_context[chat_id] = [get_system_message()]
    await context.bot.send_message(chat_id=chat_id, text="🔄 Context reset! Ready for a fresh start.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_message = update.message.text
    
    # Ensure system prompt is in context
    ensure_system_prompt_in_context(chat_id)
    
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
    
    # Trim context while preserving system message
    chat_context[chat_id] = history
    trim_context(chat_id)
    
    # Get updated history after trimming
    history = chat_context[chat_id]

    # Prepare messages for ollama
    ollama_messages = []
    for msg in history:
        ollama_messages.append({"role": msg["role"], "content": msg["content"]})

    try:
        response = await ollama_client.chat(
            model=OLLAMA_MODEL, messages=ollama_messages
            )
        bot_reply = response['message']['content']
        # Add bot reply to context
        history.append({"role": "assistant", "content": bot_reply})
        chat_context[chat_id] = history
        trim_context(chat_id)  # Trim again after adding bot response
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
    