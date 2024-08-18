from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, DecimalField, FieldList, FormField
from wtforms.validators import DataRequired, URL, Email, NumberRange

class RegisterForm(FlaskForm):
    name = StringField(
        label='Name', 
        validators=[DataRequired()],
        render_kw={"class": "form-control"}
        )
    email = StringField(
        label='Email', 
        validators=[DataRequired(), Email()],
        render_kw={"class": "form-control"}
        )
    password = PasswordField(
        label='Password', 
        validators=[DataRequired()],
        render_kw={"class": "form-control", "autocomplete":"new-password"}
        )
    submit = SubmitField(
        label='Sign Up',
        render_kw={"class": "custom-btn"})


class LoginForm(FlaskForm):
    email = StringField(
        label='Email', 
        validators=[DataRequired(), Email()],
        render_kw={"class": "form-control"}
        )
    password = PasswordField(
        label='Password', 
        validators=[DataRequired()],
        render_kw={"class": "form-control"}
        )
    submit = SubmitField(
        label='Sign In',
        render_kw={"class": "btn btn-primary"}
        )
    

class PlayerForm(FlaskForm):
    player_name = StringField('Player Name', validators=[DataRequired()])
    buyin = DecimalField('Buy-in Amount', validators=[DataRequired(), NumberRange(min=0)], places=2)
    cashout = DecimalField('Cash-out Amount', validators=[DataRequired(), NumberRange(min=0)], places=2)


class EditGameForm(FlaskForm):
    players = FieldList(FormField(PlayerForm), min_entries=1)