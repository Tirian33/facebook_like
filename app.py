import os
from flask import Flask, abort, request, jsonify, g, render_template, Response, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import PendingRollbackError, OperationalError, TimeoutError
from sqlalchemy import distinct
from flask_marshmallow import Marshmallow
from datetime import (datetime, timedelta, timezone)
import jwt
from flask_jwt_extended import *
from flask_bcrypt import *
import json
from werkzeug.utils import secure_filename

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

#Both account IDs are assumed to not be None
def canMakeContent(targetAccID, posterID):
   
    if int(targetAccID) == posterID:
        return 1
    

    targetAcc = Account.query.filter_by(id = targetAccID).first()

    if targetAcc is not None:
        if not targetAcc.isPublic:
            return 2
        
        rel = Relationship.query.filter_by(firstAccountID = targetAcc.id, secondAccountID = posterID, deletedAt = None, isFriendRelation = True).first()
        if rel is not None:
            return 1
    #Not the same account, and Poster is not friend with target account.
    return 3



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
    public = request.json.get('public') == 'public'
    if Account.query.filter_by(username=username).first() is not None:
        abort(400)  #Username is already in use
    acnt = Account(username, password, fName, lName, public)
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
        abort(404)
    
    if(acct.checkPW(request.json.get('password'))):
        accountToken = create_access_token(identity=acct.id, expires_delta=timedelta(minutes=10))
        response = jsonify({"msg": "login is valid for accountID " + str(acct.id)})
        set_access_cookies(response, accountToken)
        return response    
    #Bad info must have been given so we abort
    abort(401)

#Friend request sending
@app.route('/api/makeFriend', methods=['POST'])
@jwt_required()
def sendFriendRequest():
    if request.json.get('friendCode') is None:
        abort(400, "Need Friend Code of requested friend.")
    elif len(request.json.get('friendCode')) != 8:
        abort(400, "Friend Code is 8 characters.")

    targetAccount = Account.query.filter_by(friendCode=request.json.get('friendCode')).first()
   
    if targetAccount is None:
        abort(400, "Friend not found.")
    
    pendingInverse = Relationship.query.filter_by(secondAccountID = get_jwt_identity(), firstAccountID = targetAccount.id, deletedAt = None).first()
    
    # Other person sent a friend request in the past, lets accept
    if pendingInverse is not None:
        if pendingInverse.isFriendRelation: 
            pendingInverse.confirmedRelation = True
            db.session.add(pendingInverse.makeInverse())
            db.session.commit()
            return "OK", 200

    # Request was sent in the past
    if Relationship.query.filter_by(firstAccountID = get_jwt_identity(), secondAccountID = targetAccount.id).first() is not None:
        abort(400, "Request already sent")

    # Lets make the request
    elif pendingInverse is None:
        newRelationship = Relationship(get_jwt_identity(), targetAccount.id)
        db.session.add(newRelationship)
        db.session.commit()
    
    return "OK", 200

@app.route('/api/declineFriend', methods=['POST'])
@jwt_required()
def declineFriendRequest():
    if request.json.get('friendCode') is None:
        abort(400, "Need Friend Code of declining friend.")
    elif len(request.json.get('friendCode')) != 8:
        abort(400, "Friend Code is 8 characters.")

    targetAccount = Account.query.filter_by(friendCode=request.json.get('friendCode')).first()
   
    if targetAccount is None:
        abort(400, "Friend not found.")
    
    targetRelationship = Relationship.query.filter_by(secondAccountID = get_jwt_identity(), firstAccountID = targetAccount.id, deletedAt = None).first()
    
    if targetRelationship is None:
        abort(400, "User has no pending request from specified friendCode.")
    
    targetRelationship.deletedAt = datetime.now()
    db.session.commit()
    
    return "OK", 200

