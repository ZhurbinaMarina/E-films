from flask import Flask, render_template, redirect, abort, request, jsonify, make_response, session, url_for
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import requests
import os
from data import db_session
from data.users import User
from data.reviews import Reviews
from forms.user_form import RegisterForm, LoginForm, SearchMovieForm, EditingProfileForm
from forms.reviews_form import ReviewsForm
from config import KINOPOISK_API_TOKEN

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route("/")
@app.route('/index/<sort_option>')
def main_page(sort_option=None):
    options = {'cartoon': 'мультфильм', 'fantastic': 'фантастика', 'action_movie': 'боевик',
               'comedy': 'комедия', 'adventures': 'приключения', 'family': 'семейный', 'detective': 'детектив',
               'drama': 'драма', 'melodrama': 'мелодрама', 'horror': 'ужасы'}
    db_sess = db_session.create_session()
    if current_user.is_authenticated:
        reviews = db_sess.query(Reviews).filter(
            (Reviews.user == current_user) | (Reviews.is_private != True))
    else:
        reviews = db_sess.query(Reviews).filter(Reviews.is_private != True)
    sort_reviews = []
    if sort_option == 'by_rating':
        sort_reviews = sorted(reviews, key=lambda x: x.rating, reverse=True)
    elif sort_option in options.keys():
        for review in reviews:
            if options[sort_option] in review.genres:
                sort_reviews.append(review)
    else:
        sort_reviews = reviews[::-1]
    return render_template("index.html", reviews=sort_reviews, title='E-films',
                           css_file=f"{url_for('static', filename='css/rating_output.css')}",
                           sort_option=sort_option)


@app.route('/register', methods=['GET', 'POST'])
def register(): # Renamed `reqister` to register
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пароли не совпадают")
        try: # Added a try/except block to handle errors that might occur when calling add_user.
            db_sess = db_session.create_session()
            if db_sess.query(User).filter(User.email == form.email.data).first():
                return render_template('register.html', title='Регистрация',
                                    form=form,
                                    message="Такой пользователь уже есть")
            add_user(form.email.data, form.password.data, form.name.data)
            db.sess.commit() # Added db_sess.commit() to commit changes made to the database and 
            db.sess.close() # Closed the database session using db_sess.close() after committing or rolling back the transaction.
            return redirect(url_for('login')) # Replaced the hardcoded redirect URL '/login' with the url_for function. This makes the redirect more flexible and less error-prone in case the route changes in the future.
        except Exception as e:
            db.sess.rollback() # db_sess.rollback() in case an error occurs.
            db.sess.close()
    return render_template('register.html', title='Регистрация', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            session['user_name'] = user.name
            return redirect("/")
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/editing', methods=['GET', 'POST'])
def editing():
    form = EditingProfileForm()
    if request.method == "GET":
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.id == current_user.id).first()
        if user:
            form.name.data = user.name
            form.email.data = user.email
            form.about.data = user.about
        else:
            abort(404)
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.id == current_user.id).first()
        if request.form.get('_checkBox'):
            if not user.check_password(form.old_password.data):
                return render_template('editing.html', title='Редактирование профиля',
                                       form=form,
                                       message="Неверный пароль")
            if form.old_password.data == form.new_password.data:
                return render_template('editing.html', title='Редактирование профиля',
                                       form=form,
                                       message="Новый пароль совпадает со старым")
        if user:
            user.email = form.email.data
            user.about = form.about.data
            if request.form.get('_checkBox'):
                user.set_password(form.new_password.data)
            if form.name.data is not None:
                user.name = form.name.data
            db_sess.commit()
            return redirect('/')
        else:
            abort(404)
    return render_template('editing.html', title='Редактирование профиля', form=form)


@app.route('/reviews/<page_title>', methods=['GET', 'POST'])
@login_required
def add_reviews(page_title):
    form = ReviewsForm()
    if page_title != 'index':
        if request.method == "GET":
            form.title.data = page_title
    if form.validate_on_submit():
        movies = search_movie_api(form.title.data)
        genres_movie = []
        if movies == []:
            return render_template('reviews.html', title='Добавление отзыва',
                                   form=form, header='Добавление',
                                   css_file=f"{url_for('static', filename='css/rating_setting.css')}",
                                   message="Такого фильма не существует")
        else:
            flag = False
            for movie in movies:
                if movie['name'] == form.title.data:
                    flag = True
                    genres_movie = movie['genres']
                    print(genres_movie)
            if flag is False:
                return render_template('reviews.html', title='Добавление отзыва',
                                       form=form, header='Добавление',
                                       css_file=f"{url_for('static', filename='css/rating_setting.css')}",
                                       message="Такого фильма не существует")
        if 'rating' not in request.form:
            return render_template('reviews.html', title='Добавление отзыва',
                                   form=form, header='Добавление',
                                   css_file=f"{url_for('static', filename='css/rating_setting.css')}",
                                   message="Поставьте рейтинг фильму")
        db_sess = db_session.create_session()
        reviews = Reviews()
        reviews.title = form.title.data
        reviews.content = form.content.data
        reviews.is_private = form.is_private.data
        reviews.rating = int(request.form['rating'])
        reviews.genres = genres_movie
        current_user.reviews.append(reviews)
        db_sess.merge(current_user)
        db_sess.commit()
        if page_title == 'index':
            return redirect('/')
        else:
            return redirect(f'/movie_info/{page_title}')
    return render_template('reviews.html', title='Добавление отзыва',
                           form=form, header='Добавление',
                           css_file=f"{url_for('static', filename='css/rating_setting.css')}")


