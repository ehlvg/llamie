# Llamie Telegram Bot
# This bot is designed to interact with ollama local API

import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from ollama import AsyncClient, Client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('llamie_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OLLAMA_MODEL = "gpt-oss:120b"
SYSTEM_PROMPT = 'You are chatting in a messaging app. Your name is Anfisa. You respond shortly, with no formatting, elaboration, extra fluff, tables, just an SMS-like one-two paragraph (maximum) responses. Be casual, natural, you can include a bit of emojis sometimes.'
ollama_client = AsyncClient(host='https://ollama.com', headers={'Authorization': '' + os.getenv("OLLAMIE_TOKEN")})

logger.info(f"Starting Llamie Bot with model: {OLLAMA_MODEL}")
logger.info(f"Ollama token configured: {'Yes' if os.getenv('OLLAMIE_TOKEN') else 'No'}")

if not BOT_TOKEN:
    logger.error("BOT_TOKEN environment variable is not set")
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
        logger.info(f"Created new context for chat {chat_id}")
    elif not chat_context[chat_id] or chat_context[chat_id][0]["role"] != "system":
        # If no system message or it's not first, add it
        chat_context[chat_id].insert(0, get_system_message())
        logger.info(f"Added system prompt to existing context for chat {chat_id}")

def trim_context(chat_id):
    """Trims context while preserving system message"""
    if chat_id not in chat_context:
        return
    
    messages = chat_context[chat_id]
    original_length = len(messages)
    
    if len(messages) <= MAX_CONTEXT:
        return
    
    # Always keep system message (first) and trim the middle, keeping recent messages
    system_msg = messages[0] if messages and messages[0]["role"] == "system" else get_system_message()
    recent_messages = messages[-(MAX_CONTEXT-1):]  # Keep last MAX_CONTEXT-1 messages
    
    chat_context[chat_id] = [system_msg] + recent_messages
    logger.info(f"Trimmed context for chat {chat_id}: {original_length} -> {len(chat_context[chat_id])} messages")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    chat = update.effective_chat
    
    logger.info(f"START command - Chat: {chat_id} ({chat.type}), User: {user.id} (@{user.username or 'no_username'}) {user.first_name}")
    
    ensure_system_prompt_in_context(chat_id)
    await context.bot.send_message(chat_id=chat_id, text="👋 Hello! I am Llamie Bot. How can I assist you today?")
    
    logger.info(f"START response sent to chat {chat_id}")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    chat = update.effective_chat
    
    logger.info(f"RESET command - Chat: {chat_id} ({chat.type}), User: {user.id} (@{user.username or 'no_username'}) {user.first_name}")
    
    old_context_length = len(chat_context.get(chat_id, []))
    chat_context[chat_id] = [get_system_message()]
    
    logger.info(f"Context reset for chat {chat_id}: {old_context_length} -> 1 message")
    
    await context.bot.send_message(chat_id=chat_id, text="🔄 Context reset! Ready for a fresh start.")
    
    logger.info(f"RESET response sent to chat {chat_id}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    chat = update.effective_chat
    user_message = update.message.text
    
    logger.info(f"Message received - Chat: {chat_id} ({chat.type}), User: {user.id} (@{user.username or 'no_username'}) {user.first_name}")
    logger.info(f"Message content: {user_message}")
    
    # Ensure system prompt is in context
    ensure_system_prompt_in_context(chat_id)
    
    # Check if this is a reply to the bot's message
    is_reply_to_bot = (update.message.reply_to_message and 
                      update.message.reply_to_message.from_user.is_bot)
    
    # Check if the bot is mentioned by username
    is_mentioned = "@OllamieBot" in user_message
    
    logger.info(f"Message analysis - Chat: {chat_id}, Reply to bot: {is_reply_to_bot}, Mentioned: {is_mentioned}")
    
    # Only respond if it's a reply to bot or bot is mentioned
    if not (is_reply_to_bot or is_mentioned):
        logger.info(f"Ignoring message in chat {chat_id} - not a reply to bot and not mentioned")
        return
    
    # Remove the mention from the message if present
    if is_mentioned:
        user_message = user_message.replace("@OllamieBot", "").strip()
        logger.info(f"Removed mention, new message: {user_message}")
        if not user_message:  # If message is empty after removing mention
            await context.bot.send_message(chat_id=chat_id, text="👋 How can I help you?")
            logger.info(f"Sent help message to chat {chat_id}")
            return
    
    # Update context
    history = chat_context.get(chat_id, [])
    history.append({"role": "user", "content": user_message})
    
    logger.info(f"Added user message to context - Chat: {chat_id}, Context length: {len(history)}")
    
    # Trim context while preserving system message
    chat_context[chat_id] = history
    trim_context(chat_id)
    
    # Get updated history after trimming
    history = chat_context[chat_id]

    # Prepare messages for ollama
    ollama_messages = []
    for msg in history:
        ollama_messages.append({"role": msg["role"], "content": msg["content"]})

    logger.info(f"Sending {len(ollama_messages)} messages to Ollama for chat {chat_id}")

    try:
        response = await ollama_client.chat(
            model=OLLAMA_MODEL, messages=ollama_messages
            )
        bot_reply = response['message']['content']
        
        logger.info(f"Ollama response for chat {chat_id}: {bot_reply}")
        
        # Add bot reply to context
        history.append({"role": "assistant", "content": bot_reply})
        chat_context[chat_id] = history
        trim_context(chat_id)  # Trim again after adding bot response
        
        await context.bot.send_message(chat_id=chat_id, text=f"🤖 {bot_reply}")
        
        logger.info(f"Bot response sent to chat {chat_id}, final context length: {len(chat_context[chat_id])}")
        
    except Exception as e:
        logger.error(f"Error processing message in chat {chat_id}: {str(e)}")
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Error: {e}")
        logger.info(f"Error message sent to chat {chat_id}")

def main():
    logger.info("Initializing Llamie Bot...")
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    logger.info("🚀 Llamie Bot is running and ready to accept messages!")
    print("🚀 Llamie Bot is running!")
    
    try:
        app.run_polling(drop_pending_updates=True)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        print("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {str(e)}")
        print(f"Bot crashed: {str(e)}")
        raise

if __name__ == "__main__":
    main()
    