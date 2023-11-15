"""This is the main driving module for the Facebook imitation app 'Y'."""
from datetime import (datetime, timedelta, timezone)
import jwt
from flask import Flask, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import PendingRollbackError, OperationalError
from flask_jwt_extended import (JWTManager, get_jwt, get_jwt_identity, create_access_token, set_access_cookies)
from flask_bcrypt import Bcrypt

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

from login_logout_bp import login_logout_bp
app.register_blueprint(login_logout_bp)

#ERROR HANDLING
@jwt.unauthorized_loader
def handle_missing_token(error):
    '''
    Handles access to pages without a access_token
    P:
        error: error object
    R:
        Redirects to the login_page
    '''
    return redirect(url_for('pages.login_page', redirect_reason = "noTkn"))  #Was not signed in

@jwt.expired_token_loader
def handle_expired_token(jwt_info, token):
    '''
    Handles access to pages with an expired access_token
    P:
        error: error object
    R:
        Redirects to the login_page
    '''
    return redirect(url_for('pages.login_page', redirect_reason = "tknExp"))  #Token expired
def handle_missing_token(error):
    '''
    Handles access to pages without a access_token
    P:
        error: error object
    R:
        Redirects to the login_page
    '''
    return redirect(url_for('pages.login_page', redirect_reason = "noTkn"))  #Was not signed in

@jwt.expired_token_loader
def handle_expired_token(error, second):
    '''
    Handles access to pages with an expired access_token
    P:
        error: error object
    R:
        Redirects to the login_page
    '''
    print(error, second)
    return redirect(url_for('pages.login_page', redirect_reason = "tknExp"))  #Token expired

@app.errorhandler(500)
def handle500(error):
    '''
    Sometimes the session will close when it is in use. 
        This is usually an error due to losing connection to the DB.
    P:
        error: error object
    R:
        Returns 500 error and forces caller to retry.
    '''
    #most likely we lost DB connection
    if isinstance(error, (OperationalError, PendingRollbackError)):
        db.session.rollback()
        db.session.close()
        db.session.begin()
        return jsonify({'error': 'Lost connection to DB. Retry request.', 'retry':True}), 500
    raise error

@app.after_request
def refresh_jwt(response):
    '''
    Refreshes the jwt token after user performs any API request while having a valid jwt token.
    P: 
        response: The response that is about to be returned to the user.
    R: 
        The expected response + cookie reset data
    '''
    try:
        expire_time = get_jwt()["exp"]
        refresh_time = datetime.timestamp(datetime.now(timezone.utc) + timedelta(minutes=10))
        if refresh_time > expire_time:
            new_token = create_access_token(identity = get_jwt_identity(),
                                           expires_delta = timedelta(minutes=10))
            set_access_cookies(response, new_token)
        return response
    #If user got here with a corrupted token, throws RT error so just return the corrupted token.
    except (RuntimeError, KeyError):
        return response

#Teardown (don't mess with this)
@app.teardown_appcontext
def kill_session(exception=None):
    '''
    Terminates the db session on application close.
    '''
    db.session.remove()

#defining the app as itself (don't mess with this)

if __name__ == '__main__':
    app.run(host="localhost", port=5000, debug=True)
