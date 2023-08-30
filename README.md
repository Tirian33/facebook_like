# facebook_like
For CSE 6214
Used language Python
Used Packages: see requirements.txt

Group members:
Tirian Judy - tirian33 = Team lead & backend member
Alexander Way - = Backend member
Debrah Kwaku - debrahGh = Frontend member
Rishita Garag - = Frontend and documentation

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


SRS at: https://docs.google.com/document/d/1dPo8VYm1W8P0Whk1zNR_1woAZ8ZA6i3S/edit?usp=sharing&ouid=100268486651223932090&rtpof=true&sd=true


To run:
1 time executions in current directory perform: 
$pip install requirements.txt
$export FLASK_APP=app
$export FLASK_ENV=development

After the above have been performed you can launch the app at any time from commandline in the project directory with:
$flask run --reload