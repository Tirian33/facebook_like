from app import db, bcrypt
import time
import uuid
from datetime import datetime, timedelta
import random
import string


class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(32))
    passwordHash = db.Column(db.String(128))
    fName = db.Column(db.String(32), nullable=False)
    lName = db.Column(db.String(32), nullable=False)
    isPublic = db.Column(db.Boolean, default=False)
    friendCode = db.Column(db.String(8), unique=True)
    deletedAt = db.Column(db.DateTime)
    
    def checkPW(self, password):
        return bcrypt.check_password_hash(self.passwordHash, password)

    def toDict(self):
        dictForm = {
            'id' : self.id,
            'username' : self.username,
            'fName' : self.fName,
            'lName' : self.lName,
            'isPublic' : self.isPublic,
            'friendCode' : self.friendCode,
        }
        return dictForm
    
    def toPostData(self):
        data = {}
        data[self.id] = self.fName + " " + self.lName
        return data


    def __init__(self, username, passwordUnhashed, first, last, public = False):
        self.username = username
        self.passwordHash = bcrypt.generate_password_hash(passwordUnhashed).decode('utf-8')
        self.fName = first
        self.lName = last
        self.isPublic = public
        while True:
            code = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(8))
            if Account.query.filter_by(friendCode=code).first() is None:
                self.friendCode = code
                break

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    posterID = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    postedOnID = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    textContent = db.Column(db.String(400)) #We are limiting charcter count to 400 characters.
    sharedPostID = db.Column(db.Integer, nullable=True)
    associatedImageID = db.Column(db.Integer, nullable=True)
    replies = db.relationship('Reply', backref='post', lazy='joined')
    reactions = db.relationship('Reaction', backref='post', lazy='joined')
    createdAt = db.Column(db.DateTime)
    editedAt = db.Column(db.DateTime)
    deletedAt = db.Column(db.DateTime)

    def process(self, callerAccId):
        userReacted = False
        sharedPostTxt = ""
        sharedPostImg = ""

        for react in self.reactions:
            if react.posterID == callerAccId:
                userReacted = True

        if self.sharedPostID is not None and self.sharedPostID != 0:
            targPst = Post.query.filter_by(id=self.sharedPostID).first()
            sharedPostTxt = targPst.textContent
            sharedPostImg = targPst.associatedImageID

        dictForm = {
            'id' : self.id,
            'posterID' : self.posterID,
            'postedOnID' : self.postedOnID,
            'textContent' : self.textContent,
            'sharedPostID' : self.sharedPostID,
            'associatedImageID' : self.associatedImageID,
            'replies' : self.replies,
            'reactions' : len(self.reactions),
            'createdAt' : self.createdAt,
            'editiedAt' : self.editedAt,
            'userReacted' : userReacted,
            'sharedPostTxt' : sharedPostTxt,
            'sharedPostImgId' : sharedPostImg,
        }

        return dictForm

    def __init__(self, pID, text, target, sharedPID=None, imgID=None):
        self.posterID = pID
        self.postedOnID = target
        self.textContent = text
        self.sharedPostID = sharedPID
        self.associatedImageID = imgID
        self.createdAt = datetime.now()
        self.editedAt = None

class Reply(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    respondingTo = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    posterID = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    textContent = db.Column(db.String(400)) #We are limiting charcter count to 400 characters.
    deletedAt = db.Column(db.DateTime)
    def __init__(self, resToID, pID, text):
        self.respondingTo = resToID
        self.posterID = pID
        self.textContent = text

class Reaction(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    respondingTo = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    posterID = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    reactionType = db.Column(db.Integer, default=0)
    deletedAt = db.Column(db.DateTime) 

    def __init__(self, resTo, pID, reactionType = 0):
        self.respondingTo = resTo
        self.posterID = pID
        self.reactionType = reactionType

class Relationship(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    firstAccountID = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    secondAccountID = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    confirmedRelation = db.Column(db.Boolean, default=False)
    isFriendRelation = db.Column(db.Boolean, default=True)
    deletedAt = db.Column(db.DateTime)

    def __init__(self, initiatorID, targetID, friend=True):
        self.firstAccountID = initiatorID
        self.secondAccountID = targetID
        self.isFriendRelation = friend
    
    def makeInverse(self):
        inverse = Relationship(self.secondAccountID, self.firstAccountID, self.isFriendRelation)
        inverse.confirmedRelation = True
        return inverse

class Img(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    img = db.Column(db.LargeBinary, nullable=False)
    name = db.Column(db.Text, nullable=False)
    mimetype = db.Column(db.Text, nullable=False)
    deletedAt = db.Column(db.DateTime)