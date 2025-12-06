# bot.py — Ozon-like shop bot (SQLite, admin via Telegram commands)
import os
import sqlite3
import uuid
import logging
from functools import wraps

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, ConversationHandler, filters
)

# ---------- CONFIG ----------
TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0") or 0)
if not TOKEN or not ADMIN_ID:
    raise SystemExit("Set TELEGRAM_TOKEN and ADMIN_ID environment variables")

DB = "shop.db"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- DB helpers ----------
def init_db():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT, price INTEGER,
        stock INTEGER, image_url TEXT, description TEXT,
        category_id INTEGER, FOREIGN KEY(category_id) REFERENCES categories(id))""")
    cur.execute("""CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY, user_id INTEGER, items TEXT, total INTEGER, status TEXT, name TEXT, phone TEXT)""")
    con.commit()
    con.close()

def db(query, params=(), fetch=False, one=False):
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute(query, params)
    res = None
    if fetch: res = cur.fetchall()
    if one: res = cur.fetchone()
    con.commit()
    con.close()
    return res

# init db + sample data
init_db()
if not db("SELECT id FROM products LIMIT 1", fetch=True):
    # sample categories
    db("INSERT OR IGNORE INTO categories (name) VALUES (?)", ("Уход за лицом",))
    db("INSERT OR IGNORE INTO categories (name) VALUES (?)", ("Аппараты",))
    cat = db("SELECT id FROM categories WHERE name=?", ("Уход за лицом",), one=True)[0]
    db("INSERT INTO products (title,price,stock,image_url,description,category_id) VALUES (?,?,?,?,?,?)",
       ("Сыворотка омолаживающая", 1500, 10, "", "Лёгкая сыворотка для дневного ухода", cat))
    db("INSERT INTO products (title,price,stock,image_url,description,category_id) VALUES (?,?,?,?,?,?)",
       ("Крем увлажняющий", 900, 15, "", "Интенсивное увлажнение", cat))

# ---------- helpers ----------
def admin_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *a, **k):
        uid = update.effective_user.id if update.effective_user else None
        if uid != ADMIN_ID:
            if update.effective_message:
                await update.effective_message.reply_text("Доступ только для администратора.")
            return
        return await func(update, context, *a, **k)
    return wrapper

def price_str(p): return f"{p} ₽"

# ---------- UI builders ----------
def main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Каталог", callback_data="catalog")],
        [InlineKeyboardButton("🔥 Акции", callback_data="promo"), InlineKeyboardButton("🆕 Новинки", callback_data="new")],
        [InlineKeyboardButton("🧺 Корзина", callback_data="cart"), InlineKeyboardButton("📞 Поддержка", callback_data="support")]
    ])

def categories_kb():
    cats = db("SELECT id, name FROM categories", fetch=True)
    kb = []
    for cid, name in cats:
        kb.append([InlineKeyboardButton(name, callback_data=f"cat:{cid}")])
    kb.append([InlineKeyboardButton("◀ Назад", callback_data="back")])
    return InlineKeyboardMarkup(kb)

def product_card_kb(pid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("В корзину", callback_data=f"add:{pid}")],
        [InlineKeyboardButton("◀ В каталог", callback_data="catalog")]
    ])

# ---------- Handlers ----------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Добро пожаловать в магазин косметики! Выберите:", reply_markup=main_menu_kb())

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data
    await q.answer()
    # catalog
    if data == "catalog":
        await q.edit_message_text("Выберите категорию:", reply_markup=categories_kb())
        return
    if data.startswith("cat:"):
        cid = int(data.split(":",1)[1])
        rows = db("SELECT id, title, price, stock FROM products WHERE category_id=?", (cid,), fetch=True)
        if not rows:
            await q.edit_message_text("В этой категории товаров нет.", reply_markup=categories_kb())
            return
        kb = []
        for pid, title, price, stock in rows:
            kb.append([InlineKeyboardButton(f"{title} — {price}₽", callback_data=f"prod:{pid}")])
        kb.append([InlineKeyboardButton("◀ Назад", callback_data="catalog")])
        await q.edit_message_text("Товары:", reply_markup=InlineKeyboardMarkup(kb))
        return
    if data.startswith("prod:"):
        pid = int(data.split(":",1)[1])
        row = db("SELECT title, price, stock, image_url, description FROM products WHERE id=?", (pid,), one=True)
        if not row:
            await q.edit_message_text("Товар не найден.")
            return
        title, price, stock, img, desc = row
        text = f"*{title}*\n\n{desc or ''}\n\nЦена: {price_str(price)}\nОстаток: {stock}"
        if img:
            await q.message.reply_photo(photo=img, caption=text, parse_mode="Markdown", reply_markup=product_card_kb(pid))
            try: await q.message.delete()
            except: pass
        else:
            await q.edit_message_text(text, parse_mode="Markdown", reply_markup=product_card_kb(pid))
        return
    if data.startswith("add:"):
        pid = data.split(":",1)[1]
        cart = context.user_data.get("cart", {})
        cart[pid] = cart.get(pid, 0) + 1
        context.user_data["cart"] = cart
        await q.answer("Добавлено в корзину ✅")
        return
    if data == "cart":
        cart = context.user_data.get("cart", {})
        if not cart:
            await q.edit_message_text("Корзина пуста.")
            return
        text = "Ваша корзина:\n"
        total = 0
        for pid, qty in cart.items():
            r = db("SELECT title, price FROM products WHERE id=?", (pid,), one=True)
            if not r: continue
            title, price = r
            total += price * qty
            text += f"{title} x{qty} — {price*qty}₽\n"
        text += f"\nИтого: {total}₽"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Оформить", callback_data="checkout")],
            [InlineKeyboardButton("Очистить", callback_data="clear_cart")],
            [InlineKeyboardButton("◀ Назад", callback_data="back")]
        ])
        await q.edit_message_text(text, reply_markup=kb)
        return
    if data == "clear_cart":
        context.user_data["cart"] = {}
        await q.edit_message_text("Корзина очищена.")
        return
    if data == "checkout":
        await q.edit_message_text("Введите ваше имя:")
        context.user_data["checkout_step"] = "name"
        return
    if data == "back":
        await q.edit_message_text("Главное меню:", reply_markup=main_menu_kb())
        return

async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    step = context.user_data.get("checkout_step")

    if step == "name":
        context.user_data["order_name"] = txt
        context.user_data["checkout_step"] = "phone"
        await update.message.reply_text("Введите телефон:")
        return

    if step == "phone":
        phone = txt
        name = context.user_data.get("order_name","")
        cart = context.user_data.get("cart", {})
        if not cart:
            await update.message.reply_text("Корзина пуста.")
            return
        total = 0
        items = ""
        for pid, qty in cart.items():
            r = db("SELECT title, price FROM products WHERE id=?", (pid,), one=True)
            if not r: continue
            total += r[1] * qty
            items += f"{pid}:{qty};"
        oid = str(uuid.uuid4())
        db("INSERT INTO orders (id,user_id,items,total,status,name,phone) VALUES (?,?,?,?,?,?,?)",
           (oid, update.effective_user.id, items, total, "new", name, phone))
        await update.message.reply_text(f"Заказ создан.\nИтого: {total}₽\nМенеджер свяжется с вами.")
        context.user_data["cart"] = {}
        context.user_data.pop("checkout_step", None)
        return

    await update.message.reply_text("Используйте /start или меню.")

# ---------- Setup ----------
def build_app():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_router))
    return app

if __name__ == "__main__":
    logger.info("Bot starting...")
    app = build_app()
    app.run_polling()