@app.route('/reviews/<page_title>/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_reviews(page_title, id):
    form = ReviewsForm()
    rating = None
    if request.method == "GET":
        db_sess = db_session.create_session()
        reviews = db_sess.query(Reviews).filter(Reviews.id == id,
                                                Reviews.user == current_user).first()
        if reviews:
            form.title.data = reviews.title
            form.content.data = reviews.content
            form.is_private.data = reviews.is_private
            rating = reviews.rating
        else:
            abort(404)
    if form.validate_on_submit():
        movies = search_movie_api(form.title.data)
        if movies == []:
            return render_template('reviews.html', title='Добавление отзыва',
                                   form=form, header='Добавление',
                                   css_file=f"{url_for('static', filename='css/rating_setting.css')}",
                                   message="Такого фильма не существует")
        else:
            flag = False
            for movie in movies:
                if movie['name'] == form.title.data:
                    flag = True
            if flag is False:
                return render_template('reviews.html', title='Добавление отзыва',
                                       form=form, header='Добавление',
                                       css_file=f"{url_for('static', filename='css/rating_setting.css')}",
                                       message="Такого фильма не существует")
        db_sess = db_session.create_session()
        reviews = db_sess.query(Reviews).filter(Reviews.id == id,
                                                Reviews.user == current_user
                                                ).first()
        rating = reviews.rating
        if 'rating' not in request.form:
            return render_template('reviews.html', title='Добавление отзыва',
                                   form=form, header='Добавление',
                                   css_file=f"{url_for('static', filename='css/rating_setting.css')}",
                                   message="Поставьте рейтинг фильму", rating=rating)
        if reviews:
            reviews.title = form.title.data
            reviews.content = form.content.data
            reviews.is_private = form.is_private.data
            reviews.rating = int(request.form['rating'])
            db_sess.commit()
            if page_title == 'index':
                return redirect('/')
            else:
                return redirect(f'/movie_info/{page_title}')
        else:
            abort(404)
    return render_template('reviews.html',
                           title='Редактирование отзыва',
                           form=form, header='Редактирование',
                           css_file=f"{url_for('static', filename='css/rating_setting.css')}",
                           rating=rating)


@app.route('/reviews_delete/<page_title>/<int:id>', methods=['GET', 'POST'])
@login_required
def reviews_delete(page_title, id):
    db_sess = db_session.create_session()
    reviews = db_sess.query(Reviews).filter(Reviews.id == id,
                                            Reviews.user == current_user
                                            ).first()
    if reviews:
        db_sess.delete(reviews)
        db_sess.commit()
    else:
        abort(404)
    if page_title == 'index':
        return redirect('/')
    else:
        return redirect(f'/movie_info/{page_title}')


@app.route('/search_movie', methods=['GET', 'POST'])
def search_movie():
    movie_form = SearchMovieForm()
    search_on = False
    select_fields = ['name', 'id', 'rating', 'year', 'slogan', 'persones', 'genres', 'fees', 'premiere', 'description',
                     'logo', 'poster', 'video', 'releaseYears']
    movies = []
    if request.method == 'GET':
        if request.args.getlist('input_search') != []:
            search_on = True
            name_film = request.args.getlist('input_search')[0]
            if name_film != '':
                movies = search_movie_api(name_film)
                # for movie in movies:
                #     for elem in movie.keys():
                #          print(f'{elem}: {movie[elem]}')
    return render_template('search_movie.html', title='Поиск фильмов', movie_form=movie_form, search_on=search_on,
                           select_fields=select_fields, movies=movies)


@app.route('/movie_info/<movie_name>', methods=['GET', 'POST'])
def movie_info(movie_name):
    select_fields = ['name', 'id', 'rating', 'year', 'slogan', 'persones', 'genres', 'fees', 'premiere', 'description',
                     'logo', 'poster', 'video', 'releaseYears']
    movie = None
    reviews = None
    if request.method == 'GET':
        if movie_name != '':
            movie = search_movie_api(movie_name)[0]
            db_sess = db_session.create_session()
            reviews = db_sess.query(Reviews).filter(Reviews.title == movie_name).all()
    return render_template('movie_info.html', title=f'{movie_name}',
                           select_fields=select_fields, movie=movie, reviews=reviews,
                           css_file=f"{url_for('static', filename='css/rating_output.css')}")


def search_movie_api(name_movie):
    file = requests.get(
        f"https://api.kinopoisk.dev/v1/movie?token={KINOPOISK_API_TOKEN}&name={name_movie}").json()
    movies = file['docs']
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
    return movies


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


@app.errorhandler(400)
def bad_request(_):
    return make_response(jsonify({'error': 'Bad Request'}), 400)


def add_user(email, password, name=None, about=None):
    db_sess = db_session.create_session()
    user = User()
    user.email = email
    user.set_password(password)
    if name is not None:
        user.name = name
    if about is not None:
        user.about = about
    db_sess.add(user)
    db_sess.commit()


def web_main():
    db_session.global_init("db/blogs.db")
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)


if __name__ == '__main__':
    web_main()
