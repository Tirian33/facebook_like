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

    def genToken(account, expiry=600):
        return jwt.encode({'id': account.id, 'exp': (time.time() + expiry)},
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