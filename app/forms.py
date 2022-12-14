# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from flask_wtf          import FlaskForm
from flask_wtf.file     import FileField, FileRequired
from wtforms            import StringField, TextAreaField, SubmitField, PasswordField
from wtforms.validators import InputRequired, Email, DataRequired

class LoginForm(FlaskForm):
	username    = StringField  (u'Username'  , validators=[DataRequired()])
	password    = PasswordField(u'Password'  , validators=[DataRequired()])

class RegisterForm(FlaskForm):
	fname        = StringField  (u'First Name', validators=[DataRequired()])
	lname        = StringField  (u'Last Name', validators=[DataRequired()])
	username    = StringField  (u'Username'  , validators=[DataRequired()])
	password    = PasswordField(u'Password'  , validators=[DataRequired()])
	email       = StringField  (u'Email'     , validators=[DataRequired(), Email()])
	phone_number = StringField (u'Phone Number'  , validators=[DataRequired()])

class AccountInfor(FlaskForm):
	new_fname        = StringField  (u'First Name')
	new_lname        = StringField  (u'Last Name')
	new_email = StringField(u'Email', validators=[Email()])
	new_phone_num = StringField(u'Phone Number')
	new_password = PasswordField(u'Password')
	password    = PasswordField(u'Password')

class PasswordRequestForm(FlaskForm):
	email = StringField(u'Email', validators=[DataRequired(), Email()])

class ConfirmEmail(FlaskForm):
	confirm_code = StringField(u'Confirm Code', validators=[DataRequired()])
