import os
from flask import Flask, abort, request, jsonify, g
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import PendingRollbackError, OperationalError, TimeoutError
from sqlalchemy import distinct
from flask_marshmallow import Marshmallow
import jwt
from flask_httpauth import HTTPBasicAuth
import bcrypt
import json

# Initializing
app = Flask(__name__)
app.config.from_pyfile("settings.py")
db = SQLAlchemy(app)
auth = HTTPBasicAuth()
jwtInfo = app.config(['SECRET_KEY'])
app.app_context().push() 

from models import *

#Constasnts go here

#assisting methods go here
def softDeleteObjects(listing) -> None:
    for item in listing:
        item.deletedAt = datetime.now()
    db.session.commit()


#ERROR HANDLING
@app.errorhandler(500)
def handle500(error):
    #most likely we lost DB connection
    if isinstance(error, OperationalError) or isinstance(error, PendingRollbackError):
        db.session.rollback()
        db.session.close()
        db.session.begin()
        return jsonify({'error': 'Lost connection to DB. Retry request.', 'retry':True}), 500
    else:
        raise error
    
#Picky about using _ instead of camelCase
@auth.verify_password
def verify_password(unOrToken, password):
    acnt = Account.checkToken(unOrToken)
    #check to see if an Account was found
    if not acnt:
        acnt = Account.query.filter_by(username=unOrToken).first()
        #check to see if an Account was found
        if not acnt or not acnt.checkPW(password):
            return False
    g.account = acnt
    return True

#API routes
#Account creation at default request
@app.route('/api/account', methods=['POST'])
def makeAccount():
    username = request.json.get('username')
    password = request.json.get('password')
    if username is None or password is None:
        abort(400)  #Missing UN/PW thus can't create account
    if Account.query.filter_by(username=username).first() is not None:
        abort(400)  #Username is already in use
    acnt = Account(username, password)
    db.session.add(acnt)
    db.session.commit()
    return 404 #Temporary It should direct the user to the logedin homepage signed in with a token