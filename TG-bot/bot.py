import logging
import requests
import httpx
import os
from dotenv import load_dotenv
from telegram import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    Update,
    WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    CommandHandler,
    ConversationHandler,
    CallbackContext,
    CallbackQueryHandler
)
from voice_processing.main import convert_ogg_to_wav
from utils.utils import send_audio_to_server, send_text_to_server, format_schedule, get_info, get_categories

load_dotenv()


WAITING_FOR_DOCTOR = 1
WAITING_ANALYSIS = 2
WAITING_QUESTION = 3
CATEGORY_SELECTED = 4

TOKEN = os.getenv("TOKEN")
CHOOSE_MAP_WEBAPP = "https://mellow-caramel-c43daa.netlify.app/"
FASTAPI_URL = os.getenv("FASTAPI_URL")

# Логирование
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)


async def start(update: Update, context: CallbackContext):
    await show_main_keyboard(update, context)


async def handle_voice(update: Update, context: CallbackContext):
    """Обработка голосовых сообщений"""
    chat_id = update.message.chat_id
    voice = update.message.voice
    file_id = voice.file_id

    # Получение ссылки на голосовое сообщение
    file_info = await context.bot.get_file(file_id)
    file_url = file_info.file_path

    response = httpx.get(file_url)
    if response.status_code == 200:
        file_path = f"./voices/voice_{chat_id}.wav"
        convert_ogg_to_wav(response.content, file_path)
        result = await send_audio_to_server(file_path)
        await update.message.reply_text(result)
    else:
        await update.message.reply_text("Ошибка загрузки голосового сообщения!")

async def handle_keyboard_buttons(update: Update, context):
    """Обработка кнопок клавиатуры"""
    text = update.message.text
    match text:
        case "Назад":
            await show_main_keyboard(update, context)
        case "Подтвердить запись ✅":
            await update.message.reply_text("Для продолжения записи обратитесь в колл-центр \n" + "Номер колл-центра: 8(3022)73-70-73")
            await show_main_keyboard(update, context)
        case "О поликлинике 📄":
            result = await get_info("info")
            text = format_schedule(result['info'])
            await update.message.reply_text(text, parse_mode="Markdown")
        case "Исследования 🔬":
            categories = await get_categories("categories")
            categories = categories['categories']
            keyboard = [[InlineKeyboardButton(category, callback_data=category)] for category in categories]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Выберите категорию исследования:", reply_markup=reply_markup)
            return WAITING_ANALYSIS
        case "справки (бассейн)":
            pass
        case "справки (абитуриентам)":
            pass
        case _:
            context.user_data["attempts_to_call_center"] = context.user_data.get("attempts_to_call_center", 0) + 1
            if context.user_data.get("attempts_to_call_center", 0) == 3:
                msg = f"Я не могу помочь вам с этим вопросом \n" + "Номер колл-центра: 8(3022)73-70-73"
                await update.message.reply_text(msg)
                context.user_data["attempts_to_call_center"] = 0


async def analysis_category_chosen(update: Update, context: CallbackContext):
    """Обработка выбора категории анализов"""
    query = update.callback_query
    await query.answer()

    category = query.data

    print(category)

    if category == "справки (бассейн)" or category == "справки (абитуриентам)":
        analyses = await send_text_to_server("analysis-list/certificates", category)
        analysis_list_text = "\n".join(
            [
                f"🧪 - {analysis['full_text'][:100]} : {analysis['price']} руб."
                for analysis in analyses
            ]
        )
        await context.bot.send_message(chat_id=update.effective_chat.id,text=analysis_list_text)
        return ConversationHandler.END

    # Сохраняем категорию для следующего шага
    context.user_data["selected_category"] = category

    # Отправляем запрос на ввод названия услуги
    await context.bot.send_message(chat_id=update.effective_chat.id,text=
        f"🔍 Вы выбрали категорию: {category}\n"
        "📝 Введите название услуги или ключевые слова для поиска:"
    )

    return WAITING_ANALYSIS


