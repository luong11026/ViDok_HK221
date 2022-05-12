# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from app         import db
from flask_login import UserMixin

class Users(db.Model, UserMixin):

    __tablename__ = 'Users'

    id       = db.Column(db.Integer,     primary_key=True)
    user     = db.Column(db.String(64),  unique = True, nullable=False)
    email    = db.Column(db.String(120), unique = True, nullable=False)
    password = db.Column(db.String(500), nullable=False)
    ligands  = db.relationship('Ligands', backref='Users', lazy=True)

    def __init__(self, user, email, password):
        self.user       = user
        self.password   = password
        self.email      = email

    def __repr__(self):
        return str(self.id) + ' - ' + str(self.user)

    def save(self):

        # inject self into db session    
        db.session.add ( self )

        # commit change and save the object
        db.session.commit( )

        return self 

class Ligands(db.Model):

    __tablename__ = 'Ligands'

    id       = db.Column(db.Integer,     primary_key=True)
    time     = db.Column(db.DateTime, nullable=False)
    path    = db.Column(db.String(500), unique = True, nullable=False)
    score   = db.Column(db.Float)
    user    = db.Column(db.String(64), db.ForeignKey('Users.user'), nullable=False)

    def __init__(self, time, path, score, user):
        self.time       = time
        self.path       = path
        self.score      = score
        self.user       = user

    def __repr__(self):
        return str(self.user) + ' - ' + str(self.time)

    def save(self):

        # inject self into db session    
        db.session.add ( self )

        # commit change and save the object
        db.session.commit( )

        return self 