import logging
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, MessageHandler, filters, CommandHandler, ConversationHandler
import aiohttp
from config import BOT_TOKEN, KINOPOISK_API_TOKEN

proxy_url = "socks5://user:pass@host:port"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
)

logger = logging.getLogger(__name__)

reply_keyboard = [['Информация о фильме', '/start_kinopoisk'], ['Собакен', 'Котик']]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)


async def get_response(url, params=None):
    logger.info(f"getting {url}")
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            return await resp.json()


async def start_kinopoisk(update, context):
    user = update.effective_user
    print(user.mention_html())
    await update.message.reply_html(
        rf"""Привет, {user.mention_html()} 
Ты можешь отправить название интересующего вас фильма, а я выдам подробную информацию о нем.""")
    return 1


async def api_kinopoisk(update, context):
    name_film = update.message.text
    request = f"https://api.kinopoisk.dev/v1/movie?token={KINOPOISK_API_TOKEN}&name={name_film}"
    response = await get_response(request)
    movies = response['docs']
    print(movies)
    print(len(movies))
    for movie in movies:
        if 'genres' in movie.keys():
            genres = movie['genres']
            edited_genres = []
            for elem in genres:
                edited_genres.append(elem['name'])
            edited_genres = ', '.join(edited_genres)
            movie['genres'] = edited_genres
        if 'countries' in movie.keys():
            countries = movie['countries']
            edited_countries = []
            for elem in countries:
                edited_countries.append(elem['name'])
            edited_countries = ', '.join(edited_countries)
            movie['countries'] = edited_countries
    film_exists = False
    movie = None
    for elem in movies:
        if elem['name'] == name_film:
            film_exists = True
            movie = elem
    if film_exists:
        print(movie)
        print(movie['description'])
        message = f"""{movie['name']}\n ID: {movie.get('id', 'None')}  
Рейтинг КП: {movie['rating']['kp']}  Рейтинг IMDB: {movie['rating']['imdb']}\n
Год: {movie['year']}\n
Жанры: {movie['genres']}\n
Страны: {movie['countries']}\n
Описание фильма: {movie['description']}"""
        print(message)
        print()

        await context.bot.send_photo(
            update.message.chat_id,
            movie['poster']['url'],
            caption=f"{message}")
    else:
        await update.message.reply_text("К сожалению, я не смог найти такой фильм")
    return ConversationHandler.END


async def stop_kinopoisk(update, context):
    await update.message.reply_text(
        f"Спасибо, что пользуйтесь нашими услугами")
    return ConversationHandler.END


async def start(update, context):
    await update.message.reply_text(
        "Я бот-справочник. Какая информация вам нужна?",
        reply_markup=markup)


async def help_command(update, context):
    await update.message.reply_text("Я пока не умею помогать... Я только ваше эхо.")


async def echo(update, context):
    if update.message.text == 'Собакен':
        await api_dog(update, context)
    elif update.message.text == 'Котик':
        await api_kot(update, context)
    elif update.message.text == 'Информация о фильме':
        await start_kinopoisk(update, context)


async def close_keyboard(update, context):
    await update.message.reply_text(
        "Ok",
        reply_markup=ReplyKeyboardRemove()
    )


async def api_kot(update, context):
    api_kot_uri = "https://api.thecatapi.com/v1/images/search"
    response = await get_response(api_kot_uri)

    await context.bot.send_photo(
        update.message.chat_id,
        response[0]['url'],
        caption="Ваш котик:"
    )


async def api_dog(update, context):
    api_kot_uri = "https://dog.ceo/api/breeds/image/random"
    response = await get_response(api_kot_uri)

    await context.bot.send_photo(
        update.message.chat_id,
        response['message'],
        caption="Ваш собакен:"
    )


def main():
    application = Application.builder().token(BOT_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start_kinopoisk', start_kinopoisk)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, api_kinopoisk)]
        },
        fallbacks=[CommandHandler('stop_kinopoisk', stop_kinopoisk)]
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("close", close_keyboard))
    application.add_handler(CommandHandler("api_kot", api_kot))
    application.add_handler(CommandHandler("api_dog", api_dog))
    text_handler = MessageHandler(filters.TEXT, echo)
    application.add_handler(text_handler)

    application.run_polling()


if __name__ == '__main__':
    main()
