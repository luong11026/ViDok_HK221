# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""
import os
from flask    import json

from .models  import Users
from app      import app,db
from flask    import render_template
from app.config import Config

# build a Json response
def response( data ):
    return app.response_class( response=json.dumps(data),
                               status=200,
                               mimetype='application/json' )
def g_db_commit( ):

    db.session.commit( );    

def g_db_add( obj ):

    if obj:
        db.session.add ( obj )

def g_db_del( obj ):

    if obj:
        db.session.delete ( obj )

def create_user_folders(user_id):
    try:
        os.mkdir(os.path.join(Config.CHEM_DIR, "compounds", str(user_id)))
        os.mkdir(os.path.join(Config.CHEM_DIR, "dockings", str(user_id)))
    except:
        print("Error creating user folders")