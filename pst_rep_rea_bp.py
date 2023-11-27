"""This is the main driving module for Post, Reply, and Reaction related actions in the Facebook imitation app 'Y'."""
from datetime import datetime
from flask import request, jsonify, Blueprint
from flask_jwt_extended import (get_jwt_identity, jwt_required)
from werkzeug.utils import secure_filename
from models import (db, Post, Reaction, Reply, Account, Img, Relationship)

pst_rep_rea_bp = Blueprint('pst_rep_rea', __name__)

def make_error(code=400, message="Unspecified Error Occured."):
    '''
    Makes a jsonified error message.
    P:
        message(string): Message for the error
        code(int): HTTP error code (400s)
    R: 
        response object
    '''
    err = jsonify({'message': message})
    err.status_code = code
    return err

#canMakeContent
def can_make_content(target_acc_id, poster_id):
    '''
    Determines if a user can make a post on the target's timeline.
    P:
        target_acc_id(int): Account.id of the target to be posted on.
        poster_id(int): Account id of the one who wants to post.
    R:
        1 if the poster is allowed to post.
        2 if the target account has gone private.
        3 if the target account is not friends with the poster.
    '''
    if int(target_acc_id) == poster_id:
        return 1

    target_acc = Account.query.filter_by(id = target_acc_id).first()

    if target_acc is not None:
        if not target_acc.is_public:
            return 2

        rel = Relationship.query.filter_by(first_acc_id = target_acc.id, second_acc_id = poster_id, deleted_at = None, is_friend_relation = True).first()
        if rel is not None:
            return 1
    #Not the same account, and Poster is not friend with target account.
    return 3

def soft_delete_objects(listing) -> None:
    """"Soft deletes the listing of objects passed."""
    for item in listing:
        item.deleted_at = datetime.now()
    db.session.commit()

@pst_rep_rea_bp.route('/api/post', methods=['POST'])
@jwt_required()
def make_post():
    '''
    Creates a Post object.
    Expects the following fields in the request object:
        textContent(string): Non-empty string unless there is a sharedPosId or and image.
        sharedPostId(int): Post that is being shared (nullable)
        postedOnID(int): The account the post is to be put on.
        May have a file called "pic" for the image.
    '''
    if ((request.form.get('textContent') is None and request.form.get('sharedPostId')is None) 
        or request.form.get('postedOnID') is None):
        return  make_error(400, "Invalid request recieved.")

    target_account = Account.query.filter_by(id = request.form.get('postedOnID'),
                                             deleted_at = None).first()
    if (target_account is None):
        return make_error(400, "Can't find that person to post on.")
    
    permission = can_make_content(request.form.get('postedOnID'), get_jwt_identity())
    
    if permission == 2:
        return make_error(400, "You do not have permission to post right now.")
    elif permission == 3:
        return make_error(400, "You are not friends. You cannot post")
    
    new_post = Post(get_jwt_identity(), request.form.get('textContent'),
                    request.form.get('postedOnID'), request.form.get('sharedPostId'))
    # If there is only one image attachment...
    if (len(request.files.getlist('pic')) == 1 and 
        ((request.files['pic'].mimetype == 'image/jpeg') 
         or (request.files['pic'].mimetype == 'image/png'))):

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

            new_post.associated_image_id = img_id
        else:
            return make_error(400, "Maximum image file size is 40 KB. File must be .jpg or .png!")

    # If there are multiple image attachments, error out.
    elif len(request.files.getlist('pic')) > 1:
        return make_error(400, "Only one image may be uploaded at a time.")
    
    db.session.add(new_post)
    db.session.commit()

    return "OK", 200 #returning "OK"

@pst_rep_rea_bp.route('/api/post/edit/<int:post_id>', methods=['POST'])
@jwt_required()
def edit_post(post_id):
    '''
    Edits a Post if the caller was the one to make the post.
    Request form is expected to have field textContent.
    '''
    if (request.form.get('textContent') is None):
        return make_error(400, "Invalid request recieved.")

    target_post = Post.query.filter_by(id=post_id, deleted_at = None,
                                       poster_id = get_jwt_identity()).first()

    if (target_post is None):
        return make_error(404, "Unable to find that post")

    target_post.text_content = request.form.get('textContent')
    target_post.edited_at = datetime.now()
    db.session.commit()

    return "OK", 200 #returning "OK"

