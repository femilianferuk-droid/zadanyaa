import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Настройки
TOKEN = "8580593984:AAGJClodpSPOFK7dQPSSWa_IuDwhtwr8llE"
ADMIN_CHAT_ID = 7973988177
COMMISSION = 0.1  # 10% комиссия

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица заданий
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            task_id INTEGER PRIMARY KEY AUTOINCREMENT,
            creator_id INTEGER,
            description TEXT,
            task_text TEXT,
            reward REAL,
            status TEXT DEFAULT 'active',
            executor_id INTEGER,
            proof_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (creator_id) REFERENCES users (user_id),
            FOREIGN KEY (executor_id) REFERENCES users (user_id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Получение пользователя
def get_user(user_id):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

# Создание пользователя
def create_user(user_id, username):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)', (user_id, username))
    conn.commit()
    conn.close()

# Обновление баланса
def update_balance(user_id, amount):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

# Создание задания
def create_task(creator_id, description, task_text, reward):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO tasks (creator_id, description, task_text, reward)
        VALUES (?, ?, ?, ?)
    ''', (creator_id, description, task_text, reward))
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return task_id

# Получение активных заданий
def get_active_tasks():
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks WHERE status = "active"')
    tasks = cursor.fetchall()
    conn.close()
    return tasks

# Получение задания по ID
def get_task(task_id):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks WHERE task_id = ?', (task_id,))
    task = cursor.fetchone()
    conn.close()
    return task

# Получение заданий пользователя
def get_user_tasks(user_id):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks WHERE creator_id = ? ORDER BY created_at DESC', (user_id,))
    tasks = cursor.fetchall()
    conn.close()
    return tasks

# Обновление статуса задания
def update_task_status(task_id, status, executor_id=None, proof_text=None):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    if executor_id and proof_text:
        cursor.execute('''
            UPDATE tasks SET status = ?, executor_id = ?, proof_text = ?
            WHERE task_id = ?
        ''', (status, executor_id, proof_text, task_id))
    elif executor_id:
        cursor.execute('''
            UPDATE tasks SET status = ?, executor_id = ? WHERE task_id = ?
        ''', (status, executor_id, task_id))
    else:
        cursor.execute('UPDATE tasks SET status = ? WHERE task_id = ?', (status, task_id))
    conn.commit()
    conn.close()

# Получение всех пользователей
def get_all_users():
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    conn.close()
    return [user[0] for user in users]

# Получение статистики
def get_stats():
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM tasks')
    total_tasks = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM tasks WHERE status = "active"')
    active_tasks = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM tasks WHERE status = "completed"')
    completed_tasks = cursor.fetchone()[0]
    
    cursor.execute('SELECT SUM(balance) FROM users')
    total_balance = cursor.fetchone()[0] or 0
    
    conn.close()
    
    return {
        'total_users': total_users,
        'total_tasks': total_tasks,
        'active_tasks': active_tasks,
        'completed_tasks': completed_tasks,
        'total_balance': total_balance
    }

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    create_user(user_id, username)
    
    await show_main_menu(update, context)

# Главное меню
async def show_main_menu(update, context):
    user_id = update.effective_user.id if hasattr(update.effective_user, 'id') else update.from_user.id
    
    keyboard = [
        [InlineKeyboardButton("👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton("📋 Создать задание", callback_data="create_task")],
        [InlineKeyboardButton("🎯 Активные задания", callback_data="active_tasks")],
        [InlineKeyboardButton("📊 Мои задания", callback_data="my_tasks")]
    ]
    
    if user_id == ADMIN_CHAT_ID:
        keyboard.append([InlineKeyboardButton("⚙️ Админ панель", callback_data="admin_panel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(update, 'message'):
        await update.message.reply_text(
            "👋 Добро пожаловать в бот для выполнения заданий!\n\n"
            "Здесь вы можете:\n"
            "• Создавать задания за деньги\n"
            "• Выполнять задания других пользователей\n"
            "• Зарабатывать реальные деньги\n\n"
            "Выберите действие:",
            reply_markup=reply_markup
        )
    else:
        await update.edit_message_text(
            "👋 Добро пожаловать в бот для выполнения заданий!\n\n"
            "Выберите действие:",
            reply_markup=reply_markup
        )

# Обработчик callback-запросов
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "profile":
        await show_profile(query, context)
    elif data == "create_task":
        await create_task_start(query, context)
    elif data == "active_tasks":
        await show_active_tasks(query, context)
    elif data == "my_tasks":
        await show_my_tasks(query, context)
    elif data == "deposit":
        await deposit(query, context)
    elif data == "withdraw":
        await withdraw(query, context)
    elif data == "admin_panel":
        await admin_panel(query, context)
    elif data == "admin_stats":
        await admin_stats(query, context)
    elif data == "admin_balance":
        await admin_balance_start(query, context)
    elif data == "admin_broadcast":
        await admin_broadcast_start(query, context)
    elif data == "main_menu":
        await show_main_menu(query, context)
    elif data.startswith("task_"):
        task_id = int(data.split("_")[1])
        await take_task(query, context, task_id)
    elif data.startswith("complete_"):
        task_id = int(data.split("_")[1])
        await complete_task_start(query, context, task_id)
    elif data.startswith("approve_"):
        task_id = int(data.split("_")[1])
        await approve_task(query, context, task_id)
    elif data.startswith("reject_"):
        task_id = int(data.split("_")[1])
        await reject_task(query, context, task_id)

# Показать профиль
async def show_profile(query, context):
    user = get_user(query.from_user.id)
    balance = user[2] if user else 0
    
    keyboard = [
        [InlineKeyboardButton("💳 Пополнить баланс", callback_data="deposit")],
        [InlineKeyboardButton("💰 Вывести средства", callback_data="withdraw")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"👤 Ваш профиль\n\n"
        f"🆔 ID: {query.from_user.id}\n"
        f"👤 Имя: @{query.from_user.username or 'Не указано'}\n"
        f"💰 Баланс: {balance:.2f}₽\n\n"
        f"Пополнение от 10₽, вывод от 50₽",
        reply_markup=reply_markup
    )

# Пополнение баланса
async def deposit(query, context):
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="profile")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "💳 По поводу пополнения/вывода, напишите сюда: @nezeexsupp, сразу укажите сумму!\n\n"
        "Минимальное пополнение: 10₽\n"
        "Минимальный вывод: 50₽",
        reply_markup=reply_markup
    )

# Вывод средств
async def withdraw(query, context):
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="profile")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "💰 По поводу пополнения/вывода, напишите сюда: @nezeexsupp, сразу укажите сумму!\n\n"
        "Минимальное пополнение: 10₽\n"
        "Минимальный вывод: 50₽",
        reply_markup=reply_markup
    )

# Начало создания задания
async def create_task_start(query, context):
    user = get_user(query.from_user.id)
    if user[2] < 0.1:
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "❌ Недостаточно средств на балансе для создания задания.\n"
            "Минимальная сумма задания: 0.1₽\n\n"
            "Пополните баланс в профиле.",
            reply_markup=reply_markup
        )
        return
    
    context.user_data['creating_task'] = True
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "📝 Создание нового задания\n\n"
        "Шаг 1/2: Напишите описание задания (это увидят другие пользователи):",
        reply_markup=reply_markup
    )

# Показать активные задания
async def show_active_tasks(query, context):
    tasks = get_active_tasks()
    
    if not tasks:
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("❌ Нет активных заданий.", reply_markup=reply_markup)
        return
    
    keyboard = []
    for task in tasks:
        creator = get_user(task[1])
        keyboard.append([InlineKeyboardButton(
            f"🎯 {task[2]} - {task[4]}₽", 
            callback_data=f"task_{task[0]}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "🎯 Активные задания:\n\n"
    for task in tasks:
        creator = get_user(task[1])
        text += f"• {task[2]} - {task[4]}₽\n"
    
    await query.edit_message_text(text, reply_markup=reply_markup)

# Взять задание
async def take_task(query, context, task_id):
    task = get_task(task_id)
    if not task or task[5] != 'active':
        await query.edit_message_text("❌ Задание уже выполнено или удалено.")
        return
    
    context.user_data['executing_task'] = task_id
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="active_tasks")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📋 Задание:\n\n{task[3]}\n\n"
        f"💵 Вознаграждение: {task[4]}₽\n\n"
        "После выполнения задания отправьте доказательство выполнения одним сообщением.",
        reply_markup=reply_markup
    )

# Админ панель
async def admin_panel(query, context):
    if query.from_user.id != ADMIN_CHAT_ID:
        await query.edit_message_text("❌ Доступ запрещен.")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("💳 Изменить баланс", callback_data="admin_balance")],
        [InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "⚙️ Админ панель\n\n"
        "Выберите действие:",
        reply_markup=reply_markup
    )

# Админ статистика
async def admin_stats(query, context):
    if query.from_user.id != ADMIN_CHAT_ID:
        await query.edit_message_text("❌ Доступ запрещен.")
        return
    
    stats = get_stats()
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📊 Статистика бота:\n\n"
        f"👥 Всего пользователей: {stats['total_users']}\n"
        f"📋 Всего заданий: {stats['total_tasks']}\n"
        f"🟢 Активных заданий: {stats['active_tasks']}\n"
        f"✅ Выполненных заданий: {stats['completed_tasks']}\n"
        f"💰 Общий баланс: {stats['total_balance']:.2f}₽",
        reply_markup=reply_markup
    )

# Начало изменения баланса
async def admin_balance_start(query, context):
    if query.from_user.id != ADMIN_CHAT_ID:
        await query.edit_message_text("❌ Доступ запрещен.")
        return
    
    context.user_data['admin_action'] = 'change_balance'
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "💳 Изменение баланса\n\n"
        "Введите данные в формате:\n"
        "ID_пользователя:СУММА\n\n"
        "Пример: 123456789:100.50",
        reply_markup=reply_markup
    )

# Начало рассылки
async def admin_broadcast_start(query, context):
    if query.from_user.id != ADMIN_CHAT_ID:
        await query.edit_message_text("❌ Доступ запрещен.")
        return
    
    context.user_data['admin_action'] = 'broadcast'
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📢 Рассылка сообщений\n\n"
        "Введите сообщение для рассылки всем пользователям:",
        reply_markup=reply_markup
    )

# Показать мои задания
async def show_my_tasks(query, context):
    user_id = query.from_user.id
    tasks = get_user_tasks(user_id)
    
    if not tasks:
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📭 У вас нет созданных заданий.", reply_markup=reply_markup)
        return
    
    text = "📊 Ваши задания:\n\n"
    for task in tasks:
        status = "✅ Выполнено" if task[5] == 'completed' else "🟢 Активно" if task[5] == 'active' else "⏳ На проверке"
        text += f"🎯 {task[2]}\n💵 {task[4]}₽ | {status}\n\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup)

# Одобрить задание
async def approve_task(query, context, task_id):
    task = get_task(task_id)
    if not task:
        await query.edit_message_text("❌ Задание не найдено.")
        return
    
    # Перевод денег исполнителю
    reward = task[4] * (1 - COMMISSION)
    update_balance(task[6], reward)  # executor_id
    
    # Обновление статуса
    update_task_status(task_id, 'completed')
    
    await context.bot.send_message(
        task[6],  # executor_id
        f"✅ Ваше задание одобрено!\n"
        f"💵 На ваш баланс зачислено: {reward:.2f}₽\n"
        f"📋 Задание: {task[2]}"
    )
    
    await query.edit_message_text("✅ Задание одобрено, средства переведены исполнителю.")

# Отклонить задание
async def reject_task(query, context, task_id):
    task = get_task(task_id)
    if not task:
        await query.edit_message_text("❌ Задание не найдено.")
        return
    
    # Возврат денег создателю
    update_balance(task[1], task[4])  # creator_id
    
    # Обновление статуса
    update_task_status(task_id, 'rejected')
    
    await context.bot.send_message(
        task[6],  # executor_id
        f"❌ Ваше задание отклонено.\n"
        f"📋 Задание: {task[2]}\n"
        f"💵 Деньги возвращены создателю задания."
    )
    
    await query.edit_message_text("❌ Задание отклонено, средства возвращены создателю.")

# Обработчик текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    # Админ: изменение баланса
    if context.user_data.get('admin_action') == 'change_balance' and user_id == ADMIN_CHAT_ID:
        try:
            user_id_str, amount_str = text.split(':')
            target_user_id = int(user_id_str.strip())
            amount = float(amount_str.strip())
            
            user = get_user(target_user_id)
            if not user:
                await update.message.reply_text("❌ Пользователь не найден.")
                return
            
            update_balance(target_user_id, amount)
            
            await update.message.reply_text(
                f"✅ Баланс пользователя {target_user_id} изменен на {amount:.2f}₽\n"
                f"Новый баланс: {(user[2] + amount):.2f}₽"
            )
            
            # Уведомление пользователю
            await context.bot.send_message(
                target_user_id,
                f"ℹ️ Ваш баланс был изменен администратором.\n"
                f"Изменение: {amount:+.2f}₽\n"
                f"Новый баланс: {(user[2] + amount):.2f}₽"
            )
            
            context.user_data.pop('admin_action', None)
            
        except ValueError:
            await update.message.reply_text("❌ Неверный формат. Используйте: ID:СУММА")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    
    # Админ: рассылка
    elif context.user_data.get('admin_action') == 'broadcast' and user_id == ADMIN_CHAT_ID:
        users = get_all_users()
        success = 0
        failed = 0
        
        for user_id in users:
            try:
                await context.bot.send_message(user_id, f"📢 Рассылка от администратора:\n\n{text}")
                success += 1
            except:
                failed += 1
        
        await update.message.reply_text(
            f"📢 Рассылка завершена:\n"
            f"✅ Успешно: {success}\n"
            f"❌ Не удалось: {failed}"
        )
        
        context.user_data.pop('admin_action', None)
    
    # Создание задания - шаг 1: описание
    elif context.user_data.get('creating_task') == True:
        context.user_data['task_description'] = text
        context.user_data['creating_task'] = 'step2'
        await update.message.reply_text(
            "Шаг 2/2: Напишите текст задания (это увидят исполнители после принятия задания):"
        )
    
    # Создание задания - шаг 2: текст задания
    elif context.user_data.get('creating_task') == 'step2':
        description = context.user_data['task_description']
        task_text = text
        user = get_user(user_id)
        
        # Запрос суммы вознаграждения
        context.user_data['task_text'] = task_text
        context.user_data['creating_task'] = 'step3'
        await update.message.reply_text(
            "Шаг 3/3: Укажите сумму вознаграждения (в рублях):\n\n"
            f"Ваш текущий баланс: {user[2]:.2f}₽\n"
            f"Минимальная сумма: 0.1₽"
        )
    
    # Создание задания - шаг 3: сумма
    elif context.user_data.get('creating_task') == 'step3':
        try:
            reward = float(text)
            user = get_user(user_id)
            
            if reward < 0.1:
                await update.message.reply_text("❌ Минимальная сумма задания: 0.1₽")
                return
            
            if user[2] < reward:
                await update.message.reply_text("❌ Недостаточно средств на балансе.")
                return
            
            # Создание задания
            task_id = create_task(
                user_id,
                context.user_data['task_description'],
                context.user_data['task_text'],
                reward
            )
            
            # Списание средств
            update_balance(user_id, -reward)
            
            # Очистка данных
            context.user_data.pop('creating_task', None)
            context.user_data.pop('task_description', None)
            context.user_data.pop('task_text', None)
            
            await update.message.reply_text(
                f"✅ Задание успешно создано!\n\n"
                f"📋 Описание: {context.user_data.get('task_description', '')}\n"
                f"💵 Вознаграждение: {reward}₽\n\n"
                f"ID задания: {task_id}"
            )
            
        except ValueError:
            await update.message.reply_text("❌ Пожалуйста, введите корректную сумму.")
    
    # Доказательство выполнения задания
    elif context.user_data.get('executing_task'):
        task_id = context.user_data['executing_task']
        task = get_task(task_id)
        
        if task and task[5] == 'active':
            # Назначение исполнителя
            update_task_status(task_id, 'pending', user_id, text)
            
            # Уведомление создателя
            await context.bot.send_message(
                task[1],  # creator_id
                f"📨 Новое доказательство по вашему заданию!\n\n"
                f"📋 Задание: {task[2]}\n"
                f"💵 Вознаграждение: {task[4]}₽\n"
                f"👤 Исполнитель: @{update.effective_user.username or 'Не указан'}\n\n"
                f"📎 Доказательство:\n{text}\n\n"
                f"Одобрить или отклонить?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{task_id}")],
                    [InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{task_id}")]
                ])
            )
            
            context.user_data.pop('executing_task', None)
            await update.message.reply_text(
                "✅ Доказательство отправлено создателю задания!\n"
                "Ожидайте проверки и выплаты средств."
            )
        else:
            await update.message.reply_text("❌ Задание уже выполнено или отменено.")
            context.user_data.pop('executing_task', None)

def main():
    # Инициализация БД
    init_db()
    
    # Создание приложения
    application = Application.builder().token(TOKEN).build()
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    
    # Обработчики callback-запросов
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Обработчики сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()
