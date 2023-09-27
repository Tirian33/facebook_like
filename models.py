from app import db, bcrypt
import time
import uuid
from datetime import datetime, timedelta

class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(32))
    passwordHash = db.Column(db.String(128))
    fName = db.Column(db.String(32), nullable=False)
    lName = db.Column(db.String(32), nullable=False)
    isPublic = db.Column(db.Boolean, default=False)
    friendCode = db.Column(db.String(10), unique=True, default=str(uuid.uuid4()))
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


    def __init__(self, username, passwordUnhashed, first, last, public = False):
        self.username = username
        self.passwordHash = bcrypt.generate_password_hash(passwordUnhashed).decode('utf-8')
        self.fName = first
        self.lName = last
        self.isPublic = public

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    posterID = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    textContent = db.Column(db.String(400)) #We are limiting charcter count to 400 characters.
    sharedPostID = db.Column(db.Integer, nullable=True)
    replies = db.relationship('Reply', backref='post', lazy='dynamic')
    reactions = db.relationship('Reaction', backref='post', lazy='dynamic')
    deletedAt = db.Column(db.DateTime)

    def __init__(self, pID, text, sharedPID=None):
        self.posterID = pID
        self.textContent = text
        self.sharedPostID = sharedPID

class Reply(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    respondingTo = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    posterID = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    textContent = db.Column(db.String(400)) #We are limiting charcter count to 400 characters.
    deletedAt = db.Column(db.DateTime)

class Reaction(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    respondingTo = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    posterID = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    reactionType = db.Column(db.Integer, default=0)
    deletedAt = db.Column(db.DateTime) 

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
