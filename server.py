from flask import Flask, render_template, request, flash, redirect, url_for, flash
from flask_login import LoginManager, current_user, login_user, logout_user, login_required, UserMixin
import boto3
import os
from datetime import datetime
import pymysql
from flask_sqlalchemy import SQLAlchemy
import json

app = Flask(__name__)

login = LoginManager(app)
#RDS Database connection. I'm using SQLAlchemy to create models for the database
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://admin:MyPassword@myfinal-1.cre3giroxarw.us-east-1.rds.amazonaws.com:3306/myfinal'  # Replace with your Amazon RDS configuration
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['TEMPLATES_AUTO_RELOAD'] = True


#AWS Creds
AWS_REGION = #YOUR AWS REGION
AWS_ACCESS_KEY = # YOUR ACCES KEY
AWS_SECRET_KEY = # YOUR SECRET KEY
AWS_BUCKET_NAME = # YOUR BUCKET NAME
LAMBDA_FUNCTION_NAME = #YOUR LAMBDA FUNCTION NAME

#Storing info for the s3 boto for s3 bucket communication
s3_client = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY
)
#Storing info for the lambda client for lambda function communication.
lambda_client = boto3.client(
    "lambda",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY
)

db = SQLAlchemy(app)
with app.app_context():
    db.create_all()

app.secret_key = 'CS421'


if not os.path.exists("uploads"):
    os.makedirs("uploads")


#Admin DB model for ther RDS Database. Allows for users to create an account to use the app.
class Admin(UserMixin, db.Model):
	__tablename__ = 'Admin'
	adminid = db.Column(db.Integer, primary_key=True)
	fname = db.Column(db.String(50))
	lname = db.Column(db.String(50))
	email = db.Column(db.String(50), unique=True)
	pword = db.Column(db.String(50))
	
	def __init__(self, fname,lname,email,pword):
		self.fname = fname
		self.lname = lname
		self.email = email
		self.pword = pword
	
	def get_id(self):
           return (self.adminid)



#FileUpload DB modle for the RDS Database. Creates the table for keeping track of order info.
class FileUpload(db.Model):
    __tablename__ = 'fileio'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_email = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f"<UploadedFile {self.filename}>"


def addAdmin(fname, lname, email, pword):
	admin = Admin(fname,lname,email,pword)
	db.session.add(admin)
	db.session.commit()



@login.user_loader
def load_user(user_id):
    return Admin.query.get(user_id)

@app.route('/')
@app.route('/home')
def homepage():
    if current_user.is_authenticated:
        return render_template('home.html', admin=current_user)
    return render_template('home.html')

#Homepage. Users can sign in once they have autheticated
@app.route('/home', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['pword']
        admin = Admin.query.filter_by(email=email).first()
        if admin and admin.pword == password:
            login_user(admin)
            return redirect(url_for('secret'))
        else:
            flash('Invalid email or password. Please try again.')

    return render_template('home.html')

@app.route('/secret')
@login_required
def secret():
    return render_template('secret.html')

#Signs the user up to the website. I'm using the RDS database to store the user info

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    print('hello world signup')
    if request.method == 'POST':
        req = dict(request.form)
        print(req)
        print('hello world')
        addAdmin(req['fname'], req['lname'], req['email'], req['pword'])
        return render_template("home.html")
    else:
        return render_template("signup.html")
    



#Upload. This function will be performing the grunt of the project, making calls to the s3 bucket, lambda, and the RDS database for storing and sending the file

@app.route("/upload", methods=["POST"])
@login_required
def upload():
    if request.method == "POST":
        file = request.files["file"]
        user_emails = request.form["email"].split(",")[:5]  # Get the user's emails as a list, maximum of 5 emails

        if file and user_emails:
            #staging the file
            file_path = os.path.join("uploads", file.filename)
            file.save(file_path)

            #sends the file over to s3
            s3_client.upload_file(file_path, AWS_BUCKET_NAME, file.filename)

            #uploads the file to the RDS Database (the table layout can be found in 'tables.py'. The file is stored as well as the date of when the file was uploaded (uses datetime from the previous assignment))
            uploaded_file = FileUpload(filename=file.filename, user_email=",".join(user_emails))
            db.session.add(uploaded_file)
            db.session.commit()

            # gets rid of the staged file
            os.remove(file_path)

            #Prepping data to be sent
            lambda_payload = {
                "recipient_emails": user_emails,
                "s3_bucket": AWS_BUCKET_NAME,
                "s3_object_key": file.filename
            }

            #starts the lambda function that sends the email data over to the function for login. 
            startLambda(lambda_payload)

            return "File uploaded and email notifications sent successfully!"
        else:
            return "Please provide both a file and at least one email address!"
            
    return render_template("upload.html")  



    #Sends the data through lambda    
def startLambda(lambda_payload):
    response = lambda_client.invoke(
        FunctionName=LAMBDA_FUNCTION_NAME,
        InvocationType="Event",  
        Payload=json.dumps(lambda_payload)
    )


if __name__ == '__main__':
   with app.app_context():
    db.create_all()

    app.run(host='0.0.0.0', port=5000, debug=True)