# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

# Python modules
import os, logging 
import json
from datetime import datetime
from unittest import result
from sqlalchemy import desc

# Flask modules``
from flask               import render_template, request, url_for, redirect, send_from_directory, jsonify, Response
from flask_login         import login_user, logout_user, current_user, login_required
from werkzeug.exceptions import HTTPException, NotFound, abort
from jinja2              import TemplateNotFound
from sqlalchemy import func

# App modules
from app        import app, lm, db, bc
from app.models import Users, Ligands
from app.forms  import ConfirmEmail, LoginForm, ModifyInfoForm, PasswordRequestForm, RegisterForm
from app.chem_utils import DockingAgent, save_compound
from app.dss_system import DSSSystem
from app.util   import create_user_folders, response
from app.config import Config
from app.email import create_confirm_code, create_pw, sendmail_code, sendmail_pw

# Create session
session ={}
session['confirmed'] = False
session['confirm_code_hash'] = '123'
session['email'] = 'empty'

# pro   de login manager with load_user callback
@lm.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

# Logout user
@app.route('/logout.html')
def logout():
    logout_user()
    return redirect(url_for('index'))

# Register a new user
@app.route('/register.html', methods=['GET', 'POST'])
def register():
    # declare the Registration Form
    form = RegisterForm(request.form)

    msg     = None
    success = False
    if request.method == 'GET': 

        return render_template( 'accounts/register.html', form=form, msg=msg)

    # check if both http method is POST and form is valid on submit
    if form.validate_on_submit():
        # assign form data to variables
        username = request.form.get('username', '', type=str)
        password = request.form.get('password', '', type=str) 
        email    = request.form.get('email'   , '', type=str) 
        
        fname = request.form.get('fname','',type=str)
        lname = request.form.get('lname','',type=str)
        phone_num = request.form.get('phone_number', '', type=int)
        # filter User out of database through username
        user = Users.query.filter_by(user=username).first()

        # filter User out of database through username
        user_by_email = Users.query.filter_by(email=email).first()

        if user or user_by_email:
            msg = 'Error: User exists!'
        elif phone_num == '':
            msg = 'Error: Input phone number again!'
        else:
            confirm_code = create_confirm_code()
            sendmail_code(email, confirm_code)
            confirm_code_hash = bc.generate_password_hash(confirm_code)
            session['confirm_code_hash'] = confirm_code_hash
            pw_hash = bc.generate_password_hash(password)
            user = Users(username, email, pw_hash, fname, lname, phone_num, confirmed=False)
            user.save()
            create_user_folders(user.id)
            msg     = 'User created successfully'
            success = True
            session['email'] = email
            return redirect(url_for('confirm_email'))
    else:
        msg = 'Input error'     

    return render_template( 'accounts/register.html', form=form, msg=msg, success=success)

@app.route('/confirm_email.html', methods = ['GET', 'POST'])
def confirm_email():
    form = ConfirmEmail(request.form)
    msg = None
    success = False
    if request.method == 'GET': 

        return render_template( 'accounts/confirmemail.html', form=form, msg = msg)

    confirm_code = request.form.get('confirm_code','', type=str)
    code_hash = session['confirm_code_hash']
    
    if bc.check_password_hash(code_hash, confirm_code):
        # filter User out of database through username
        user_by_email = Users.query.filter_by(email=session['email']).first()
        user_by_email.confirmed = True
        db.session.commit()
        msg = 'Confirmed successfully'
        success = True
    else:
        msg = 'Your code is incorrect'
    return render_template( 'accounts/confirmemail.html', form=form, msg = msg, success = success)

