# facebook_like
For CSE 6214
Used language Python
Used Packages: see requirements.txt

Group members:
Tirian Judy - tirian33 = Team lead & backend member
Alexander Way - asw241 = Backend member
Debrah Kwaku - debrahGh = Frontend member
Rishita Garg - RishitaGarg1= Frontend and documentation

Purpose:
Description
The purpose of this project is to emulate a low level version of Facebook. It will allow for basic friend operations and for posting messages.

Objectives:
Creation of a social media platform that allows friend systems, status updates/posts, a timeline of posts, comments and like reactions to posts made by self and others.

Features:
Login Auth and JWT tracking
Friend System
Pubilc status posts
Private messages between friends
Personal Timeline of posts
Ability to react to posts with comments and likes


To run:
1. Create or load .env file with variables: SQLALCHEMY_DATABASE_URI, SQLALCHEMY_SESSION_TIMEOUT, MAX_CONTENT_LENGTH, and SECRET_KEY.
2. Execute the following in project folder (only needed to be performed on first run) 
$pip install -r requirements.txt
$export FLASK_APP=app
$export FLASK_ENV=development

3. Execute the following command in project folder (All cases, start here if project is fuly configed and was restarted)
$flask run --reload
