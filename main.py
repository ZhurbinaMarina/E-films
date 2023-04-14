from flask import Flask, render_template, redirect, abort, request, jsonify, make_response, session, url_for
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import requests
from data import db_session
from data.users import User
from data.reviews import Reviews
from forms.user_form import RegisterForm, LoginForm, SearchMovieForm, EditingProfileForm
from forms.reviews_form import ReviewsForm

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
@app.route('/index')
def main_page():
    db_sess = db_session.create_session()
    if current_user.is_authenticated:
        reviews = db_sess.query(Reviews).filter(
            (Reviews.user == current_user) | (Reviews.is_private != True))
    else:
        reviews = db_sess.query(Reviews).filter(Reviews.is_private != True)

    return render_template("index.html", reviews=reviews, title='E-films',
                           css_file=f"{url_for('static', filename='css/rating_output.css')}")


@app.route('/register', methods=['GET', 'POST'])
def reqister():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пароли не совпадают")
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть")
        add_user(form.email.data, form.password.data, form.name.data)
        return redirect('/login')
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
    TOKEN = "K93Q796-7QDMZ0T-GE8GE19-979AGST"
    file = requests.get(
        f"https://api.kinopoisk.dev/v1/movie?token={TOKEN}&name={name_movie}").json()
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


def main():
    db_session.global_init("db/blogs.db")
    app.run(port=8080, host='127.0.0.1')  # port=8080, host='127.0.0.1'


if __name__ == '__main__':
    main()
