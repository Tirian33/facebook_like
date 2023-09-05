from app import db, jwtInfo
import time
import jwt
import bcrypt
from datetime import datetime, timedelta

class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(32))
    passwordHash = db.Column(db.String(128))
    #fName = db.Column(db.String(32), nullable=False)
    #lName = db.Column(db.String(32), nullable=False)
    login = db.relationship('Login', back_populates='account', uselist=False)
    deletedAt = db.Column(db.DateTime)

    def hashPW(input) -> str:
        byteForm = input.encode('utf-8')
        hashedForm = bcrypt.hashpw(byteForm, bcrypt.gensalt())
        return hashedForm
    
    def checkPW(self, password):
        pwBytes = password.encode('utf-8')
        return bcrypt.checkpw(self.passwordHash.encode('utf-8'), pwBytes)

    def genToken(self, expiry=600):
        return jwt.encode({'id': self.id, 'exp': (time.time() + expiry)},
                            jwtInfo, algorithm='HS256' )

    @staticmethod
    def checkToken(token):
        try:
            #attempt to resolve the account
            accData = jwt.decode(token, jwtInfo, algoritms=['HS256'])
        except:
            #we can't resolve an account so return no account
            return
        return Account.query.get(accData)['id']

    #def __init__(self, username, passwordUnhashed, first, last): JIC Need to store F & L names.
    def __init__(self, username, passwordUnhashed):
        self.username = username
        self.passwordHash = self.hashPW(passwordUnhashed)
        #self.fName = first
        #self.lName = last

# JIC Need to break login to different aspects
#class Login(db.Model):
#    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
#    username = db.Column(db.String(32))
#    passwordHash = db.Column(db.String(128))

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    posterID = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    textContent = db.Column(db.String(400)) #We are limiting charcter count to 400 characters.
    #Figure out backpopulation of replies
    #Figure out backpopulation of reactions
    #Figure out image content allowance
    deletedAt = db.Column(db.DateTime)

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
    deletedAt = db.Column(db.DateTime) #Since this is volitile and meaningless data do we want to store its deletion?

class Relationship(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    firstAccountID = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    secondAccountID = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    confirmedRelation = db.Column(db.Boolean, default=False)
    isFriendRelation = db.Column(db.Boolean, default=True)