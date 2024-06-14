import requests
import logging
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
from telegram import ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from tokens import TOKEN

NYT_API_KEY = 'sGqG0K9kRgayMZEYLbv0aGpixAWXIAt9'

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

reply_keyboard = [['/web_scraping', '/search_book'],
                  ['/author_info', '/help']]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)

AUTHOR_INFO = range(1)
SEARCH_BOOK = range(1)

def log_user(user_id, message):
    filename = f"{user_id}.log"
    with open(filename, 'a') as file:
        file.write(message + '\n')

async def web_scraping_task(update, context):
    try:
        if "current_index" not in context.user_data:
            context.user_data["current_index"] = 0
        animal_names = getAnimalName()
        current_index = context.user_data["current_index"]
        end_index = current_index + 3
        for i in range(current_index, end_index):
            if i >= len(animal_names):
                await update.message.reply_text("Все цитаты извлечены.")
                return

            try:
                name = animal_names[i]
                url = f'https://a-z-animals.com/animals/{name}/'
                req = Request(url, headers={'User-Agent': 'Chrome/58.0.3029.110'})
                webpage = urlopen(req).read()
                data = BeautifulSoup(webpage, 'html.parser')
                funfact = data.find('p', {'class': 'mb-0'})
                if funfact and funfact.text.strip():
                    await update.message.reply_text(f"{i+1}. {name}: {funfact.text.strip()}")
                else:
                    await update.message.reply_text(f"{i+1}. {name}: no data")
            except Exception as e:
                await update.message.reply_text(f"Ошибка при обработке данных: {e}")
                continue

        context.user_data["current_index"] = end_index

    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")

def getAnimalName():
    nameList = []
    url = 'https://a-z-animals.com/animals/'
    req = Request(url, headers={'User-Agent': 'Chrome/58.0.3029.110'})
    webpage = urlopen(req).read()
    data = BeautifulSoup(webpage, 'html.parser')
    animalList = data.find_all('li', {'class':'list-item col-md-4 col-sm-6'})
    for i in animalList:
        name = i.find_next_sibling()
        if name:
            nameList.append(name.text)
    properList = [x.replace(' ', '-') for x in nameList]
    return properList

async def start(update, context):
    user = update.effective_user
    log_user(user.id, f"User {user.id} started the bot.")
    await update.message.reply_text(
        "Привет! Я бот для работы с API книг New York Times.",
        reply_markup=markup
    )

async def search_book_start(update, context):
    user = update.effective_user
    log_user(user.id, f"User {user.id}: Вводит название книги.")
    await update.message.reply_text("Введите название книги:")
    return SEARCH_BOOK

async def search_book_response(update, context):
    title = update.message.text
    response = requests.get( f'https://api.nytimes.com/svc/books/v3/lists/best-sellers/history.json?title={title}&api-key={NYT_API_KEY}')
    data = response.json()
    if data['status'] == 'OK':
        books = data['results']
        if books:
            book = books[0]
            message = f"{book['title']} by {book['author']}"
        else:
            message = 'Книга не найдена в списке бестселлеров.'
        user = update.effective_user
        log_user(user.id, f"User {user.id}: Ищиет книгу.\n {message}")
        await update.message.reply_text(message)
    return ConversationHandler.END

async def author_info_start(update, context):
    user = update.effective_user
    log_user(user.id, f"User {user.id}: Вводит имя автора.")
    await update.message.reply_text("Введите имя автора:")
    return AUTHOR_INFO

async def author_info_response(update, context):
    author = update.message.text
    response = requests.get(f'https://api.nytimes.com/svc/books/v3/lists/best-sellers/history.json?author={author}&api-key={NYT_API_KEY}')
    data = response.json()
    if data['status'] == 'OK':
        books = data['results']
        if books:
            message = f"Книги автора {author} в списке бестселлеров:\n"
            for book in books:
                message += f"{book['title']}\n"
        else:
            message = f'Автор {author} не найден в списке бестселлеров.'
        user = update.effective_user
        log_user(user.id, f"User {user.id}: Ищет информацию об авторе.\n {message}")
        await update.message.reply_text(message)
    return ConversationHandler.END

async def help(update, context):
    user = update.effective_user
    log_user(user.id, f"User {user.id} requested help.")
    await update.message.reply_text(
        "Вот доступные команды:\n/author_info - Выводит книги введенного автора, которые были бестселлерами\n/search_book - Ищет автора по названию книги\n/bestsellers - bla bla\n/help - Объяснение команд")

def main():
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('author_info', author_info_start)],
        states={
            AUTHOR_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, author_info_response)]
        },
        fallbacks=[]
    )

    search = ConversationHandler(
        entry_points=[CommandHandler('search_book', search_book_start)],
        states={
            SEARCH_BOOK: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_book_response)]
        },
        fallbacks=[]
    )

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('web_scraping', web_scraping_task))
    application.add_handler(search)
    application.add_handler(CommandHandler('help', help))
    application.add_handler(conv_handler)

    application.run_polling()

if __name__ == '__main__':
    main()
