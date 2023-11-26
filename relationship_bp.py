"""This is the main driving module for Relationship actions in the Facebook imitation app 'Y'."""
from datetime import datetime
from flask import (request, jsonify, Blueprint)
from flask_jwt_extended import (get_jwt_identity, jwt_required)
from models import (db, Relationship, Account)

relationship_bp = Blueprint('relationship', __name__)

#Friend request sending
@relationship_bp.route('/api/makeFriend', methods=['POST'])
@jwt_required()
def send_friend_request():
    '''
    Creates a one way Relationship that is not confirmed between the caller and the target.
    Request of json should have field 'friendCode'(string): The friend_code of the target Account.
    '''
    if request.json.get('friendCode') is None:
        err = jsonify({'message':
                       "Need Friend Code of requested friend."})
        err.status_code = 400
        return err

    target_account = Account.query.filter_by(friend_code=request.json.get('friendCode')).first()

    if target_account is None:
        err = jsonify({'message':
                       "No user found with that Friend Code."})
        err.status_code = 400
        return err

    if target_account.id == get_jwt_identity():
        err = jsonify({'message':
                       "You entered your Friend Code. You need someone else's to be friends"})
        err.status_code = 400
        return err

        # Request was sent in the past
    if Relationship.query.filter_by(first_acc_id = get_jwt_identity(),
                                    second_acc_id = target_account.id, deleted_at = None
                                    ).first() is not None:
        err = jsonify({'message':
                       "You already sent this user a friend request in the past."})
        err.status_code = 400
        return err

    pending_inverse = Relationship.query.filter_by(second_acc_id = get_jwt_identity(),
                                                    first_acc_id = target_account.id,
                                                    deleted_at = None
                                                    ).first()

    # Other person sent a friend request in the past, lets accept
    if pending_inverse is not None:
        if pending_inverse.is_friend_relation:
            pending_inverse.confirmed_relation = True
            db.session.add(pending_inverse.make_inverse())
            db.session.commit()
            return "OK", 200
        err = jsonify({'message':
                       "The user you are trying to friend has blocked you."})
        err.status_code = 400
        return err

    # Lets make the request
    new_relationship = Relationship(get_jwt_identity(), target_account.id)
    db.session.add(new_relationship)
    db.session.commit()

    return "OK", 200

@relationship_bp.route('/api/declineFriend', methods=['POST'])
@jwt_required()
def decline_friend_request():
    '''
    Declines a friend request by soft deleting the relationship.
    Request json is expected to have friendCode(string): Account.friend_code of target account.
    '''
    if request.json.get('friendCode') is None:
        err = jsonify({'message':
                       "Need Friend Code of declining friend."})
        err.status_code = 400
        return err
    if len(request.json.get('friendCode')) != 8:
        err = jsonify({'message':
                       "Friend Code must be 8 characters"})
        err.status_code = 400
        return err

    target_account = Account.query.filter_by(friend_code=request.json.get('friendCode')).first()

    if target_account is None:
        err = jsonify({'message':
                       "The user that has sent this request no longer exists."})
        err.status_code = 400
        return err

    target_relationship = Relationship.query.filter_by(second_acc_id = get_jwt_identity(),
                                                        first_acc_id = target_account.id,
                                                        deleted_at = None).first()

    if target_relationship is None:
        err = jsonify({'message':
                       "Somehow you tried to accept a request that doesn't exist!"})
        err.status_code = 400
        return err

    target_relationship.deleted_at = datetime.now()
    db.session.commit()

    return "OK", 200

@relationship_bp.route('/api/removeFriend', methods=['POST'])
@jwt_required()
def remove_friend():
    '''
    Removes a friend by soft deleting both confirmed friend Relationships.
    Request json is expected to have friendCode(string): Account.friend_code of target account.
    '''
    if request.json.get('friendCode') is None:
        err = jsonify({'message':
                       "Friend Code required."})
        err.status_code = 400
        return err
    if len(request.json.get('friendCode')) != 8:
        err = jsonify({'message':
                       "Friend Code is 8 characters"})
        err.status_code = 400
        return err

    target_account = Account.query.filter_by(friend_code=request.json.get('friendCode')).first()

    if target_account is None:
        err = jsonify({'message':
                       "Friend Code does not target an account."})
        err.status_code = 400
        return err

    target_relationship = Relationship.query.filter_by(second_acc_id = target_account.id,
                                                       first_acc_id = get_jwt_identity(),
                                                       deleted_at = None).first()

    target_relationship_inv = Relationship.query.filter_by(second_acc_id = get_jwt_identity(),
                                                           first_acc_id = target_account.id,
                                                           deleted_at = None).first()

    target_relationship.deleted_at = datetime.now()
    target_relationship_inv.deleted_at = datetime.now()
    db.session.commit()

    return "OK", 200

@relationship_bp.route('/api/blockUser', methods=['POST'])
@jwt_required()
def block_user():
    '''
    Creates a block Relationship with target account.
    Request json is expected to have friendCode(string): Account.friend_code of target account.
    '''
    if request.json.get('friendCode') is None:
        err = jsonify({'message':
                       "Friend Code required."})
        err.status_code = 400
        return err
    if len(request.json.get('friendCode')) != 8:
        err = jsonify({'message':
                       "Friend Code is 8 characters"})
        err.status_code = 400
        return err

    target_account = Account.query.filter_by(
        friend_code=request.json.get('friendCode')).first()

    if target_account is None:
        err = jsonify({'message':
                       "Friend Code does not target an account."})
        err.status_code = 400
        return err

    block_relationship = Relationship(get_jwt_identity(), target_account.id, False)

    friend_req = Relationship.query.filter_by(second_acc_id = get_jwt_identity(),
                                            first_acc_id = target_account.id,
                                            deleted_at = None).first()
    friend_req.deleted_at = datetime.now()

    db.session.add(block_relationship)
    db.session.commit()

    return "OK", 200

@relationship_bp.route('/api/unblockUser', methods=['POST'])
@jwt_required()
def unblock_user():
    '''
    Removes a block Relationship with target account by soft deleting it.
    Request json is expected to have friendCode(string): Account.friend_code of target account.
    '''
    if request.json.get('friendCode') is None:
        err = jsonify({'message':
                       "Friend Code is required."})
        err.status_code = 400
        return err
    if len(request.json.get('friendCode')) != 8:
        err = jsonify({'message':
                       "Friend Code is 8 characters."})
        err.status_code = 400
        return err

    target_account = Account.query.filter_by(friend_code=request.json.get('friendCode')).first()

    if target_account is None:
        err = jsonify({'message':
                       "Friend Code does not target an account."})
        err.status_code = 400
        return err

    target_block = Relationship.query.filter_by(first_acc_id = get_jwt_identity(),
                                                second_acc_id = target_account.id,
                                                is_friend_relation = False,
                                                deleted_at = None).first()
    if target_block is not None:
        target_block.deleted_at = datetime.now()
        db.session.commit()
    return "OK", 200
