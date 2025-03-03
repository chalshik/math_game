from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS
import sqlite3
import os 
import json
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
CORS(app)

def create_tables():
    conn = connect_db()
    conn.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL)')
    conn.execute('CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, sender INTEGER, receiver INTEGER, message TEXT NOT NULL, time DATETIME DEFAULT CURRENT_TIMESTAMP)')
    conn.commit()
    conn.close()

def connect_db():
    db = sqlite3.connect('chat.db')
    return db

@app.route('/get_messages', methods=['GET'])
def get_messages():
    db = connect_db()
    cursor = db.cursor()
    
    # Get the receiver from the query string
    receiver = request.args.get('receiver')
    
    # Get the receiver's and sender's IDs
    cursor.execute('SELECT id FROM users WHERE username = ?', (receiver,))
    receiver_row = cursor.fetchone()
    if not receiver_row:
        return jsonify({"status": "error", "message": "Receiver not found"}), 404
    
    receiver_id = receiver_row[0]
    cursor.execute('SELECT id FROM users WHERE username = ?', (session['username'],))
    sender_row = cursor.fetchone()
    if not sender_row:
        return jsonify({"status": "error", "message": "Sender not found"}), 404
    
    sender_id = sender_row[0]
    
    # Query to get messages between the sender and receiver
    cursor.execute("""
        SELECT message, sender, receiver 
        FROM messages 
        WHERE (sender = ? AND receiver = ?) OR (sender = ? AND receiver = ?)
        """, (sender_id, receiver_id, receiver_id, sender_id))
    
    messages = cursor.fetchall()
    db.close()
    
    # Format the messages with a 'type' to distinguish sender and receiver
    message_list = []
    for message, msg_sender, msg_receiver in messages:
        msg_type = 'sent' if msg_sender == sender_id else 'received'
        message_list.append({
            'message': message,
            'type': msg_type
        })
    
    # Return the messages as JSON
    return jsonify(message_list)

@app.route('/all_users', methods=['GET'])
def all_users():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('SELECT username FROM users')
    users = cursor.fetchall()
    conn.close()
    usernames = [user[0] for user in users]
    return jsonify(usernames)

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.get_json()
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE username = ?',(data['receiver'],))
    receiver_id = cursor.fetchone()[0]
    cursor.execute('SELECT id FROM users WHERE username = ?',(session['username'],))
    sender_id = cursor.fetchone()[0]
    cursor.execute('INSERT INTO messages (sender,receiver,message) VALUES (?,?,?)',(sender_id,receiver_id,data['message']))
    conn.commit()
    conn.close()
    return jsonify({"status":"success","message":"message sent successfully"})

@app.route('/register', methods=['POST'])
def register_user():
    data = request.get_json()
    
    # Check if the user exists
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (data['username'],))
    user = cursor.fetchone()
    
    if user:
        return jsonify({'status': 'error', 'message': 'username already exists'})
    
    # Hash the password before saving
    hashed_password = generate_password_hash(data['password'])
    cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (data['username'], hashed_password))
    conn.commit()
    conn.close()

    return jsonify({'status': 'success', 'message': 'user registered successfully'})

@app.route('/login_page', methods=['GET'])
def login_page():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data['username']
    password = data['password']
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    if user and check_password_hash(user[2], password):  # user[2] is password column
        session['username'] = username
        return jsonify({"status":"success","message":"user logged in successfully"})
    else:
        return jsonify({"status":"error","message":"invalid username or password","name":username})

@app.route('/logout', methods=['GET'])
def logout():
    session.pop('username', None)
    return redirect(url_for('login_page'))

@app.route('/main', methods=['GET'])
def main():
    if 'username' in session:
        username = session['username']
        return render_template('home.html', username=username)
    else:
        return redirect(url_for('login_page'))

@app.route('/', methods=['GET'])
def home():
    create_tables()  # Create tables at startup
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
