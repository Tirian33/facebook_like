"""This is the main driving module for page rendering in the Facebook imitation app 'Y'."""
from flask import abort, request, render_template, redirect, url_for, Blueprint
from flask_jwt_extended import (get_jwt_identity, jwt_required)
from models import (db, Post, Relationship, Account)
from pst_rep_rea_bp import can_make_content

pages_bp = Blueprint('pages', __name__)

@pages_bp.route('/')
def index_page():
    """Index redirects to the login page."""
    return redirect(url_for('pages.login_page'))

@pages_bp.route('/login')
def login_page():
    """Renders the login page."""
    redirected = request.args.get('redirectReason')
    return render_template('login.html', redirectReason=redirected)

@pages_bp.route('/register')
def register_page():
    """ Alias for /signup, renders the signup page."""
    return render_template('signup.html')

@pages_bp.route('/profile')
@jwt_required()
def home_page():
    """Renders the profile page with data for the current user."""
    acc = Account.query.filter_by(id=get_jwt_identity()).first()

    #Gets all the accounts that are friends with the user.
    raw_friends = db.session.query(Account).join( Relationship, (Relationship.first_acc_id==acc.id)
                                                 & (Relationship.second_acc_id == Account.id)
                                                 & (Relationship.confirmed_relation == True)
                                                 & (Relationship.is_friend_relation == True)
                                                 & (Relationship.deleted_at == None)).all()
    raw_postable = db.session.query(Account).join( Relationship, (Relationship.first_acc_id==acc.id)
                                                  & (Relationship.second_acc_id == Account.id)
                                                  & (Relationship.confirmed_relation == True)
                                                  & (Relationship.is_friend_relation == True)).all()
                                                  & (Relationship.confirmed_relation == True)
                                                  & (Relationship.is_friend_relation == True)).all()

    friends = []
    postable = {}
    postable.update(acc.to_post_data())

    for friend in raw_friends:
        friends.append(friend.to_dict())

    for user in raw_postable:
        postable.update(user.to_post_data())

    raw_timeline = Post.query.filter_by(posted_on_id=get_jwt_identity(),
                                    deleted_at=None).order_by(Post.id.desc()).all()
    processed_timeline = []
    for pst in raw_timeline:
        processed_timeline.append(pst.process(get_jwt_identity()))

    liked_posts = []
    liked_reactions = []
    for post in raw_timeline:
        for reaction in post.reactions:
            if reaction.poster_id == get_jwt_identity():
                if reaction.deleted_at is None:
                    liked_posts.append(post.id)
                    liked_reactions.append(reaction.id)

    user_reactions = {liked_posts[i]: liked_reactions[i] for i in range(len(liked_posts))}

    posts = []
    num_likes = []
    for post in raw_timeline:
        posts.append(post.id)
        count_likes = 0
        for reaction in post.reactions:
            if reaction.deleted_at is None:
                count_likes = count_likes+1
        num_likes.append(count_likes)

    num_likes = {posts[i]: num_likes[i] for i in range(len(posts))}

    return render_template('profile.html', account = acc.to_dict(), friends = friends,
                           timeline = processed_timeline, postable=postable,
                           pageOwner=get_jwt_identity(), user = acc,
                           likedPosts = liked_posts, userReactions=user_reactions,
                           numLikes=num_likes)