async def restore_previous_keyboard(update: Update, context: CallbackContext):
    """Возвращение к предыдущему меню"""
    previous_keyboard = context.user_data.get("last_keyboard")
    if previous_keyboard:
        reply_markup = ReplyKeyboardMarkup(previous_keyboard, resize_keyboard=True)
        await update.message.reply_text("Возвращаюсь назад...", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Нет предыдущего меню.")

async def show_main_keyboard(update: Update, context: CallbackContext):
    """Отправляет стартовое меню"""
    keyboard = [
        [KeyboardButton("Врачи 👩🏻‍⚕️"), KeyboardButton("Исследования 🔬")],
        [KeyboardButton("Задать вопрос 🙋🏻")],
        [KeyboardButton("О поликлинике 📄")],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    context.user_data["last_keyboard"] = keyboard
    await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)
    
async def request_doctor(update: Update, context: CallbackContext):
    await update.message.reply_text("Напишите врача, к которому хотите записаться:")
    return WAITING_FOR_DOCTOR

async def request_question(update: Update, context: CallbackContext):
    await update.message.reply_text("Тут вы можете задать вопрос в свободной форме, и я постараюсь на него ответить! \n" + "Например: (Подготовка к сдаче крови и др.)")
    return WAITING_QUESTION

async def process_doctor(update: Update, context: CallbackContext):
    doctor_name = update.message.text.strip()
    if not doctor_name:
        await update.message.reply_text("Введите корректное название специальности.")
        return WAITING_FOR_DOCTOR

    await update.message.reply_text("Ищем врачей... ⏳")

    doctors = await send_text_to_server("doctors-list", doctor_name)

    if "error" in doctors:
        await update.message.reply_text("Ошибка. Данный врач сейчас не доступен")
        return ConversationHandler.END

    if not doctors:
        await update.message.reply_text("Врачи с такой специализацией не найдены.")
        return ConversationHandler.END

    # Формируем список врачей
    doctor_list_text = "\n".join(
        [f"👨‍⚕️ {doc['specialization']} - {doc['academic_degree']} ({doc['type_visit']}): {doc['price']} руб."
         for doc in doctors]
    )

    await update.message.reply_text(f"Вот список доступных врачей:\n\n{doctor_list_text}")

    # Только после загрузки врачей показываем кнопки
    keyboard = [
        [KeyboardButton("Подтвердить запись ✅")],
        [KeyboardButton("Назад")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Подтвердить запись?", reply_markup=reply_markup)

    return ConversationHandler.END

async def process_question(update: Update, context: CallbackContext):
    question_name = update.message.text.strip()
    if not question_name:
        await update.message.reply_text("Введите корректный вопрос")
        return WAITING_QUESTION

    msg = await send_text_to_server("faq", question_name)

    if msg['answer'] != "Не найдено!":
        await update.message.reply_text(msg['answer'], parse_mode="Markdown")
    else:
        context.user_data["attempts_to_call_center"] = context.user_data.get("attempts_to_call_center", 0) + 1
        await update.message.reply_text("Вопрос не найден!")

    return ConversationHandler.END


async def process_search_query(update: Update, context: CallbackContext):
    user_input = update.message.text
    category = context.user_data.get("selected_category")

    analyses = await send_text_to_server("analysis-list", f"{category}.{user_input}")

    if not analyses or "error" in analyses:
        await update.message.reply_text("Данного исследования не найдено или он находится в другой категории")
        return ConversationHandler.END

    analysis_list_text = "\n".join(
        [
            f"🔬 - {analysis['full_text'][:100]} : {analysis['price']} руб."
            for analysis in analyses
        ]
    )

    await update.message.reply_text(analysis_list_text, parse_mode="Markdown")


    return ConversationHandler.END

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("Врачи 👩🏻‍⚕️"), request_doctor),
            MessageHandler(filters.Regex("Задать вопрос 🙋🏻"), request_question),
            MessageHandler(filters.Regex("Исследования 🔬"), handle_keyboard_buttons)
        ],
        states={
            WAITING_FOR_DOCTOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_doctor)],
            WAITING_ANALYSIS: [
                CallbackQueryHandler(analysis_category_chosen),  # Обработка выбора категории
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_search_query)  # Обработка запроса
            ],
            WAITING_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_question)],
        },
        fallbacks=[]
    )
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(analysis_category_chosen))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_keyboard_buttons))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    logging.info("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
