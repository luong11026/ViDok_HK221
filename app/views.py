# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

# Python modules
import os, logging 
import json
from datetime import datetime

# Flask modules``
from flask               import render_template, request, url_for, redirect, send_from_directory, jsonify, Response
from flask_login         import login_user, logout_user, current_user, login_required
from werkzeug.exceptions import HTTPException, NotFound, abort
from jinja2              import TemplateNotFound

# App modules
from app        import app, lm, db, bc
from app.models import Users
from app.forms  import LoginForm, RegisterForm
from app.chem_utils import DockingAgent, save_compound
from app.dss_system import DSSSystem
from app.util   import create_user_folders, response
from app.config import Config

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

        return render_template( 'accounts/register.html', form=form, msg=msg )

    # check if both http method is POST and form is valid on submit
    if form.validate_on_submit():

        # assign form data to variables
        username = request.form.get('username', '', type=str)
        password = request.form.get('password', '', type=str) 
        email    = request.form.get('email'   , '', type=str) 

        # filter User out of database through username
        user = Users.query.filter_by(user=username).first()

        # filter User out of database through username
        user_by_email = Users.query.filter_by(email=email).first()

        if user or user_by_email:
            msg = 'Error: User exists!'
        
        else:         

            pw_hash = bc.generate_password_hash(password)

            user = Users(username, email, pw_hash)
            user.save()

            create_user_folders(user.id)

            msg     = 'User created successfully.'
            success = True

    else:
        msg = 'Input error'     

    return render_template( 'accounts/register.html', form=form, msg=msg, success=success )

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
    compound_name = dtime.strftime("%Y-%m-%dT%H:%M:%SZ") + ".mol"
    save_compound(current_user.id, compound_name, data["ligand"])

    result = docking_agent.run(current_user.id, compound_name, dtime)
    if not result:
        return response({"status": "failed"})

    return_result = {
        "status": "success",
        "receptor": "download/receptor/" + result["receptor"],
        "ligand": "download/ligand/" + result["ligand"],
        "score": result["score"],
        "suggestions": result["suggestions"]
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

# Return sitemap
@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'sitemap.xml')

@app.route("/download/<molecule>/<file_name>", methods= ["GET"])
def download(molecule, file_name):
    dir = os.getcwd()
    if molecule == "receptor":
        dir += "/" + os.path.join(Config.CHEM_DIR, "receptors")
    elif molecule == "ligand":  
        dir += "/" + os.path.join(Config.CHEM_DIR, "dockings", str(current_user.id))
    else:
        dir += "/"
    
    return send_from_directory(directory = dir, path = file_name, as_attachment = False)