import os
import json
import re
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
# Use PostgreSQL if available (Production), else fallback to local SQLite (Development)
db_url = os.environ.get('DATABASE_URL', 'sqlite:///cgpa_calculator.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'super-secret-key')

db = SQLAlchemy(app)

# --- DATABASE MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    register_number = db.Column(db.String(20), unique=True, nullable=False) # Changed from username
    name = db.Column(db.String(100), nullable=False) # Added Name
    password_hash = db.Column(db.String(200), nullable=False) # Stores the hashed PIN
    data = db.relationship('StudentData', backref='user', uselist=False)

class StudentData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    calculator_data = db.Column(db.Text, nullable=False)

# --- ROUTES ---

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    reg_no = data.get('register_number', '').strip().upper()
    name = data.get('name', '').strip()
    pin = data.get('pin')

    # Basic Validation
    if not reg_no or not name or not pin:
        return jsonify({"success": False, "message": "All fields are required"}), 400
    
    # Optional: Check format (Example: 6108...)
    # if not reg_no.startswith("6108"): 
    #     return jsonify({"success": False, "message": "Invalid Register Number format"}), 400

    if User.query.filter_by(register_number=reg_no).first():
        return jsonify({"success": False, "message": "Register Number already registered"}), 400

    hashed_pin = generate_password_hash(pin)
    new_user = User(register_number=reg_no, name=name, password_hash=hashed_pin)
    
    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"success": True, "userId": new_user.id, "name": new_user.name, "register_number": new_user.register_number})
    except Exception as e:
        return jsonify({"success": False, "message": "Server Error"}), 500

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    reg_no = data.get('register_number', '').strip().upper()
    pin = data.get('pin')

    user = User.query.filter_by(register_number=reg_no).first()

    if user and check_password_hash(user.password_hash, pin):
        return jsonify({"success": True, "userId": user.id, "name": user.name, "register_number": user.register_number})
    
    return jsonify({"success": False, "message": "Invalid Register Number or PIN"}), 401

@app.route('/save', methods=['POST'])
def save_data():
    req = request.json
    user_id = req.get('userId')
    new_data = json.dumps(req.get('data'))

    record = StudentData.query.filter_by(user_id=user_id).first()
    
    if record:
        record.calculator_data = new_data
    else:
        new_record = StudentData(user_id=user_id, calculator_data=new_data)
        db.session.add(new_record)
    
    db.session.commit()
    return jsonify({"success": True})

@app.route('/load/<int:user_id>', methods=['GET'])
def load_data(user_id):
    record = StudentData.query.filter_by(user_id=user_id).first()
    if record:
        return jsonify({"success": True, "data": json.loads(record.calculator_data)})
    return jsonify({"success": False, "message": "No data found"})

# --- INIT DB ---
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=5000)