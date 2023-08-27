import os
from flask import Flask, abort, request, jsonify, g, render_template
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
jwtInfo = app.config['SECRET_KEY']
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

#Account related
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
    return jsonify(acnt)

@app.route('/api/account/<int:id>')
def getAccount(id):
    acnt = Account.query.get(id)
    if not acnt:
        abort(404) #Account not found
    return jsonify(acnt)

#Token related
@app.route('/api/token')
@auth.login_required
def getToken():
    token = g.account.genToken(600)
    return jsonify({'token': token.decode('ascii'), 'duration': 600})



#Webpages
@app.route('/')
def indexPage():
    return render_template('index.html')

#Teardown (don't mess with this)
@app.teardown_appcontext
def killSession(exception=None):
    db.session.remove()

#defining the app as itself (don't mess with this)

if __name__ == '__main__':
    app.run(host="localhost", port=5000, debug=True)