#Post related
@app.route('/api/post', methods=['POST'])
@jwt_required()
def makePost():
    if ((request.form.get('textContent') is None and request.form.get('sharedPostId')is None) or request.form.get('postedOnID') is None):
        abort(400, "Invalid request recieved.")

    targetAccount = Account.query.filter_by(id = request.form.get('postedOnID'), deletedAt = None).first()
    if (targetAccount is None):
        abort(400, "Can't find that person to post on.")
    
    permission = canMakeContent(request.form.get('postedOnID'), get_jwt_identity())
    
    if permission == 2:
        abort(400, "You do not have permission to post right now.")
    elif permission == 3:
        abort(400, "You are not friends. You cannot post")
    
    newPost = Post(get_jwt_identity(), request.form.get('textContent'), request.form.get('postedOnID'), request.form.get('sharedPostId'))
   
    # If there is only one image attachment...
    if len(request.files.getlist('pic')) == 1 and request.files['pic'].mimetype != 'application/octet-stream':
        # Retrieve the image object
        pic = request.files['pic']
        filename = secure_filename(pic.filename)
        mimetype = pic.mimetype
        img = Img(img=pic.read(), mimetype=mimetype, name=filename)
        
        # Store the image object
        db.session.add(img)
        db.session.commit()

        # Get the image id
        img_id = img.id

        newPost.associatedImageID = img_id

    # If there are multiple image attachments, error out.
    elif len(request.files.getlist('pic')) > 1:
        abort(400, "Only one image may be uploaded at a time.")
    
    db.session.add(newPost)
    db.session.commit()
    
    return "OK", 200 #returning "OK"

@app.route('/api/post/<int:postID>', methods=['DELETE'])
@jwt_required()
def deletePost(postID):
    requesterID = get_jwt_identity()
    
    targetPost = Post.query.filter_by(id=postID).first()
    if targetPost is None:
        abort(400) #Request made was bad
    
    if (targetPost.postedOnID == requesterID or targetPost.posterID == requesterID):
        #DEL
        softDeleteObjects(targetPost.replies)
        softDeleteObjects(targetPost.reactions)
        targetPost.deletedAt = datetime.now()
        db.session.commit()
        return "Done", 200
    
    abort(401) #Request was made by someone without perms

#Reply related
@app.route('/api/reply', methods=['POST'])
@jwt_required()
def makeReply():
    if (request.json.get('textContent') is None or request.json.get('respTo') is None):
        abort(400, "Invalid request recieved.")

    targetPost = Post.query.fitler_by(id = request.json.get('respTo'), deletedAt = None).first()
    if targetPost is None:
        abort(400, "The post you are trying to respond to has been deleted.")

    targetAccount = Account.query.filter_by(id = targetPost.postedOnID, deletedAt = None).first()
    if targetAccount is None:
        abort(400, "The post you are trying to respond to has been deleted.")
    
    permission = canMakeContent(request.json.get('respTo'), get_jwt_identity())
    if permission == 2:
        abort(400, "You do not have permission to reply right now.")
    elif permission == 3:
        abort(400, "You are not friends. You cannot reply.")
    

    newReply = Reply(request.json.get('respTo'), get_jwt_identity(), request.json.get('textContent'))
    db.session.add(newReply)
    db.session.commit()
    return "OK", 200 #returning "OK"

@app.route('/api/reply/<int:replyID>', methods=['DELETE'])
@jwt_required()
def deleteReply(replyID):
    requesterID = get_jwt_identity()
    
    target = Reply.query.filter_by(id=replyID, deletedAt=None).first()
    if target is None:
        abort(400) #Request made was bad
    
    containingPost = Post.query.filter_by(id=target.respondingTo).first()
    
    if (containingPost.postedOnID == requesterID or target.posterID == requesterID):
        target.deletedAt = datetime.now()
        db.session.commit()
        return "Done", 200
    
    abort(401) #Request was made by someone without perms

#Reaction related
#Input {reactionType:int, respTo:int} respTo - FK PostID
@app.route('/api/reaction', methods=['POST'])
@jwt_required()
def makeReaction():
    if (request.json.get('reactionType') is None or request.json.get('respTo') is None):
        abort(400, "Invalid request recieved.")

    targetPost = Post.query.fitler_by(id = request.json.get('respTo'), deletedAt = None).first()
    if targetPost is None:
        abort(400, "The post you are trying to react to has been deleted.")
    
    permission = canMakeContent(request.json.get('respTo'), get_jwt_identity())
    if permission == 2:
        abort(400, "You do not have permission to react right now.")
    elif permission == 3:
        abort(400, "You are not friends. You cannot react.")
    

    newReply = Reply(request.json.get('respTo'), get_jwt_identity(), request.json.get('textContent'))
    db.session.add(newReply)
    db.session.commit()
    return "OK", 200 #returning "OK"

@app.route('/api/reaction/<int:reactionID>', methods=['DELETE'])
@jwt_required()
def deleteReaction(reactionID):
    requesterID = get_jwt_identity()
    
    target = Reaction.query.filter_by(id=reactionID).first()
    if target is None:
        abort(400) #Request made was bad
    
    containingPost = Post.query.filter_by(id=target.respondingTo).first()

    if (containingPost.postedOnID == requesterID or target.posterID == requesterID):
        target.deletedAt = datetime.now()
        db.session.commit()
        return "Done", 200
    
    abort(401) #Request was made by someone without perms

