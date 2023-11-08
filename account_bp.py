from flask import Flask, abort, request, jsonify, Blueprint
import jwt
from flask_jwt_extended import *
from flask_bcrypt import *
import json
from werkzeug.utils import secure_filename
from models import *

account_bp = Blueprint('account', __name__)

MAX_FILE_SIZE = 60000
FILE_SIZE_ERR_MSG = "Maximum image file size is 40 KB."

def imageHandler(request, fileAccessor, imgTarget, account):
    if len(request.files.getlist(fileAccessor)) == 1 and request.files[fileAccessor].mimetype != 'application/octet-stream':
        # Retrieve the image object
        profile_pic = request.files[fileAccessor]
        filename = secure_filename(profile_pic.filename)
        image = profile_pic.read()
        if len(image) < 60000:

            mimetype = profile_pic.mimetype
            img = Img(img=image, mimetype=mimetype, name=filename)
            
            # Store the image object
            db.session.add(img)
            db.session.commit()

            # Get the image id
            img_id = img.id
            print(img_id)

            if imgTarget == 1:
                account.profileImageID = img_id
            else:
                account.coverImageID = img_id
        else:
            #File too large
            print(len(image))
            return False
    
    #Successful end
    print(fileAccessor, imgTarget)
    print(account.profileImageID)
    print(account.coverImageID)
    return True

#Account creation at default request
@account_bp.route('/api/account', methods=['POST'])
def makeAccount():
    username = request.form.get('username')
    password = request.form.get('password')
    fName = request.form.get('fName')
    lName = request.form.get('lName')
    bio = request.form.get('bio')
    public = request.form.get('public') == 'public'

    if Account.query.filter_by(username=username).first() is not None:
        abort(400)  #Username is already in use
    acnt = Account(username, password, fName, lName, bio, public)

    if (not (imageHandler(request, 'profile-image', 1, acnt) and imageHandler(request, 'cover-image', 0, acnt))):
        abort(400, FILE_SIZE_ERR_MSG)
    
    db.session.add(acnt)
    db.session.commit()
    accountToken = create_access_token(identity=acnt.id, expires_delta=timedelta(minutes=10))
    response = jsonify({"msg": "login is valid for accountID " + str(acnt.id)})
    set_access_cookies(response, accountToken)
    
    return response

@account_bp.route('/api/account/updateBio', methods=['POST'])
@jwt_required()
def updateAccountBio():
    acnt = Account.query.filter_by(id=get_jwt_identity(), deletedAt=None).first()
    if acnt is None:
        abort(404, "Your account does not exist.")

    acnt.bio = request.form.get('new-bio')
    
    db.session.commit()
    return "Okay", 200

@account_bp.route('/api/account/updateImages', methods=['POST'])
@jwt_required()
def updateAccountImages():
    acnt = Account.query.filter_by(id=get_jwt_identity(), deletedAt=None).first()
    if acnt is None:
        abort(404, "Your account does not exist.")

    if (not (imageHandler(request, 'profile-image', 1, acnt) and imageHandler(request, 'cover-image', 0, acnt))):
        abort(400, FILE_SIZE_ERR_MSG)
    
    db.session.commit()
    return "Okay", 200

@account_bp.route('/api/account/updatePassword', methods=['POST'])
@jwt_required()
def updateAccountPassword():
    acnt = Account.query.filter_by(id=get_jwt_identity(), deletedAt=None).first()

    if acnt is None:
        abort(404, "Your account does not exist.")
    
    currPW = request.form.get('current-password')
    newPW = request.form.get('new-password')

    if currPW is None or newPW is None:
        abort(400, "Incorrect arguments.")

    if(not acnt.changePW(currPW, newPW)):
        abort(400, "Your the password you entered is incorrect.")
    db.session.commit()
    return "Okay", 200

@account_bp.route('/api/account/<int:id>')
@jwt_required()
def getAccount(id):
    acnt = Account.query.get(id)
    if not acnt:
        abort(400) #Account not found
    return jsonify(acnt.toDict())
