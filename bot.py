
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = "ВАШ_ТОКЕН_ТЕЛЕГРАМ"

# Логирование
logging.basicConfig(level=logging.INFO)

# Каталог товаров
PRODUCTS = {
    "1": {"name": "Крем для лица", "price": 1200, "desc": "Увлажняющий, 50ml"},
    "2": {"name": "Сыворотка витамин C", "price": 2100, "desc": "Осветляет кожу"},
    "3": {"name": "Маска омолаживающая", "price": 1800, "desc": "Эффект лифтинга"},
}

# Главное меню
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🛍 Каталог", callback_data="catalog")],
        [InlineKeyboardButton("🔥 Акции", callback_data="sale")],
        [InlineKeyboardButton("📞 Поддержка", callback_data="support")]
    ]
    await update.message.reply_text(
        "Добро пожаловать в магазин косметологии!\nВыберите раздел:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Обработка кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "catalog":
        keyboard = [
            [InlineKeyboardButton(f"{p['name']} - {p['price']}₽", callback_data=f"product_{pid}")]
            for pid, p in PRODUCTS.items()
        ]
        await query.edit_message_text("Каталог товаров:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("product_"):
        pid = query.data.split("_")[1]
        p = PRODUCTS[pid]
        keyboard = [
            [InlineKeyboardButton("🛒 Купить", url="https://t.me/YourSupport")],
            [InlineKeyboardButton("⬅ Назад", callback_data="catalog")]
        ]
        await query.edit_message_text(
            f"**{p['name']}**\n"
            f"Цена: {p['price']}₽\n"
            f"Описание: {p['desc']}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif query.data == "sale":
        await query.edit_message_text("🔥 Акции скоро появятся!")

    elif query.data == "support":
        await query.edit_message_text("📞 Поддержка: @YourSupport")

# Запуск бота
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
