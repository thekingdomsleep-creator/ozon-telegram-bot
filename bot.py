
import telebot
import os
from openai import OpenAI

BOT_TOKEN = os.getenv("8277705336:AAEStAvtfyDL4Ad_-XGZo2rqh3hYDXyF-5c")
OPENAI_API_KEY = os.getenv("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")

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
