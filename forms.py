from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, DecimalField, FieldList, FormField
from wtforms.validators import DataRequired, URL, Email, NumberRange, Length

class RegisterForm(FlaskForm):
    name = StringField(
        label='Name', 
        validators=[DataRequired(), Length(min=3, max=15)],
        render_kw={"class": "form-control"}
        )
    email = StringField(
        label='Email', 
        validators=[DataRequired(), Email()],
        render_kw={"class": "form-control"}
        )
    password = PasswordField(
        label='Password', 
        validators=[DataRequired(), Length(min=3, max=25)],
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
        validators=[DataRequired(), Length(min=3, max=25)],
        render_kw={"class": "form-control"}
        )
    submit = SubmitField(
        label='Sign In',
        render_kw={"class": "btn btn-primary"}
        )