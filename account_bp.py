"""This is the driving module for account and image actions in the Facebook imitation app 'Y'."""
from datetime import (timedelta)
from flask import request, jsonify, Blueprint, Response
from flask_jwt_extended import (get_jwt_identity, jwt_required,
                                 create_access_token, set_access_cookies)
from werkzeug.utils import secure_filename
from models import (db, Account, Img)

account_bp = Blueprint('account', __name__)

MAX_FILE_SIZE = 60000
FILE_SIZE_ERR_MSG = "Maximum image file size is 40 KB."

def image_handler(req, f_access, img_target, account):
    '''
    Processes images in request object
    P:
        request(Request): The Request sent to the API
        f_access(string): The name of the file to be accessed.
        img_target(int): 1 if dealing with 'profile-image', 0 if dealing with 'cover-image'
        account(Account): The account to register the image with.
    R:
        True on success.
    '''
    if len(req.files.getlist(f_access)) == 1:
        #Ensure that an octet-stream isn't passed.
        if req.files[f_access].mimetype == 'application/octet-stream':
            return True

        # Retrieve the image object
        profile_pic = req.files[f_access]
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

            if img_target == 1:
                account.profile_image_id = img_id
            else:
                account.cover_image_id = img_id
        else:
            #File too large
            return False

    #Successful end
    return True

@account_bp.route('/api/images/<int:img_id>')
@jwt_required()
def get_img(img_id):
    '''
    Returns image to be rendered by the webpage.
    P:
        img_id (int): PK for image object
    R:
        Repsonse containing the image data.
    '''
    img = Img.query.filter_by(id=img_id).first()

    if not img:
        err = jsonify({'message': 'Image not found.'})
        err.status_code = 400
        return err

    return Response(img.img, mimetype=img.mimetype)

#Account creation at default request
@account_bp.route('/api/account', methods=['POST'])
def make_account():
    '''
    Creates an Account object from the sent Request.
    The form is expected to have username, password, fName, lName, bio, and public.
    It may or may not have files of the name 'profile-image' or 'cover-image'.
    
    R:
        Aborts with a 400 if either the Username is in use or the sent files are too large.
        Otherwise sets the auth cookie and returns 200.
    '''
    username = request.form.get('username')
    password = request.form.get('password')
    f_name = request.form.get('fName')
    l_name = request.form.get('lName')
    bio = request.form.get('bio')
    public = request.form.get('public') == 'public'

    if Account.query.filter_by(username=username).first() is not None:
        err = jsonify({'message': 'An account already exists with that user name.'})
        err.status_code = 400
        return err
    acnt = Account(username, password, f_name, l_name, bio, public)

    if not (image_handler(request, 'profile-image', 1, acnt)
            and image_handler(request, 'cover-image', 0, acnt)):
        err = jsonify({'message': FILE_SIZE_ERR_MSG})
        err.status_code = 400
        return err

    db.session.add(acnt)
    db.session.commit()
    account_token = create_access_token(identity=acnt.id, expires_delta=timedelta(minutes=10))
    response = jsonify({"msg": "login is valid for accountID " + str(acnt.id)})
    set_access_cookies(response, account_token)

    return response

@account_bp.route('/api/account/updateBio', methods=['POST'])
@jwt_required()
def update_account_bio():
    '''
    Updates the logged in account's bio.
    Request is expected to have a form fields 'new-bio'.
    '''
    acnt = Account.query.filter_by(id=get_jwt_identity(), deleted_at=None).first()
    if acnt is None:
        return "Your account does not exist.", 404

    acnt.bio = request.form.get('new-bio')

    db.session.commit()
    return "Okay", 200

@account_bp.route('/api/account/updateImages', methods=['POST'])
@jwt_required()
def update_account_images():
    '''
    Updates associated cover_image_id and profile_image_id of caller's account.
    Aborts with 404 if account has since been deleted and aborts with 400 if file is too large.
    '''
    acnt = Account.query.filter_by(id=get_jwt_identity(), deleted_at=None).first()
    if acnt is None:
        return "Your account does not exist.", 404

    if not (image_handler(request, 'profile-image', 1, acnt)
            and image_handler(request, 'cover-image', 0, acnt)):
        err = jsonify({'message': FILE_SIZE_ERR_MSG})
        err.status_code = 400
        return err

    db.session.commit()
    return "Okay", 200

@account_bp.route('/api/account/updatePassword', methods=['POST'])
@jwt_required()
def update_account_password():
    '''
    Updates the currently logged in account's password.
    Expects a form with fields current-password and new-password.
    Aborts with 400 if a field is missing or if the current-password is not the current password.
    '''
    acnt = Account.query.filter_by(id=get_jwt_identity(), deleted_at=None).first()

    if acnt is None:
        return "Your account does not exist.", 404

    cur_pw = request.form.get('current-password')
    new_pw = request.form.get('new-password')

    if cur_pw is None or new_pw is None:
        err = jsonify({'message': "Incorrect arguments."})
        err.status_code = 400
        return err

    if not acnt.change_pw(cur_pw, new_pw):
        err = jsonify({'message': "The password you entered is incorrect."})
        err.status_code = 400
        return err
    db.session.commit()
    return "Okay", 200