@app.route('/modify.html', methods=['GET', 'POST'])
def modify():
    # declare the Modification Form
    form = ModifyInfoForm(request.form)
    msg = None
    success = False
    if request.method == 'GET':
        return render_template('home/modify.html', form=form, msg=msg )

    if form.validate_on_submit():
        # assign form data to variables
        fname = request.form.get('fname', '', type=str)
        lname = request.form.get('lname', '', type=str)
        username = request.form.get('username', '', type=str)
        password = request.form.get('password', '', type=str)
        new_password = request.form.get('new_password', '', type=str)
        new_email = request.form.get('new_email', '', type=str)
        new_phonenum = request.form.get('new_phonenum', '', type=int)
        # filter User out of database through username
        user = Users.query.filter_by(user=username).first()
        # filter Email
        user_by_email = Users.query.filter_by(email=new_email).first()
        if user:
            if user_by_email:
                msg = 'Error: Email exists!'
                return render_template('home/modify.html', form=form, msg=msg, success=success)
            if new_phonenum == '':
                msg = 'Error: Input phone number again!'
            if bc.check_password_hash(user.password, password):
                pw_hash = bc.generate_password_hash(new_password)
                user.update(fname, lname, pw_hash, new_email, new_phonenum)
                msg = 'Modify user info successfully.'
                success=True
                # logout and login again
                logout()
                return render_template('home/modify.html', form=form, msg=msg, success=success)
            else:
                msg = "Wrong password. Please try again."
        else:
            msg = "Unknown user"
    # return redirect(url_for('modify'))
    return render_template('home/modify.html', form=form, msg=msg, success=success)

@app.route('/passwordrequest.html', methods=['GET', 'POST'])
def request_password():
    # declare the form
    form = PasswordRequestForm(request.form)
    msg = None
    success = False
    
    if request.method == 'GET':
        return render_template('accounts/passwordrequest.html', form=form, msg=msg)
    if form.validate_on_submit():
        # get email
        receiver_email = request.form.get('email', '', type=str)
        # filter User out of database through email
        user_by_email = Users.query.filter_by(email=receiver_email).first()
        if user_by_email:
            #create new password for user
            result_pw = create_pw()
            pw_hash = bc.generate_password_hash(result_pw)
            # user_by_email.update(password=pw_hash)
            user_by_email.password = pw_hash
            db.session.commit()
            sendmail_pw(receiver_email, result_pw)
            msg = 'Please check your email'
            success=True
            return render_template('accounts/passwordrequest.html', form=form, msg=msg, success=success)
        else:
            msg = f"Email: {receiver_email} doesn't exist"
    return render_template('accounts/passwordrequest.html', form=form, msg=msg, success=success)

# Authenticate user
@app.route('/login.html', methods=['GET', 'POST'])
def login():
    
    # Declare the login form
    form = LoginForm(request.form)

    # Flask message injected into the page, in case of any errors
    msg = None

    # check if both http method is POST and form is valid on submit
    if form.validate_on_submit():

        # assign form data to variables
        username = request.form.get('username', '', type=str)
        password = request.form.get('password', '', type=str) 

        # filter User out of database through username
        user = Users.query.filter_by(user=username).first()

        if user:
            
            if bc.check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for('index'))
            else:
                msg = "Wrong password. Please try again."
        else:
            msg = "Unknown user"

    return render_template( 'accounts/login.html', form=form, msg=msg )

# App main route + generic routing
@app.route('/', defaults={'path': 'index.html'})
@app.route('/<path>')
def index(path):

    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    try:

        if not path.endswith( '.html' ):
            path += '.html'

        # Serve the file (if exists) from app/templates/FILE.html
        return render_template( 'home/' + path )
    
    except TemplateNotFound:
        return render_template('home/page-404.html'), 404
    
    except:
        return render_template('home/page-500.html'), 500

