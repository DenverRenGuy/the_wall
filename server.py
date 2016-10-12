from flask import Flask, redirect, render_template, request, session, flash, url_for
from mysqlconnection import MySQLConnector
import re
from flask.ext.bcrypt import Bcrypt

app = Flask(__name__)
app.secret_key = "ShhhSneaky"
mysql = MySQLConnector(app, 'thewall')
bcrypt = Bcrypt(app)

#Regex matches
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9\.\+_-]+@[a-zA-Z0-9\._-]+\.[a-zA-Z]*$')
LETTERS_REGEX = re.compile(r'^[a-zA-Z]')

@app.route('/')
def index():

    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    d = request.form
    errors = False

    #Registration Logic Checks
    if not LETTERS_REGEX.match(d['first_name'] + d['last_name']):
        errors = True
        flash('Names must only be Letters', 'error')
    if len(d['first_name']) < 2 or len(d['last_name']) < 2:
        errors = True
        flash('Names must be at least two characters', 'error')
    if not EMAIL_REGEX.match(d['email']):
        errors = True
        flash('Email is not in email format')
    if len(d['password']) < 8:
        errors = True
        flash('Passwords must be 8 characters or more', 'error')
    if d['password'] != d['confirm_password']:
        errors = True
        flash('Passwords do not match', 'error')

    if errors:
        return redirect('/')

    #User Exist Checks
    userExistQuery = "SELECT COUNT(*) FROM users WHERE email = :email"
    data = {
        'email': d['email']
    }

    userCount = mysql.query_db(userExistQuery, data)
    if userCount[0]['COUNT(*)'] > 0:
        errors = True
        flash('Email already registered to user in the system, Please Login.', 'error')
        return redirect('/')

    else:
        #Generate Hash
        pw_hash = bcrypt.generate_password_hash(d['password'])

        #Generate query
        registerQuery = 'INSERT INTO users(first_name, last_name, email, password, created_at) VALUES (:first_name, :last_name, :email, :pw_hash, NOW())'
        data = {
            'first_name': d['first_name'],
            'last_name': d['last_name'],
            'email': d['email'],
            'pw_hash': pw_hash
        }

        #Submit Query
        mysql.query_db(registerQuery, data)

        #Get User
        loginQuery = 'SELECT * FROM users WHERE email = :email LIMIT 1'
        data = {
            'email': d['email']
        }
        user = mysql.query_db(loginQuery, data)
        session['user_id'] = user[0]['id']
        session['userName'] = user[0]['first_name'] + user[0]['last_name']
        session['welcome'] = 'visible'
        return redirect(url_for('wall'))

@app.route('/login', methods=['POST'])
def login():
    d = request.form
    loginQuery = 'SELECT * FROM users WHERE email = :email LIMIT 1'
    data = {
        'email': d['email']
    }
    user = mysql.query_db(loginQuery, data)

    #User check_password_hash
    if bcrypt.check_password_hash(user[0]['password'], d['password']):
        session['user_id'] = user[0]['id']
        session['userName'] = user[0]['first_name'] + user[0]['last_name']
        session['welcome'] = 'hidden'
        print session['userName']
        return redirect(url_for('wall'))
    else:
        flash('Email or Password does not match, Please try again.', 'error')
        return redirect('/')

@app.route('/logout', methods=['GET'])
def logout():
    session.pop('user_id')
    return redirect('/')

@app.route('/wall', methods=['GET','POST'])
def wall():

    messagesQuery = "SELECT m.id, m.user_id, m.message, m.created_at, u.first_name, u.last_name FROM messages m JOIN users u ON m.user_id = u.id ORDER BY created_at DESC"

    messages = mysql.query_db(messagesQuery)
    # for message in messages:
    #     commentQuery = 'SELECT * FROM comments c WHERE message_id = :message_id'
    #     data = {
    #         'message_id': message['message_id']
    #     }

    for i in range(len(messages)):
        message_id = messages[i]['id']
        commentQuery = 'SELECT u.first_name, u.last_name, c.comment, c.created_at FROM comments c JOIN users u ON c.user_id = u.id WHERE message_id = :message_id'
        data = {
             'message_id': message_id
         }
        comments = mysql.query_db(commentQuery, data)
        messages[i]['comments'] = comments

    # messageQuery = 'SELECT * FROM messages m WHERE m.user_id = :user_id'
    # messageCommentQuery = 'SELECT * FROM messages m JOIN comments c ON m.id = c.message_id ORDER BY m.user_id'
    #
    # data = {
    #     'user_id': session['user_id']
    # }
    #
    # messages = mysql.query_db(messageQuery, data)

    return render_template('wall.html', messages = messages)

@app.route('/postMessage', methods=['POST'])
def postMessage():
    insertQuery = 'INSERT INTO messages(user_id, message, created_at) VALUES(:user_id, :message, NOW())'
    data = {
        'user_id': session['user_id'],
        'message': request.form['message']
    }

    mysql.query_db(insertQuery, data)

    return redirect(url_for('wall'))

@app.route('/postComment', methods=['POST'])
def postComment():
    d = request.form

    insertQuery = 'INSERT INTO comments(user_id, message_id, comment, created_at) VALUES(:user_id, :message_id, :comment, NOW())'
    data = {
        'user_id': session['user_id'],
        'message_id': request.form['message_id'],
        'comment': d['comment']
    }
    mysql.query_db(insertQuery, data)

    return redirect(url_for('wall'))


app.run(debug=True)