#Token related
@app.route('/api/token')
def getToken():
    token = g.account.genToken(600)
    return jsonify({'token': token.decode('ascii'), 'duration': 600})


# Image upload
@app.route('/api/upload', methods=['POST'])
def uploadImage():
    pic = request.files['pic']

    if not pic:
        return 'No image uploaded', 400
    
    filename = secure_filename(pic.filename)
    mimetype = pic.mimetype

    img = Img(img=pic.read(), mimetype=mimetype, name=filename)
    db.session.add(img)
    db.session.commit()

    return "Image successfully uploaded" , 200

# Display the image
@app.route('/api/images/<int:id>')
def get_img(id):
    img = Img.query.filter_by(id=id).first()
    
    if not img:
        return "Image not found", 400
    
    return Response(img.img, mimetype=img.mimetype)

#Webpages
@app.route('/')
def indexPage():
    return render_template('index.html')

@app.route('/login')
def loginPage():
    return render_template('login.html')

@app.route('/upload')
def uploadPage():
    return render_template('upload.html')

@app.route('/register')
def registerPage():
    return render_template('register.html')

@app.route('/home')
@jwt_required()
def homePage():
    userAccID = get_jwt_identity()
    acc = Account.query.filter_by(id=userAccID).first()

    #Gets all the accounts that are friends with the user.
    allFriends = db.session.query(Account).join( Relationship, (Relationship.firstAccountID == acc.id) & (Relationship.secondAccountID == Account.id) & (Relationship.confirmedRelation == True) & (Relationship.isFriendRelation == True)).all()

    friends = []
    postable = {}
    postable.update(acc.toPostData())

    for friend in allFriends:
        if friend.deletedAt is None:
            friends.append(friend.toDict())
        postable.update(friend.toPostData())

    timeline = Post.query.filter_by(postedOnID=userAccID, deletedAt=None).order_by(Post.id.desc()).all()

    print(postable)
    return render_template('home.html', account = acc.toDict(), friends = friends, timeline = timeline, postable=postable, pageOwner=userAccID)

@app.route('/timeline/<int:accID>')
@jwt_required()
def timeline(accID):
    if(accID == get_jwt_identity()):
       return redirect(url_for('homePage'))

    permission = canMakeContent(accID, get_jwt_identity())
    if permission == 2:
        abort(401, description="Profile is private.")
    elif permission == 3:
        abort(401, description="You are not friends.")
    #Has permission to View
    timeline = Post.query.filter_by(postedOnID=accID, deletedAt=None).all()

    myAcc = Account.query.filter_by(id=get_jwt_identity()).first()
    targetAcc = Account.query.filter_by(id=accID).first()

    #Gets all the accounts that are friends with the user.
    allFriends = db.session.query(Account).join( Relationship, (Relationship.firstAccountID == accID) & (Relationship.secondAccountID == Account.id) & (Relationship.confirmedRelation == True) & (Relationship.isFriendRelation == True)).all()

    friends = []
    postable = {}
    postable.update(targetAcc.toPostData())

    for friend in allFriends:
        if friend.deletedAt is None:
            friends.append(friend.toDict())
        postable.update(friend.toPostData())

    timeline = Post.query.filter_by(postedOnID=accID, deletedAt=None).order_by(Post.id.desc()).all()

    print(postable)
    return render_template('home.html', account = myAcc.toDict(), friends = friends, timeline = timeline, postable=postable, pageOwner=accID)


@app.route('/friends')
@jwt_required()
def friendPage():
    userAccID = get_jwt_identity()
    acc = Account.query.filter_by(id=userAccID).first()

    friends = db.session.query(Account).join( Relationship, (Relationship.firstAccountID == acc.id) & (Relationship.secondAccountID == Account.id) & (Relationship.confirmedRelation == True) & (Relationship.isFriendRelation == True)).all()
    pending = db.session.query(Account).join( Relationship, (Relationship.firstAccountID == Account.id) & (Relationship.secondAccountID == acc.id) & (Relationship.confirmedRelation == False) & (Relationship.isFriendRelation == True)).all()
    return render_template('friends.html', account = acc.toDict(), friends = friends, pending = pending)

@app.route('/signup')
def signUpPage():
    return render_template('signup.html')


#Teardown (don't mess with this)
@app.teardown_appcontext
def killSession(exception=None):
    db.session.remove()

#defining the app as itself (don't mess with this)

if __name__ == '__main__':
    app.run(host="localhost", port=5000, debug=True)