@app.route('/dock', methods=['POST'])
def dock():
    if not current_user.is_authenticated:
        return redirect(url_for('index'))

    docking_agent = DockingAgent()
    data = request.get_json(force=True)
    
    dtime = datetime.utcnow()
    compound_name = dtime.strftime("%Y-%m-%dT%H-%M-%SZ") + ".mol"
    save_compound(current_user.id, compound_name, data["ligand"])

    result = docking_agent.run(current_user.id, compound_name, dtime)
    if not result:
        return response({"status": "failed"})

    return_result = {
        "status": "success",
        "receptor": ("download/%s/receptor/" % current_user.user) + result["receptor"],
        "ligand": ("download/%s/ligand/" % current_user.user) + result["ligand"],
        "score": result["score"],
        "suggestions": result["suggestions"],
        "time": result["time"]
    }
    
    return response(return_result)
    
@app.route('/apply', methods=['POST'])
def apply_suggestion():
    if not current_user.is_authenticated:
        return redirect(url_for('index'))

    data = request.get_json(force=True)
    ligand_file = os.path.join(Config.CHEM_DIR, "dockings", str(current_user.id), 
                               os.path.basename(data["ligand"]))

    molString = DSSSystem().apply(ligand_file, data)
    return response({"ligand": molString})

@app.route('/view', methods=['POST'])
def view_ligands():
    if not current_user.is_authenticated:
        return redirect(url_for('index'))

    data = request.get_json(force=True)
    block_length = data["block_length"]
    page_number = data["page_number"]
    only_me = data["only_me"]
    asc_score = data["asc_score"]
    user_name = data["user_name"]

    if asc_score: 
        list_ligands = Ligands.query.order_by(Ligands.score.asc())    
    else:
        list_ligands = Ligands.query.order_by(Ligands.score.desc())
    result_list_ligands = list_ligands

    if user_name != "":
        # if bool(Ligands.query.filter_by(user=user_name).first()):
        #     list_ligands = list_ligands.filter_by (user=user_name)
        # else:
        #     list_ligands = []
        list_users_ligands = list_ligands.filter_by(user=user_name)
        result_list_ligands = list_users_ligands


    if only_me:
        list_ligands = list_ligands.filter_by(user=current_user.user)
        result_list_ligands = list_ligands

    total = result_list_ligands.count()
    result_list_ligands = result_list_ligands.paginate(page_number, block_length, False)
    record_items = result_list_ligands.items

    results = []
    start = (page_number - 1) * block_length
    for i, ligand in enumerate(record_items):
        ligand_name = os.path.basename(ligand.path)
        ligand = {
            "no.":  start + i + 1,
            "name": ligand_name,
            "score": ligand.score,
            "user": ligand.user,
            "download": "download/" + ligand.user + "/ligand/" + ligand_name
        }
        results.append(ligand)

    return response({"list_ligands": results, "total": total})

@app.route('/overview', methods=['POST'])
def get_overview():
    list_ligands = Ligands.query.order_by(Ligands.score.asc())  
    users = Users.query.order_by(Users.id.asc())
    list_ligands_score = Ligands.query.with_entities(Ligands.score)


    total_submission = list_ligands.count()
    total_user = users.count()
    min_value = db.session.query(func.min(Ligands.score)).scalar()
    max_value = db.session.query(func.max(Ligands.score)).scalar()
    avg_value = db.session.query(func.avg(Ligands.score)).scalar()

    return response({"total_sub": total_submission, "total_us": total_user, "min_score": min_value, "max_score":max_value, "avg_score": avg_value})

# Return sitemap
@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'sitemap.xml')

@app.route("/download/<user>/<molecule>/<file_name>", methods= ["GET"])
def download(user, molecule, file_name):
    if not current_user.is_authenticated:
        return redirect(url_for('index'))

    user = Users.query.filter_by(user=user).first()

    dir = os.getcwd()
    if molecule == "receptor":
        dir += "/" + os.path.join(Config.CHEM_DIR, "receptors")
    elif molecule == "ligand":  
        dir += "/" + os.path.join(Config.CHEM_DIR, "dockings", str(user.id))
    else:
        dir += "/"
    
    return send_from_directory(directory = dir, path = file_name, as_attachment = False)