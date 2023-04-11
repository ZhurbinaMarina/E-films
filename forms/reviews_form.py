from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField
from wtforms import BooleanField, SubmitField
from wtforms.validators import DataRequired


class ReviewsForm(FlaskForm):
    title = StringField('Название фильма', validators=[DataRequired()])
    content = TextAreaField("Содержание отзыва")
    is_private = BooleanField("Личное")
    submit = SubmitField('Применить')
