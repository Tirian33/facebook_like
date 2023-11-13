from flask import abort, request, Blueprint
import jwt
from flask_jwt_extended import *
import json
from werkzeug.utils import secure_filename
from models import *

pst_rep_rea_bp = Blueprint('pst_rep_rea', __name__)

#canMakeContent
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

def softDeleteObjects(listing) -> None:
    for item in listing:
        item.deletedAt = datetime.now()
    db.session.commit()

@pst_rep_rea_bp.route('/api/post', methods=['POST'])
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
        image = pic.read()
        if len(image) < 60000:

            mimetype = pic.mimetype
            img = Img(img=image, mimetype=mimetype, name=filename)
            
            # Store the image object
            db.session.add(img)
            db.session.commit()

            # Get the image id
            img_id = img.id

            newPost.associatedImageID = img_id
        else:
            abort(400, "Maximum image file size is 40 KB.")

    # If there are multiple image attachments, error out.
    elif len(request.files.getlist('pic')) > 1:
        abort(400, "Only one image may be uploaded at a time.")
    
    db.session.add(newPost)
    db.session.commit()
    
    return "OK", 200 #returning "OK"

@pst_rep_rea_bp.route('/api/post/edit/<int:postId>', methods=['POST'])
@jwt_required()
def editPost(postId):
    if (request.form.get('textContent') is None):
        abort(400, "Invalid request recieved.")

    targetPost = Post.query.filter_by(id=postId, deletedAt = None, posterID = get_jwt_identity()).first()

    if (targetPost is None):
        abort(404, "Unable to find that post")

    targetPost.textContent = request.form.get('textContent')
    targetPost.editedAt = datetime.now()
    db.session.commit()
    
    return "OK", 200 #returning "OK"

@pst_rep_rea_bp.route('/api/post/<int:postID>', methods=['DELETE'])
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
@pst_rep_rea_bp.route('/api/reply', methods=['POST'])
@jwt_required()
def makeReply():

    if (request.form.get('textContent') is None or request.form.get('respTo') is None):
        abort(400, "Invalid request recieved.")

    targetPost = Post.query.filter_by(id = request.form.get('respTo'), deletedAt = None).first()
    if targetPost is None:
        abort(400, "The post you are trying to respond to has been deleted.")

    targetAccount = Account.query.filter_by(id = targetPost.postedOnID, deletedAt = None).first()
    if targetAccount is None:
        abort(400, "The post you are trying to respond to has been deleted.")
    
    permission = canMakeContent(targetAccount.id, get_jwt_identity())
    if permission == 2:
        abort(400, "You do not have permission to reply right now.")
    elif permission == 3:
        abort(400, "You are not friends. You cannot reply.")
    

    newReply = Reply(request.form.get('respTo'), get_jwt_identity(), request.form.get('textContent'))
    db.session.add(newReply)
    db.session.commit()
    return "Okay", 200

@pst_rep_rea_bp.route('/api/reply/<int:replyID>', methods=['DELETE'])
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
@pst_rep_rea_bp.route('/api/reaction', methods=['POST'])
@jwt_required()
def makeReaction():

    
    if (request.form.get('reactionType') is None or request.form.get('respTo') is None):
        abort(400, "Invalid request recieved.")

    targetPost = Post.query.filter_by(id = request.form.get('respTo'), deletedAt = None).first()
    if targetPost is None:
        abort(400, "The post you are trying to react to has been deleted.")

    for reaction in targetPost.reactions:
        if reaction.posterID == get_jwt_identity() and reaction.deletedAt != None:
            reaction.deletedAt = None
            db.session.commit()

            return "OK", 200 #returning "OK"


    
    
    # permission = canMakeContent(request.form.get('respTo'), get_jwt_identity())
    # if permission == 2:
    #     abort(400, "You do not have permission to react right now.")
    # elif permission == 3:
    #     abort(400, "You are not friends. You cannot react.")
   

    newReaction = Reaction(resTo=request.form.get('respTo'), pID=get_jwt_identity())
    db.session.add(newReaction)
    db.session.commit()

    return "OK", 200
 
    

@pst_rep_rea_bp.route('/api/reaction/<int:reactionID>', methods=['DELETE'])
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