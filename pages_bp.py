from flask import abort, request, render_template, redirect, url_for, Blueprint
import jwt
from flask_jwt_extended import *
import json
from models import *
from pst_rep_rea_bp import canMakeContent

pages_bp = Blueprint('pages', __name__)


@pages_bp.route('/')
def indexPage():
    return redirect(url_for('loginPage'))

@pages_bp.route('/login')
def loginPage():
    redirected = request.args.get('redirectReason')
    return render_template('login.html', redirectReason=redirected)

@pages_bp.route('/upload')
def uploadPage():
    return render_template('upload.html')

@pages_bp.route('/register')
def registerPage():
    return render_template('register.html')

@pages_bp.route('/profile')
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

    likedPosts = []
    likedReactions = []
    for post in timeline:
        for reaction in post.reactions:
            if reaction.posterID == get_jwt_identity():
                if reaction.deletedAt == None:
                    likedPosts.append(post.id)
                    likedReactions.append(reaction.id)

    userReactions = {likedPosts[i]: likedReactions[i] for i in range(len(likedPosts))}
    
    posts = []
    numLikes = []
    for post in timeline:
        posts.append(post.id)
        num_likes = 0
        for reaction in post.reactions:
            if reaction.deletedAt == None:
                    num_likes = num_likes+1
        numLikes.append(num_likes)

    numLikes = {posts[i]: numLikes[i] for i in range(len(posts))}
   
    return render_template('profile.html', account = acc.toDict(), friends = friends, timeline = timeline, postable=postable, pageOwner=userAccID, user = userAccID, likedPosts = likedPosts, userReactions=userReactions, numLikes=numLikes)

@pages_bp.route('/timeline/<int:accID>')
@jwt_required()
def timeline(accID):
    if(accID == get_jwt_identity()):
       return redirect(url_for('homePage'))

    permission = canMakeContent(accID, get_jwt_identity())
    if permission == 2:
        abort(401, description="Profile is private.")
    elif permission == 3:
        abort(401, description="You are not friends.")

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
    processedTL = []
    for pst in timeline:
        processedTL.append(pst.process(myAcc.id))

    likedPosts = []
    likedReactions = []
    for post in timeline:
        for reaction in post.reactions:
            if reaction.posterID == get_jwt_identity():
                if reaction.deletedAt == None:
                    likedPosts.append(post.id)
                    likedReactions.append(reaction.id)

    userReactions = {likedPosts[i]: likedReactions[i] for i in range(len(likedPosts))}\
    
    posts = []
    numLikes = []
    for post in timeline:
        posts.append(post.id)
        num_likes = 0
        for reaction in post.reactions:
            if reaction.deletedAt == None:
                    num_likes = num_likes+1
        numLikes.append(num_likes)

    numLikes = {posts[i]: numLikes[i] for i in range(len(posts))}

    return render_template('profile.html', account = targetAcc.toDict(), friends = friends, timeline = processedTL, postable=postable, pageOwner=accID, user=get_jwt_identity(), userReactions=userReactions, likedPosts=likedPosts, numLikes=numLikes)


@pages_bp.route('/friends')
@jwt_required()
def friendPage():
    userAccID = get_jwt_identity()
    acc = Account.query.filter_by(id=userAccID).first()

    friends = db.session.query(Account).join( Relationship, (Relationship.firstAccountID == acc.id) & (Relationship.secondAccountID == Account.id) & (Relationship.confirmedRelation == True) & (Relationship.isFriendRelation == True) & (Relationship.deletedAt == None)).all()
    pending = db.session.query(Account).join( Relationship, (Relationship.firstAccountID == Account.id) & (Relationship.secondAccountID == acc.id) & (Relationship.confirmedRelation == False) & (Relationship.isFriendRelation == True) & (Relationship.deletedAt == None)).all()
    friendsProcessed = []
    pendingProcessed = []

    for f in friends:
        friendsProcessed.append(f.toDict())
    
    for p in pending:
        pendingProcessed.append(p.toDict())
    
    return render_template('friends.html', account = acc.toDict(), friends = friendsProcessed, pending = pendingProcessed)

@pages_bp.route('/signup')
def signUpPage():
    return render_template('signup.html')

@pages_bp.route('/settings')
@jwt_required()
def settingsPage():
    userAccID = get_jwt_identity()
    acc = Account.query.filter_by(id=userAccID).first()
    return render_template('settings.html', account = acc.toDict())