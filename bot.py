
import telebot
import os
from openai import OpenAI

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)


# ----- Команда START -----
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "Привет! 👋\n\n"
        "Я бот-магазин как Ozon + AI помощник.\n"
        "Напиши, что хочешь найти или спроси что угодно!"
    )


# ----- AI ChatGPT -----
@bot.message_handler(func=lambda msg: True)
def chatgpt_reply(message):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Ты умный продавец как в Ozon. Помогаешь подобрать товары."},
                {"role": "user", "content": message.text}
            ]
        )

        answer = response.choices[0].message.content
        bot.send_message(message.chat.id, answer)

    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка AI: {e}")


# ----- Запуск -----
bot.polling(none_stop=True)
