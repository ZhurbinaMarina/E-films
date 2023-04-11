from flask import Flask, render_template, redirect, abort, request, jsonify, make_response, session
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import requests
from data import db_session
from data.users import User
from data.reviews import Reviews
from forms.user_form import RegisterForm, LoginForm, SearchMovieForm
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

    return render_template("index.html", reviews=reviews, title='Efilms')


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


@app.route('/reviews', methods=['GET', 'POST'])
@login_required
def add_reviews():
    form = ReviewsForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        reviews = Reviews()
        reviews.title = form.title.data
        reviews.content = form.content.data
        reviews.is_private = form.is_private.data
        current_user.reviews.append(reviews)
        db_sess.merge(current_user)
        db_sess.commit()
        return redirect('/')
    return render_template('reviews.html', title='Добавление отзыва',
                           form=form)


@app.route('/reviews/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_reviews(id):
    form = ReviewsForm()
    if request.method == "GET":
        db_sess = db_session.create_session()
        reviews = db_sess.query(Reviews).filter(Reviews.id == id,
                                          Reviews.user == current_user).first()
        if reviews:
            form.title.data = reviews.title
            form.content.data = reviews.content
            form.is_private.data = reviews.is_private
        else:
            abort(404)
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        reviews = db_sess.query(Reviews).filter(Reviews.id == id,
                                          Reviews.user == current_user
                                          ).first()
        if reviews:
            reviews.title = form.title.data
            reviews.content = form.content.data
            reviews.is_private = form.is_private.data
            db_sess.commit()
            return redirect('/')
        else:
            abort(404)
    return render_template('reviews.html',
                           title='Редактирование отзыва',
                           form=form)


@app.route('/reviews_delete/<int:id>', methods=['GET', 'POST'])
@login_required
def reviews_delete(id):
    db_sess = db_session.create_session()
    reviews = db_sess.query(Reviews).filter(Reviews.id == id,
                                      Reviews.user == current_user
                                      ).first()
    if reviews:
        db_sess.delete(reviews)
        db_sess.commit()
    else:
        abort(404)
    return redirect('/')


@app.route('/search_movie', methods=['GET', 'POST'])
def search_movie():
    movie_form = SearchMovieForm()
    search_on = False
    select_fields = ['name', 'id', 'rating', 'year', 'slogan', 'genres', 'description',
                    'status', 'votes', 'logo', 'poster', 'genres',
                    'persones',
                    'reviewInfo', 'facts']
    movies = []
    if request.method == 'GET':
        if request.args.getlist('input_search') != []:
            search_on = True
            name_film = request.args.getlist('input_search')[0]
            if name_film != '':
                print(request.args.getlist('input_search')[0])
                movies = search_movie_api(name_film)
                print(movies)
    return render_template('search_movie.html', title='Поиск фильмов', movie_form=movie_form, search_on=search_on,
                           select_fields=select_fields, movies=movies)


def search_movie_api(name_movie):
    TOKEN = "K93Q796-7QDMZ0T-GE8GE19-979AGST"
    file = requests.get(
            f"https://api.kinopoisk.dev/v1/movie?token={TOKEN}&name={name_movie}").json()
    movies = file['docs']
    return movies


def main():
    db_session.global_init("db/blogs.db")
    app.run(port=8080, host='127.0.0.1')  # port=8080, host='127.0.0.1'
    db_sess = db_session.create_session()

    # for user in db_sess.query(User).filter((User.id > 1) | (User.email.notilike("%1%"))):
    #     print(user)


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


if __name__ == '__main__':
    main()
