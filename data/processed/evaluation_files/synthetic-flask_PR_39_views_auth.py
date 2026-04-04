import os
import sys
import re
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, Email, EqualTo
from yourapp.models import User
from yourapp import db

blueprint = Blueprint('auth', __name__)

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

@blueprint.route('/register', methods=['GET', 'POST'])
def register() -> str:
  form = RegistrationForm()
  if form.validate_on_submit():
    user = User(username=form.username.data, email=form.email.data, password=form.password.data)
    db.session.add(user)
    db.session.commit()
    flash('Your account has been created! You can now log in.', 'success')
    return redirect(url_for('auth.login'))
  return render_template('register.html', title='Register', form=form)

@blueprint.route('/login', methods=['GET', 'POST'])
def login() -> str:
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            flash('Logged in successfully!', 'success')
            return redirect(url_for('main.index'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@blueprint.route('/logout')
def logOut() -> str:
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

anotherFunction = lambda: None