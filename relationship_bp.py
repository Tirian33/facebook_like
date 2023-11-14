from flask import abort, request, Blueprint
import jwt
from flask_jwt_extended import *
import json
from models import *

relationship_bp = Blueprint('relationship', __name__)

#Friend request sending
@relationship_bp.route('/api/makeFriend', methods=['POST'])
@jwt_required()
def sendFriendRequest():
    if request.json.get('friendCode') is None:
        abort(400, "Need Friend Code of requested friend.")

    targetAccount = Account.query.filter_by(friendCode=request.json.get('friendCode')).first()
   
    if targetAccount is None:
        abort(400, "Friend not found.")

    if targetAccount.id == get_jwt_identity():
        abort(400, "You cannot friend yourself.")
    
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

@relationship_bp.route('/api/declineFriend', methods=['POST'])
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

@relationship_bp.route('/api/removeFriend', methods=['POST'])
@jwt_required()
def removeFriend():
    if request.json.get('friendCode') is None:
        abort(400, "Need Friend Code of ex-friend.")
    elif len(request.json.get('friendCode')) != 8:
        abort(400, "Friend Code is 8 characters.")

    targetAccount = Account.query.filter_by(friendCode=request.json.get('friendCode')).first()
   
    if targetAccount is None:
        abort(400, "Ex-friend not found.")
    
    targetRelationship = Relationship.query.filter_by(secondAccountID = targetAccount.id, firstAccountID = get_jwt_identity(), deletedAt = None).first()
    targetRelationshipInv = Relationship.query.filter_by(secondAccountID = get_jwt_identity(), firstAccountID = targetAccount.id, deletedAt = None).first()
    
    targetRelationship.deletedAt = datetime.now()
    targetRelationshipInv.deletedAt = datetime.now()
    db.session.commit()
    
    return "OK", 200

@relationship_bp.route('/api/blockUser', methods=['POST'])
@jwt_required()
def block_User():
    if request.json.get('friendCode') is None:
        abort(400, "Need Friend Code of user to block.")
    elif len(request.json.get('friendCode')) != 8:
        abort(400, "Friend Code is 8 characters.")

    target_account = Account.query.filter_by(friendCode=request.json.get('friendCode')).first()
   
    if target_account is None:
        abort(400, "User not found.")
    
    block_relationship = Relationship(get_jwt_identity(), target_account.id, False)
    
    db.session.add(block_relationship)
    db.session.commit()
    
    return "OK", 200

@relationship_bp.route('/api/unblockUser', methods=['POST'])
@jwt_required()
def unblock_User():
    if request.json.get('friendCode') is None:
        abort(400, "Need Friend Code of user to unblock.")
    elif len(request.json.get('friendCode')) != 8:
        abort(400, "Friend Code is 8 characters.")

    target_account = Account.query.filter_by(friendCode=request.json.get('friendCode')).first()
   
    if target_account is None:
        abort(400, "User not found.")
    Relationship.isFriendRelation
    target_block = Relationship.query.filter_by(firstAccountID = get_jwt_identity(), secondAccountID = target_account.id, isFriendRelation = False, deletedAt = None).first()
    
    if target_block is not None:
        target_block.deletedAt = datetime.now()
        db.session.commit()
    
    
    return "OK", 200
