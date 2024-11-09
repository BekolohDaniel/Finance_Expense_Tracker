from sqlalchemy import Integer
from wtforms import StringField, PasswordField, validators, FloatField
from flask_wtf import FlaskForm
from wtforms.fields.choices import SelectField
from wtforms.fields.simple import SubmitField
from wtforms.validators import DataRequired, NumberRange, Length


# Add each default category to the database
default_categories = [("General", "General"),
                      ("Food", "Food"),
                      ("Transport", "Transport"),
                      ("Rent", "Rent"),
                      ("Entertainment", "Entertainment")]

class RegistrationForm(FlaskForm):
    username = StringField('Username', [validators.Length(min=4, max=25), validators.DataRequired()])
    email = StringField('Email Address', [validators.Length(min=6, max=35), validators.DataRequired()])
    password = PasswordField('New Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords must match')
    ])
    confirm = PasswordField('Repeat Password')
    submit = SubmitField('Register')


class LoginForm(FlaskForm):
    email = StringField('Email Address', [validators.Length(min=6, max=35), validators.DataRequired()])
    password = PasswordField('Password', [validators.DataRequired()])
    submit = SubmitField('LogIn')


# deposit form
class DepositForm(FlaskForm):
    amount = FloatField(
        'Enter amount:',
        validators=[
            DataRequired(message="Amount is required."),
            NumberRange(min=1, max=10000000000000000, message="Amount must be between 1 and 100.")
        ]
    )
    description = StringField(
        'Description',
        validators=[
            DataRequired(message="Description is required."),
            Length(min=6, max=50, message="Description must be between 6 and 50 characters.")
        ]
    )
    category = SelectField('Category', choices=default_categories, validators=[DataRequired()])
    submit = SubmitField('Deposit')
