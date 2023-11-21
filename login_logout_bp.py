"""This is the main driving module for login/logout in the Facebook imitation app 'Y'."""
from datetime import (timedelta)
from flask import request, jsonify, Blueprint
from flask_jwt_extended import create_access_token, set_access_cookies, unset_access_cookies
from models import Account

login_logout_bp = Blueprint('login_logout', __name__)

@login_logout_bp.route('/api/login', methods=['POST'])
def account_login():
    '''
    Attempts to log a user in.
    P (request contains):
        username(string): The account's username
        password(string): The password for the account
    R: 
        On success sets access cookies
        On failure aborts with 404 if either UN or PW is incorrect.

    '''
    username = request.json.get('username')
    acct = Account.query.filter_by(username=username).first()

    if acct is not None and acct.check_pw(request.json.get('password')):
        acc_token = create_access_token(identity=acct.id, expires_delta=timedelta(minutes=10))
        response = jsonify({"msg": "login is valid for accountID " + str(acct.id)})
        set_access_cookies(response, acc_token)
        return response
    #Bad info must have been given so we abort
    return "Account credentials invalid.", 404

@login_logout_bp.route('/api/logout',  methods=['POST'])
def log_out():
    '''
    Logs a user out by unsetting their access cookie.
    '''
    resp = jsonify({"msg": "Logged out"})
    unset_access_cookies(resp)
    return resp
