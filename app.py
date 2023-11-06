from flask import Flask, abort, request, jsonify, Response, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import PendingRollbackError, OperationalError
from datetime import (datetime, timedelta, timezone)
import jwt
from flask_jwt_extended import *
from flask_bcrypt import Bcrypt
import json
from werkzeug.utils import secure_filename

# Initializing
app = Flask(__name__)
app.config.from_pyfile("settings.py")
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
app.app_context().push() 

#registering Blueprints
from account_bp import account_bp
app.register_blueprint(account_bp)

from pages_bp import pages_bp
app.register_blueprint(pages_bp)

from relationship_bp import relationship_bp
app.register_blueprint(relationship_bp)

from pst_rep_rea_bp import pst_rep_rea_bp
app.register_blueprint(pst_rep_rea_bp)

from models import *

#ERROR HANDLING
@jwt.unauthorized_loader
def handleMissingToken(error):
    print(error)
    if 'Missing cookie "access_token_cookie"' in str(error):
        return redirect(url_for('pages.loginPage', redirectReason = "noTkn"))  #Was not signed in
    
    return redirect(url_for('pages.loginPage', redirectReason = "tknExp"))  #Token expired

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
        refreshtime = datetime.timestamp(datetime.now(timezone.utc) + timedelta(minutes=10))
        if refreshtime > expireTime:
            newToken = create_access_token(identity=get_jwt_identity(), expires_delta=timedelta(minutes=10))
            set_access_cookies(response, newToken)
        return response
    #If user manages to get here with a corrupted token throws RT error so just return the corrupted token.
    except (RuntimeError, KeyError):
        return response

@app.route('/api/login', methods=['POST'])
def accountLogin():
    username = request.json.get('username')
    acct = Account.query.filter_by(username=username).first()
    if acct is None:
        abort(404)
    
    if(acct.checkPW(request.json.get('password'))):
        accountToken = create_access_token(identity=acct.id, expires_delta=timedelta(minutes=10))
        response = jsonify({"msg": "login is valid for accountID " + str(acct.id)})
        set_access_cookies(response, accountToken)
        return response    
    #Bad info must have been given so we abort
    abort(401)

@app.route('/api/logout',  methods=['POST'])
def logOut():
    resp = jsonify({"msg": "Logged out"})
    unset_access_cookies(resp)
    return resp

#Token related
# @app.route('/api/token')
# def getToken():
#     token = g.account.genToken(600)
#     return jsonify({'token': token.decode('ascii'), 'duration': 600})


# Display the image
@app.route('/api/images/<int:id>')
def get_img(id):
    img = Img.query.filter_by(id=id).first()
    
    if not img:
        return "Image not found", 400
    
    return Response(img.img, mimetype=img.mimetype)


#Teardown (don't mess with this)
@app.teardown_appcontext
def killSession(exception=None):
    db.session.remove()

#defining the app as itself (don't mess with this)

if __name__ == '__main__':
    app.run(host="localhost", port=5000, debug=True)