@pst_rep_rea_bp.route('/api/post/<int:post_id>', methods=['DELETE'])
@jwt_required()
def delete_post(post_id):
    '''
    Deletes the specified post if either the post was made by the caller or is on the caller's timeline.
    '''
    target_post = Post.query.filter_by(id=post_id).first()
    if target_post is None:
        return make_error(400, "Unable to find the post to delete.") #Request made was bad

    if (target_post.posted_on_id == get_jwt_identity()
        or target_post.poster_id == get_jwt_identity()):
        #DEL
        soft_delete_objects(target_post.replies)
        soft_delete_objects(target_post.reactions)
        target_post.deleted_at = datetime.now()
        db.session.commit()
        return "Done", 200

    return make_error(401, "You lack the permission to perform this action.")

#Reply related
@pst_rep_rea_bp.route('/api/reply', methods=['POST'])
@jwt_required()
def make_reply():
    '''
    Creates a Reply.
    Request form is expected to have fields:
        textContent(string): text content
        respTo(int): Post.id of the post the reply is to be associated with.
    '''
    if (request.form.get('textContent') is None
        or request.form.get('respTo') is None):
        return make_error(400, "Invalid request recieved.")

    target_post = Post.query.filter_by(id = request.form.get('respTo'),
                                       deleted_at = None).first()
    if target_post is None:
        return make_error(400, "The post you are trying to respond to has been deleted.")

    target_account = Account.query.filter_by(id = target_post.posted_on_id,
                                             deleted_at = None).first()
    if target_account is None:
        return make_error(400, "The post you are trying to respond to has been deleted.")

    permission = can_make_content(target_account.id, get_jwt_identity())
    if permission == 2:
        return make_error(400, "You do not have permission to reply right now.")
    elif permission == 3:
        return make_error(400, "You are not friends. You cannot reply.")

    new_reply = Reply(request.form.get('respTo'),
                      get_jwt_identity(), request.form.get('textContent'))
    db.session.add(new_reply)
    db.session.commit()
    return "Okay", 200

@pst_rep_rea_bp.route('/api/reply/<int:reply_id>', methods=['DELETE'])
@jwt_required()
def delete_reply(reply_id):
    '''
    Deletes the targeted reply if the caller is either the creator or 
    the owner of the timeline that the post it is assocaited with.
    '''
    target = Reply.query.filter_by(id=reply_id, deleted_at=None).first()
    if target is None:
        return make_error(400, "Unable to find reply to delete.")

    containing_post = Post.query.filter_by(id=target.responding_to).first()

    if (containing_post.posted_on_id == get_jwt_identity()
        or target.poster_id == get_jwt_identity()):

        target.deleted_at = datetime.now()
        db.session.commit()
        return "Done", 200

    return make_error(401, "You lack the permission to perform this action.")

#Reaction related
#Input {reactionType:int, respTo:int} respTo - FK PostID
@pst_rep_rea_bp.route('/api/reaction', methods=['POST'])
@jwt_required()
def make_reaction():
    '''
    Creates a Reaction.
    Request is expected to have following form fields:
        reactionType(int): Type of reaction (for now just 1)
        respTo(int): Post.id of the post the reaction is linked to.
    '''
    if (request.form.get('reactionType') is None
        or request.form.get('respTo') is None):
        return make_error(400, "Invalid request recieved.")

    target_post = Post.query.filter_by(id = request.form.get('respTo'),
                                       deleted_at = None).first()
    if target_post is None:
        return make_error(400, "The post you are trying to react to has been deleted.")

    for reaction in target_post.reactions:
        if (reaction.poster_id == get_jwt_identity() 
            and reaction.deleted_at != None):

            reaction.deleted_at = None
            db.session.commit()

            return "OK", 200

    new_reaction = Reaction(res_to=request.form.get('respTo'),
                            poster_id=get_jwt_identity())
    db.session.add(new_reaction)
    db.session.commit()

    return "OK", 200

@pst_rep_rea_bp.route('/api/reaction/<int:reaction_id>', methods=['DELETE'])
@jwt_required()
def delete_reaction(reaction_id):
    """Deletes reaction if caller is the creator."""
    requester_id = get_jwt_identity()
    
    target = Reaction.query.filter_by(id=reaction_id).first()
    if target is None:
        return make_error(400) #Request made was bad

    containing_post = Post.query.filter_by(id=target.responding_to).first()

    if (containing_post.posted_on_id == requester_id
        or target.poster_id == requester_id):

        target.deleted_at = datetime.now()
        db.session.commit()
        return "Done", 200

    return make_error(401)
