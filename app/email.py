from flask import url_for
# for create token
from itsdangerous import URLSafeSerializer, SignatureExpired
# for send mail
import smtplib, ssl 
# for create new password
import random 
import string
# app Config
from app import app
from app.config import Config


# smtp-mail config
smtp_server = "smtp.gmail.com"
port = 587
sender_email = "vidok.noreply@gmail.com"
password = "wtebbtdtdhlquejb"


# For create token
serializer = URLSafeSerializer(Config.SECRET_KEY)

def create_pw():
    letters = string.ascii_letters
    result_pw = ''.join(random.choice(letters) for i in range(7))
    return result_pw

def create_confirm_code():
    letters = string.digits
    result_code = ''.join(random.choice(letters) for i in range(6))
    return result_code

def sendmail_pw(receiver_email, new_pw):
    message = f"This is your password {new_pw}"
    # Create a secure SSL context
    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_server,port) as server:
        server.ehlo() # Can be omitted
        server.starttls(context=context) # Secure the connection
        server.ehlo() # Can be omitted
        server.login(sender_email, password)
        # Send email here
        server.sendmail(sender_email, receiver_email, message)

def sendmail_code(receiver_email, code):
    message = f"This is your code {code}"
    # Create a secure SSL context
    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_server,port) as server:
        server.ehlo() # Can be omitted
        server.starttls(context=context) # Secure the connection
        server.ehlo() # Can be omitted
        server.login(sender_email, password)
        # Send email here
        server.sendmail(sender_email, receiver_email, message)
# def send_token(receiver_email):
#     token = serializer.dumps(receiver_email, salt='email-confirm')
#     link = url_for('confirm_email', token=token, _external = True)
#     # Create a secure SSL context
#     context = ssl.create_default_context()
#     message = f"Click on this link to confirm {link}"
#     with smtplib.SMTP(smtp_server,port) as server:
#         server.ehlo() # Can be omitted
#         server.starttls(context=context) # Secure the connection
#         server.ehlo() # Can be omitted
#         server.login(sender_email, password)
#         server.sendmail(sender_email, receiver_email, message)
