from flask import Flask, request, jsonify, render_template, session, redirect, url_for, g
from flask_cors import CORS
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
CORS(app)

DB_PATH = "chat.db"

def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Позволяет обращаться к колонкам по имени
    return conn

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def create_tables():
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender INTEGER,
                receiver INTEGER,
                message TEXT NOT NULL,
                time DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                contact_id INTEGER);
        ''')
        conn.commit()

@app.route('/get_messages', methods=['GET'])
def get_messages():
    if 'username' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    receiver = request.args.get('receiver')
    if not receiver:
        return jsonify({"status": "error", "message": "Receiver required"}), 400

    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE username = ?', (receiver,))
        receiver_row = cursor.fetchone()
        cursor.execute('SELECT id FROM users WHERE username = ?', (session['username'],))
        sender_row = cursor.fetchone()

        if not receiver_row or not sender_row:
            return jsonify({"status": "error", "message": "User not found"}), 404

        receiver_id, sender_id = receiver_row['id'], sender_row['id']

        cursor.execute('''
            SELECT message, sender FROM messages
            WHERE (sender = ? AND receiver = ?) OR (sender = ? AND receiver = ?)
            ORDER BY time ASC
        ''', (sender_id, receiver_id, receiver_id, sender_id))

        messages = [{
            'message': row['message'],
            'type': 'sent' if row['sender'] == sender_id else 'received'
        } for row in cursor.fetchall()]
    
    return jsonify(messages)

@app.route('/all_users', methods=['GET'])
def all_users():
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ?", (session['username'],))
        user_id = cursor.fetchone()
        
        # Ensure that the user_id is retrieved correctly (accessing first element of the tuple)
        if user_id:
            user_id = user_id[0]
            cursor.execute("SELECT contact_id FROM contacts WHERE user_id = ?", (user_id,))
            contacts = cursor.fetchall()
            
            users = []
            for con in contacts:
                contact_id = con[0]  # Accessing the contact_id
                cursor.execute("SELECT username FROM users WHERE id = ?", (contact_id,))
                user = cursor.fetchone()
                if user:
                    users.append(user['username'])  # Append the username to the list
        else:
            users = []  
            
    return jsonify(users)

@app.route('/send_message', methods=['POST'])
def send_message():
    if 'username' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    
    data = request.get_json()
    receiver = data.get('receiver')
    message = data.get('message')
    
    if not receiver or not message:
        return jsonify({"status": "error", "message": "Receiver and message required"}), 400

    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE username = ?', (receiver,))
        receiver_row = cursor.fetchone()
        cursor.execute('SELECT id FROM users WHERE username = ?', (session['username'],))
        sender_row = cursor.fetchone()

        if not receiver_row or not sender_row:
            return jsonify({"status": "error", "message": "User not found"}), 404

        cursor.execute('INSERT INTO messages (sender, receiver, message) VALUES (?, ?, ?)',
                       (sender_row['id'], receiver_row['id'], message))
        conn.commit()
    
    return jsonify({"status": "success", "message": "Message sent successfully"})
@app.route('/search_contact', methods=['POST'])  # Keep POST method
def search_contact():
    user = session['username']
    contact = request.json.get('contact')  # Use `request.json` to parse JSON body
    
    with connect_db() as conn:
        cursor = conn.cursor()
        
        # Check if the contact exists in the database
        cursor.execute("SELECT username FROM users WHERE username LIKE ? AND username != ?", ('%' + contact + '%', user))
        contacts = cursor.fetchone()
        
        if contacts:
            # Insert contact relationship in both directions
            cursor.execute(
                """
                INSERT INTO contacts (user_id, contact_id) 
                VALUES 
                ((SELECT id FROM users WHERE username = ?), (SELECT id FROM users WHERE username = ?)),
                ((SELECT id FROM users WHERE username = ?), (SELECT id FROM users WHERE username = ?))
                """, 
                (user, contact, contact, user)
            )
            conn.commit()
            return jsonify({"status": "success", "message": "Contact added successfully"})
        else:
            return jsonify({"status": "error", "message": "Contact not found"}), 404


@app.route('/register', methods=['POST'])
def register_user():
    data = request.get_json()
    username, password = data.get('username'), data.get('password')
    
    if not username or not password:
        return jsonify({'status': 'error', 'message': 'Username and password required'}), 400

    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM users WHERE username = ?', (username,))
        if cursor.fetchone():
            return jsonify({'status': 'error', 'message': 'Username already exists'}), 409

        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                       (username, generate_password_hash(password)))
        conn.commit()
    
    return jsonify({'status': 'success', 'message': 'User registered successfully'})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username, password = data.get('username'), data.get('password')
    
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password'], password):
            session['username'] = username
            return jsonify({"status": "success", "message": "User logged in successfully"})
        
    return jsonify({"status": "error", "message": "Invalid username or password"}), 401

@app.route('/logout', methods=['GET'])
def logout():
    session.pop('username', None)
    return redirect(url_for('login_page'))

@app.route('/main', methods=['GET'])
def main():
    if 'username' in session:
        return render_template('home.html', username=session['username'])
    return redirect(url_for('login_page'))

@app.route('/login_page', methods=['GET'])
def login_page():
    return render_template('login.html')

@app.route('/', methods=['GET'])
def home():
    create_tables()
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)