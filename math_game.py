from flask import Flask, jsonify, request, session, render_template
import random
from collections import defaultdict

app = Flask(__name__)
app.secret_key = "math_game"

# In-memory data storage
users = {}
stat = defaultdict(lambda: {'questions': [], 'correct': 0, 'wrong': 0})

# Routes
@app.route('/')
def home():
    """Render the login page"""
    return render_template('login.html')

@app.route('/register_page')
def register_page():
    """Render the registration page"""
    return render_template("register.html")

@app.route('/main')
def main():
    """Render the main page (math game page)"""
    if 'username' not in session:
        return jsonify({"status": "error", "message": "Please login first."}), 401
    return render_template("math_index.html")

@app.route('/register', methods=['POST'])
def register():
    """Handle user registration"""
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if username in users:
        return jsonify({'status': 'error', "message": "User already exists"}), 400

    users[username] = password
    return jsonify({'status': 'success', "message": "User created successfully"}), 201

@app.route('/login', methods=['POST'])
def login():
    """Handle user login"""
    data = request.json
    username = data.get('username')

    if username not in users:
        return jsonify({"status": 'error', 'message': 'User does not exist'}), 404

    session['username'] = username
    return jsonify({'status': 'success', 'message': 'Login successful'}), 200

@app.route('/get_question', methods=['GET'])
def get_question():
    """Generate and return a random math question"""
    x = random.randint(1, 100)
    y = random.randint(1, 100)
    signs = ['+', '-', '*']
    sign = random.choice(signs)
    answer = eval(f"{x}{sign}{y}")
    
    session["last_question"] = {'question': f"{x} {sign} {y}=?", 'answer': answer}
    return jsonify({'question': f"{x} {sign} {y}=?", 'answer': answer})

@app.route('/check', methods=['POST'])
def check():
    """Check if the provided answer is correct and update stats"""
    data = request.json
    username = session.get('username')
    
    if not username:
        return jsonify({"status": "error", "message": "Please login first."}), 401
    
    answer = data.get('correct')
    last_question = session.get("last_question")
    
    if not last_question:
        return jsonify({"status": "error", "message": "No question found."}), 400
    
    question = last_question['question']
    
    if answer == 1:
        stat[username]["questions"].append(question)
        stat[username]['correct'] += 1
    else:
        stat[username]['wrong'] += 1
    
    return jsonify({'message': 'Answer submitted successfully'}), 200

@app.route('/get_stat', methods=['GET'])
def get_stat():
    """Get the statistics for the current logged-in user"""
    username = session.get('username')

    if not username:
        return jsonify({"status": "error", "message": "Please login first."}), 401
    
    user_stat = stat[username]
    return jsonify({
        'username': username,
        'questions_answered': len(user_stat['questions']),
        'correct': user_stat['correct'],
        'wrong': user_stat['wrong']
    }), 200

@app.route('/test')
def test():
    """Test route to check the users and stats"""
    return jsonify(users=users, stats=stat)

if __name__ == '__main__':
    app.run(debug=True)
