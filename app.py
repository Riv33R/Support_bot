from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    Contact,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
    CallbackQueryHandler,
)
import json
import uuid

TICKETS_FILE = "tickets.json"
SUPPORT_USER_IDS = [
    "420825051",
    "987654321",
]  # Замените на реальные ID пользователей техподдержки


# Функция для асинхронной загрузки тикетов
async def load_tickets():
    try:
        with open(TICKETS_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return []


# Функция для асинхронной записи тикетов
async def save_tickets(tickets):
    with open(TICKETS_FILE, "w") as file:
        json.dump(tickets, file)


# Общая функция start для начала общения
async def start(update: Update, context: CallbackContext) -> None:
    user_id = str(update.message.from_user.id)
    if user_id in SUPPORT_USER_IDS:
        keyboard = [
            [InlineKeyboardButton("Создать тикет", callback_data="create_ticket")],
            [InlineKeyboardButton("Просмотреть тикеты", callback_data="view_tickets")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
    else:
        keyboard = [
            [KeyboardButton("Создать тикет")],
            [KeyboardButton("Посмотреть тикеты")],
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)


# Функция для обработки текстовых сообщений от пользователей
async def handle_message(update: Update, context: CallbackContext) -> None:
    if context.user_data.get("creating_ticket", True):
        tickets = await load_tickets()
        ticket = {
            "id": str(uuid.uuid4()),
            "user": update.message.from_user.id,
            "message": update.message.text,
            "username": update.message.from_user.username
            or update.message.from_user.first_name,
        }
        tickets.append(ticket)
        await save_tickets(tickets)
        await update.message.reply_text(
            "Ваш тикет сохранён. Специалист технической поддержки скоро с вами свяжется."
        )
        context.user_data["creating_ticket"] = False
    else:
        # Если текст сообщения "Создать тикет", установите флаг для создания тикета
        if update.message.text == "Создать тикет":
            context.user_data["creating_ticket"] = True
            await update.message.reply_text("Пожалуйста, введите текст вашего тикета.")
        else:
            await update.message.reply_text(
                "Пожалуйста, используйте кнопки меню для навигации."
            )


# Функция для создания тикета через inline-кнопку
async def create_ticket(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    context.user_data["creating_ticket"] = True
    await query.edit_message_text("Пожалуйста, введите текст вашего тикета.")


# Функция для просмотра тикетов (для поддержки)
async def view_tickets(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    if user_id not in SUPPORT_USER_IDS:
        await query.edit_message_text("У вас нет доступа к этой функции.")
        return

    tickets = await load_tickets()
    if not tickets:
        await query.edit_message_text("В данный момент активных тикетов нет.")
        return

    for ticket in tickets:
        ticket_info = f"Тикет от {ticket['username']} ({ticket['user']}):\nСодержимое: {ticket['message']}\n\n"
        keyboard = [
            [
                InlineKeyboardButton(
                    "Связаться с пользователем", callback_data=f"contact_{ticket['id']}"
                )
            ],
            [
                InlineKeyboardButton(
                    "Выполнить", callback_data=f"resolve_{ticket['id']}"
                )
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=user_id, text=ticket_info, reply_markup=reply_markup
        )


# Функция для связи с пользователем
async def contact_user(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    ticket_id = query.data.split("_")[1]
    tickets = await load_tickets()
    ticket = next((t for t in tickets if t["id"] == ticket_id), None)

    if ticket:
        await context.bot.send_message(
            chat_id=ticket["user"],
            text="Специалист техподдержки хочет с вами связаться. Пожалуйста, ответьте на это сообщение.",
        )
        await query.edit_message_text(
            "Сообщение пользователю отправлено. Ожидайте ответа."
        )
    else:
        await query.edit_message_text("Тикет не найден.")


# Функция для выполнения (удаления) тикета
async def resolve_ticket(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    ticket_id = query.data.split("_")[1]
    tickets = await load_tickets()
    ticket_index = next(
        (i for i, ticket in enumerate(tickets) if ticket["id"] == ticket_id), None
    )

    if ticket_index is not None:
        del tickets[ticket_index]
        await save_tickets(tickets)
        await query.edit_message_text("Тикет успешно выполнен и удален из списка.")
    else:
        await query.edit_message_text("Не удалось найти тикет.")


# Добавьте здесь функции contact_user и resolve_ticket, аналогично описанным выше

if __name__ == "__main__":
    application = (
        Application.builder()
        .token("6809598737:AAHobSxdNa2_AMNLkOs3196vM5b-hSs-ZLM")
        .build()
    )

    # Добавление обработчиков
    application.add_handler(CommandHandler("start", start))

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    application.add_handler(
        CallbackQueryHandler(view_tickets, pattern="^view_tickets$")
    )
    application.add_handler(CallbackQueryHandler(contact_user, pattern="^contact_"))
    application.add_handler(CallbackQueryHandler(resolve_ticket, pattern="^resolve_"))

    application.run_polling()
