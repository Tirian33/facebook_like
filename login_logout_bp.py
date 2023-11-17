from flask import abort, request, jsonify, Blueprint
from datetime import (timedelta)
from flask_jwt_extended import *
from models import Account

login_logout_bp = Blueprint('login_logout', __name__)

@login_logout_bp.route('/api/login', methods=['POST'])
def accountLogin():
    username = request.json.get('username')
    acct = Account.query.filter_by(username=username).first()
    if acct is None:
        abort(404)
    
    if(acct.check_pw(request.json.get('password'))):
        acc_token = create_access_token(identity=acct.id, expires_delta=timedelta(minutes=10))
        response = jsonify({"msg": "login is valid for accountID " + str(acct.id)})
        set_access_cookies(response, acc_token)
        return response    
    #Bad info must have been given so we abort
    abort(401)

@login_logout_bp.route('/api/logout',  methods=['POST'])
def logOut():
    resp = jsonify({"msg": "Logged out"})
    unset_access_cookies(resp)
    return resp