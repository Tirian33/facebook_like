"""This is the driving module for login and logout actions in the Facebook imitation app 'Y'."""
from datetime import (timedelta)
from flask import abort, request, jsonify, Blueprint
from flask_jwt_extended import (jwt_required, create_access_token, set_access_cookies, unset_access_cookies)
from models import (Account)

login_logout_bp = Blueprint('login_logout', __name__)


@login_logout_bp.route('/api/login', methods=['POST'])
def account_login():
    '''
    Handles logging in process.
    The sent request is expected to contain JSON with the following:
        username(string): user's username
        password(string): user's password
    R:
        Sets login tokens and redirects to /profile OR aborts due to invalid credentials (401)
    '''
    username = request.json.get('username')
    acct = Account.query.filter_by(username=username).first()
    if acct is None:
        abort(401)

    if acct.check_pw(request.json.get('password')):
        account_token = create_access_token(identity=acct.id, expires_delta=timedelta(minutes=10))
        response = jsonify({"msg": "login is valid for accountID " + str(acct.id)})
        set_access_cookies(response, account_token)
        return response
    #Bad info must have been given so we abort
    abort(401)

@login_logout_bp.route('/api/logout',  methods=['POST'])
@jwt_required()
def log_out():
    '''
    Handles logging out process.
    R:
        Unsets login tokens 
    '''
    resp = jsonify({"msg": "Logged out"})
    unset_access_cookies(resp)
    return resp