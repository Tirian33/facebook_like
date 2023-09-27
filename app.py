import os
from flask import Flask, abort, request, jsonify, g, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import PendingRollbackError, OperationalError, TimeoutError
from sqlalchemy import distinct
from flask_marshmallow import Marshmallow
from datetime import (datetime, timedelta, timezone)
import jwt
from flask_jwt_extended import *
from flask_bcrypt import *
import json

# Initializing
app = Flask(__name__)
app.config.from_pyfile("settings.py")
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
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


@app.after_request
def refreshJWT(response):
    try: 
        expireTime = get_jwt()["exp"]
        refreshtime = datetime.timestamp(datetime.now(timezone.utc) + timedelta(minutes=5))
        if refreshtime > expireTime:
            newToken = create_access_token(identity=get_jwt_identity(), expires_delta=timedelta(minutes=5))
            set_access_cookies(response, newToken)
        return response
    #If user manages to get here with a corrupted token throws RT error so just return the corrupted token.
    except (RuntimeError, KeyError):
        return response


#API routes

#Account related

#Account creation at default request
@app.route('/api/account', methods=['POST'])
def makeAccount():
    username = request.json.get('username')
    password = request.json.get('password')
    fName = request.json.get('fName')
    lName = request.json.get('lName')
    if Account.query.filter_by(username=username).first() is not None:
        abort(400)  #Username is already in use
    acnt = Account(username, password, fName, lName)
    db.session.add(acnt)
    db.session.commit()
    accountToken = create_access_token(identity=acnt.id, expires_delta=timedelta(minutes=10))
    response = jsonify({"msg": "login is valid for accountID " + str(acnt.id)})
    set_access_cookies(response, accountToken)
    return response

@app.route('/api/account/<int:id>')
@jwt_required()
def getAccount(id):
    acnt = Account.query.get(id)
    if not acnt:
        abort(400) #Account not found
    return jsonify(acnt)

@app.route('/api/login', methods=['POST'])
def accountLogin():
    username = request.json.get('username')
    acct = Account.query.filter_by(username=username).first()
    if acct is None:
        abort(500)
    
    if(acct.checkPW(request.json.get('password'))):
        accountToken = create_access_token(identity=acct.id, expires_delta=timedelta(minutes=10))
        response = jsonify({"msg": "login is valid for accountID " + str(acct.id)})
        set_access_cookies(response, accountToken)
        return response    
    #Bad info must have been given so we abort
    abort(500)

#Post related
@app.route('/api/post', methods=['POST'])
@jwt_required
def makePost():
    if request.json.get('testContent') is None and request.json.get('sharedPostId')is None:
        abort(400) #need content when not just reposting

    newPost = Post(get_jwt_identity, request.json.get('textContent'), request.json.get('sharedPostId'))
    db.session.add(newPost)
    db.session.commit()
    return 200 #returning "OK"
    


#Token related
@app.route('/api/token')
def getToken():
    token = g.account.genToken(600)
    return jsonify({'token': token.decode('ascii'), 'duration': 600})


#Webpages
@app.route('/')
def indexPage():
    return render_template('index.html')

@app.route('/login')
def loginPage():
    return render_template('login.html')

@app.route('/home')
@jwt_required()
def homePage():
    userAccID = get_jwt_identity()
    acc = Account.query.filter_by(id=userAccID).first()
    return render_template('home.html', account = acc.toDict())


#Teardown (don't mess with this)
@app.teardown_appcontext
def killSession(exception=None):
    db.session.remove()

#defining the app as itself (don't mess with this)

if __name__ == '__main__':
    app.run(host="localhost", port=5000, debug=True)