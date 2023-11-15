"""This is the data models for the Facebook imitation app 'Y'."""
import random
import string
from app import db, bcrypt
from datetime import datetime

class Account(db.Model):
    """Model for Account"""
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(32))
    password_hash = db.Column(db.String(128))
    first_name = db.Column(db.String(32), nullable=False)
    last_name = db.Column(db.String(32), nullable=False)
    bio = db.Column(db.String(400), nullable=True)
    profile_image_id = db.Column(db.Integer, nullable=True)
    cover_image_id = db.Column(db.Integer, nullable=True)
    is_public = db.Column(db.Boolean, default=False)
    friend_code = db.Column(db.String(8), unique=True)
    deleted_at = db.Column(db.DateTime)
    
    def check_pw(self, password):
        '''
        Compares unencrypted password to the password_hash
        P:
            password(string): Password to be tested
        R:
            Boolean of evaluation
        '''
        return bcrypt.check_password_hash(self.password_hash, password)

    def to_dict(self):
        '''
        Converts the Account to a dictionary with reduced information.
        R:
            Dictionary of the Account object (legacy version of class is returned)
        '''
        dict_form = {
            'id' : self.id,
            'username' : self.username,
            'fName' : self.first_name,
            'lName' : self.last_name,
            'bio' : self.bio,
            'isPublic' : self.is_public,
            'friendCode' : self.friend_code,
            'profileImageID': self.profile_image_id,
            'coverImageID': self.cover_image_id
        }
        return dict_form
    
    def to_post_data(self):
        '''
        Returns a dictionary with keys id & id-p which contain the (first name & last name) and profile image id respectively.
        '''
        data = {}
        data[self.id] = self.first_name + " " + self.last_name
        data[str(self.id) + "-p"] = self.profile_image_id
        return data
    
    def changePW(self, old_pw, new_pw):
        '''
        Changes the password of an Account.
        P:
            old_pw(string): Old passsword in plaintext (for authentication)
            new_pw(string): New password to be set for the Account
        R: 
            Retruns True if password was updated; False if old_pw is invalid.
        '''
        if not self.check_pw(old_pw):
            return False
        
        #Password was correct so change the PW to the new PW
        self.password_hash = bcrypt.generate_password_hash(new_pw).decode('utf-8')
        return True


    def __init__(self, username, password_unhashed, first, last, bio, public = False):
        """Constructor for Account."""
        self.username = username
        self.password_hash = bcrypt.generate_password_hash(password_unhashed).decode('utf-8')
        self.first_name = first
        self.last_name = last
        self.bio = bio
        self.is_public = public
        while True:
            code = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(8))
            if Account.query.filter_by(friendCode=code).first() is None:
                self.friend_code = code
                break

class Post(db.Model):
    """Model for Post"""
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    poster_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    posted_on_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    text_content = db.Column(db.String(400)) #We are limiting charcter count to 400 characters.
    shared_post_id = db.Column(db.Integer, nullable=True)
    associated_image_id = db.Column(db.Integer, nullable=True)
    replies = db.relationship('Reply', backref='post', lazy='joined')
    reactions = db.relationship('Reaction', backref='post', lazy='joined')
    created_at = db.Column(db.DateTime)
    edited_at = db.Column(db.DateTime)
    deleted_at = db.Column(db.DateTime)

    def process(self, caller_acc_id, caller_friends = None):
        '''
        Processes a post for timeline/home_page
        P:
            caller_acc_id(int): Account.id of the account that is rendering the page
            caller_friends(list): List of Account.ids for caller's friends
        R:
            Dictionary of the post object using camelCase for the front end with shared posts and reactions processed.
        '''
        user_reacted = False
        sp_txt = ""
        sp_img_id = ""
        sp_on = None
        sp_created_at = None

        for react in self.reactions:
            if react.poster_id == caller_acc_id:
                user_reacted = True

        if self.shared_post_id is not None and self.shared_post_id != 0:
            targ_pst = Post.query.filter_by(id=self.shared_post_id).first()
            if self.poster_id == caller_acc_id or targ_pst.poster_id == caller_acc_id or (targ_pst.id is not None and (caller_friends is None or targ_pst.poster_id in caller_friends)):
                sp_txt = targ_pst.text_content
                sp_img_id = targ_pst.associated_image_id
                sp_on = targ_pst.posted_on_id
                sp_created_at =  targ_pst.created_at

        dict_form = {
            'id' : self.id,
            'posterID' : self.poster_id,
            'postedOnID' : self.posted_on_id,
            'textContent' : self.text_content,
            'sharedPostID' : self.shared_post_id,
            'associatedImageID' : self.associated_image_id,
            'replies' : self.replies,
            'reactions' : self.reactions,
            'createdAt' : self.created_at,
            'editiedAt' : self.edited_at,
            'userReacted' : user_reacted,
            'sharedPostTxt' : sp_txt,
            'sharedPostImgId' : sp_img_id,
            'sharedPostAccId' : sp_on,
            'sharedPostCreatedAt' : sp_created_at
        }

        return dict_form

    def __init__(self, pID, text, target, shared_post_id=None, image_id=None):
        """Constructor for Post."""
        self.poster_id = pID
        self.posted_on_id = target
        self.text_content = text
        self.shared_post_id = shared_post_id
        self.associated_image_id = image_id
        self.created_at = datetime.now()
        self.edited_at = None

class Reply(db.Model):
    """Model for Reply"""
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    responding_to = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    poster_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    text_content = db.Column(db.String(400)) #We are limiting charcter count to 400 characters.
    created_at = db.Column(db.DateTime)
    edited_at = db.Column(db.DateTime)
    deleted_at = db.Column(db.DateTime)

    def __init__(self, res_to_id, pid, text):
        """Constructor for Reply"""
        self.responding_to = res_to_id
        self.poster_id = pid
        self.text_content = text
        self.created_at = datetime.now()
        self.edited_at = None

class Reaction(db.Model):
    """Model for Reaction."""
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    responding_to = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    poster_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    reaction_type = db.Column(db.Integer, default=0)
    deleted_at = db.Column(db.DateTime)

    def __init__(self, res_to, poster_id, reaction_type = 0):
        """Constructor for Reaction."""
        self.responding_to = res_to
        self.poster_id = poster_id
        self.reaction_type = reaction_type

class Relationship(db.Model):
    """Model for Relationship"""
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_acc_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    second_acc_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    confirmed_relation = db.Column(db.Boolean, default=False)
    is_friend_relation = db.Column(db.Boolean, default=True)
    deleted_at = db.Column(db.DateTime)

    def __init__(self, initiator_id, target_id, friend=True):
        """Constructor for Relationship."""
        self.first_acc_id = initiator_id
        self.second_acc_id = target_id
        self.is_friend_relation = friend
    
    def make_inverse(self):
        '''
        Returns an inverse relationship of a given Relationship. Useful for accepting friend requests.
        '''
        inverse = Relationship(self.second_acc_id, self.first_acc_id, self.is_friend_relation)
        inverse.confirmed_relation = True
        return inverse

class Img(db.Model):
    """Model for Img."""
    id = db.Column(db.Integer, primary_key=True)
    img = db.Column(db.LargeBinary, nullable=False)
    name = db.Column(db.Text, nullable=False)
    mimetype = db.Column(db.Text, nullable=False)
    deleted_at = db.Column(db.DateTime)

    def __init__(self, img, name, mimetype):
        """Constructor for Img"""
        self.img = img
        self.name = name
        self.mimetype = mimetype