@pages_bp.route('/timeline/<int:acc_id>')
@jwt_required()
def timeline(acc_id):
    """Renders the profile page with data for a different user."""
    if acc_id == get_jwt_identity():
        return redirect(url_for('homePage'))

    permission = can_make_content(acc_id, get_jwt_identity())
    if permission == 2:
        abort(401, description="Profile is private.")
    elif permission == 3:
        abort(401, description="You are not friends.")

    my_acc = Account.query.filter_by(id=get_jwt_identity()).first()
    target_acc = Account.query.filter_by(id=acc_id).first()

    # Gets all the accounts that are friends with the caller.
    all_my_friends = db.session.query(Account).join( Relationship,
                                            (Relationship.first_acc_id == get_jwt_identity())
                                            & (Relationship.second_acc_id == Account.id)
                                            & (Relationship.confirmed_relation == True)
                                            & (Relationship.is_friend_relation == True)).all()
    all_my_friends_ids = [account.id for account in all_my_friends]

    # Gets all the accounts that are friends with the user.
    raw_t_friends = db.session.query(Account).join( Relationship,
                                            (Relationship.first_acc_id == acc_id)
                                            & (Relationship.second_acc_id == Account.id)
                                            & (Relationship.confirmed_relation == True)
                                            & (Relationship.is_friend_relation == True)
                                            & (Relationship.deleted_at == None)).all()
    raw_t_postable = db.session.query(Account).join( Relationship,
                                            (Relationship.first_acc_id == acc_id)
                                            & (Relationship.second_acc_id == Account.id)
                                            & (Relationship.confirmed_relation == True)
                                            & (Relationship.is_friend_relation == True)).all()

    targ_friends = []
    postable = {}
    postable.update(target_acc.to_post_data())

    for friend in raw_t_friends:
        targ_friends.append(friend.to_dict())

    for user in raw_t_postable:
        postable.update(user.to_post_data())

    raw_timeline = Post.query.filter_by(posted_on_id=acc_id,
                                    deleted_at=None).order_by(Post.id.desc()).all()
    processed_timeline = []
    for pst in raw_timeline:
        processed_timeline.append(pst.process(my_acc.id, all_my_friends_ids))

    liked_posts = []
    liked_reactions = []
    for post in raw_timeline:
        for reaction in post.reactions:
            if reaction.poster_id == get_jwt_identity():
                if reaction.deleted_at is None:
                    liked_posts.append(post.id)
                    liked_reactions.append(reaction.id)

    user_reactions = {liked_posts[i]: liked_reactions[i]
                      for i in range(len(liked_posts))}

    posts = []
    num_likes = []
    for post in raw_timeline:
        posts.append(post.id)
        count_likes = 0
        for reaction in post.reactions:
            if reaction.deleted_at is None:
                count_likes = count_likes+1
        num_likes.append(count_likes)

    num_likes = {posts[i]: num_likes[i] for i in range(len(posts))}


    return render_template('profile.html', account = target_acc.to_dict(),
                           friends = targ_friends, timeline = processed_timeline,
                           postable=postable, pageOwner=acc_id, user=my_acc,
                           userReactions=user_reactions, likedPosts=liked_posts,
                           numLikes=num_likes)

@pages_bp.route('/friends')
@jwt_required()
def friend_page():
    """Renders the friends page for the current user."""
    acc = Account.query.filter_by(id=get_jwt_identity()).first()

    # friends = db.session.query(Account).join( Relationship, (Relationship.first_acc_id == acc.id) & (Relationship.second_acc_id == Account.id) & (Relationship.confirmed_relation == True) & (Relationship.is_friend_relation == True) & (Relationship.deleted_at == None)).all()
    # pending = db.session.query(Account).join( Relationship, (Relationship.first_acc_id == Account.id) & (Relationship.second_acc_id == acc.id) & (Relationship.confirmed_relation == False) & (Relationship.is_friend_relation == True) & (Relationship.deleted_at == None)).all()
    # blocked = db.session.query(Account).join( Relationship, (Relationship.first_acc_id == acc.id) & (Relationship.second_acc_id == Account.id) & (Relationship.is_friend_relation == False) & (Relationship.deleted_at == None)).all()

    friends = db.session.query(Account).join( Relationship, (Relationship.first_acc_id == acc.id)
                                        & (Relationship.second_acc_id == Account.id)
                                        & (Relationship.confirmed_relation == True)
                                        & (Relationship.is_friend_relation == True)
                                        & (Relationship.deleted_at == None)).all()
    pending = db.session.query(Account).join( Relationship,
                                        (Relationship.first_acc_id == Account.id)
                                        & (Relationship.second_acc_id == acc.id)
                                        & (Relationship.confirmed_relation == False)
                                        & (Relationship.is_friend_relation == True)
                                        & (Relationship.deleted_at == None)).all()
    blocked = db.session.query(Account).join( Relationship, (Relationship.first_acc_id is acc.id)
                                        & (Relationship.second_acc_id == Account.id)
                                        & (Relationship.is_friend_relation == False)
                                        & (Relationship.deleted_at == None)).all()
    friends_processed = [fren.to_dict() for fren in friends]
    pending_processed = [pend.to_dict() for pend in pending]
    blocked_processed = [blck.to_dict() for blck in blocked]

    return render_template('friends.html', account = acc.to_dict(),
                           friends = friends_processed,
                           pending = pending_processed,
                           blocked = blocked_processed)

@pages_bp.route('/signup')
def sign_up_page():
    """Renders the signup page."""
    return render_template('signup.html')

@pages_bp.route('/settings')
@jwt_required()
def settings_page():
    """Renders settings page for current user."""
    user_acc_id = get_jwt_identity()
    acc = Account.query.filter_by(id=user_acc_id).first()
    return render_template('settings.html', account = acc.to_dict())
