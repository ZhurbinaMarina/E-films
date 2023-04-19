import logging
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, MessageHandler, filters, CommandHandler, ConversationHandler
import aiohttp
from config import BOT_TOKEN, KINOPOISK_API_TOKEN

proxy_url = "socks5://user:pass@host:port"

# logging.basicConfig(
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
# )
#
# logger = logging.getLogger(__name__)

reply_keyboard = [['/start_kinopoisk'], ['Собакен', 'Котик']]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)
requested_movies = []
ind = 1


async def get_response(url, params=None):
    # logger.info(f"getting {url}")
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            return await resp.json()


async def start_kinopoisk(update, context):
    user = update.effective_user
    print(user.mention_html())
    await update.message.reply_html(
        rf"""Привет, {user.mention_html()} 
Вы можете отправить название интересующего вас фильма, а я выдам подробную информацию о нем.
Вы можете прервать диалог, послав команду /stop_kinopoisk.""")
    return 1


async def api_kinopoisk(update, context):
    global requested_movies
    name_film = update.message.text
    request = f"https://api.kinopoisk.dev/v1/movie?token={KINOPOISK_API_TOKEN}&name={name_film}"
    response = await get_response(request)
    movies = response['docs']

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
    if movies:
        requested_movies = movies
        movie = movies[0]
        message = f"""{movie['name']}\n ID: {movie.get('id', 'None')}  
Рейтинг КП: {movie['rating']['kp']}  Рейтинг IMDB: {movie['rating']['imdb']}\n
Год: {movie['year']}\n
Жанры: {movie['genres']}\n
Страны: {movie['countries']}\n
Описание фильма: {movie['description']}\n
Если вы имели ввиду другой фильм напишите 'Другой'\n
Вы можете прервать диалог, послав команду /stop_kinopoisk."""

        if movie['poster']:
            await context.bot.send_photo(
                update.message.chat_id,
                movie['poster']['url'],
                caption=f"{message}")
        else:
            await update.message.reply_text(f"{message}")
    else:
        await update.message.reply_text("К сожалению, я не смог найти такой фильм")
    return ConversationHandler.END


async def api_kinopoisk_dop(update, context):
    global requested_movies
    movie = requested_movies[ind]
    message = f"""{movie['name']}\n ID: {movie.get('id', 'None')}  
Рейтинг КП: {movie['rating']['kp']}  Рейтинг IMDB: {movie['rating']['imdb']}\n
Год: {movie['year']}\n
Жанры: {movie['genres']}\n
Страны: {movie['countries']}\n
Описание фильма: {movie['description']}\n
Если вы имели ввиду другой фильм напишите 'Другой'\n
Вы можете прервать диалог, послав команду /stop_kinopoisk."""

    if movie['poster']:
        await context.bot.send_photo(
            update.message.chat_id,
            movie['poster']['url'],
            caption=f"{message}")
    else:
        await update.message.reply_text(f"{message}")


async def stop_kinopoisk(update, context):
    global requested_movies
    requested_movies = []
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
    global requested_movies
    global ind
    if update.message.text == 'Собакен':
        await api_dog(update, context)
    elif update.message.text == 'Котик':
        await api_kot(update, context)
    elif update.message.text.lower() == 'другой':
        print('BBBBBBBBBBBBB')
        print(requested_movies)
        print(len(requested_movies))
        if requested_movies != [] and ind < len(requested_movies):
            print('CCCCCC')
            await api_kinopoisk_dop(update, context)
            ind += 1
            if ind >= len(requested_movies):
                ind = 1
                requested_movies = []
        else:
            await update.message.reply_text("Других фильмов не осталось :(")
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


def bot_main():
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
    application.add_handler(CommandHandler("stop_kinopoisk", stop_kinopoisk))
    text_handler = MessageHandler(filters.TEXT, echo)
    application.add_handler(text_handler)

    application.run_polling()


if __name__ == '__main__':
    bot_main()
