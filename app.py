from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime 

app = Flask(__name__)

# Secret key for session management
app.config['SECRET_KEY'] = 'your_secret_key'

# Database setup (SQLite in this case)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define the User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    first_name = db.Column(db.String(150), nullable=False)
    last_name = db.Column(db.String(150), nullable=False)
    password = db.Column(db.String(150), nullable=False)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event = db.Column(db.String(100), nullable=False)
    user = db.Column(db.String(100), nullable=False)
    time = db.Column(db.DateTime, nullable=False)

    
# Create the database tables within an app context
with app.app_context():
    db.create_all()

data_value = "20"
pumpstate = "OFF"
autopilot = "ON"

@app.route('/fetchdata', methods=['GET'])
def get_data():
    return str(data_value)


@app.route('/data', methods=['GET'])
def send_data():
    global data_value
    value = request.args.get('value')
    
    if value:
        data_value = value
        return pumpstate + "," + autopilot
    else:
        return "No value provided", 400

@app.route('/status', methods=['GET'])
def send_status():
    global pumpstate
    global autopilot
    return pumpstate + "," + autopilot
    

@app.route('/autopilot', methods=['GET'])
def autopilot_state():
    global autopilot
    value = request.args.get('state')
    
    if value:
        autopilot = value
        return "success"
    else:
        return "No value provided", 400

@app.route('/pump', methods=['GET'])
def pump_state():
    global pumpstate
    global autopilot

    #Retrieve event details from get request
    value = request.args.get('state')
    current_user = request.args.get('user') 
    event_name = value  
    current_time = datetime.now()
    #Create new event  
    new_event = Event(event=event_name, user=current_user, time=current_time)
    db.session.add(new_event)
    db.session.commit()

    #Update status of the system
    if value:
        pumpstate = value
        if (current_user != "autopilot"):
            autopilot = "OFF"
        return "success"
    else:
        return "No value provided", 400

@app.route('/manageusers')
def admin_users():
    if 'user_id' not in session:
        flash('You must be an admin to access this page.', 'danger')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    users = User.query.all()
    return render_template('admin_users.html', users=users, user=user)

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash('You need to log in first!', 'warning')
        return redirect(url_for('login'))
    
    # Fetch user information from session
    user = User.query.get(session['user_id'])
    
    return render_template('profile.html', user=user)

@app.route('/readings')
def readings():
    if 'user_id' not in session:
        flash('You need to log in first!', 'warning')
        return redirect(url_for('login'))
    
    # Fetch user information from session
    user = User.query.get(session['user_id'])
    events = Event.query.order_by(Event.id.desc()).all()
    # Format the event data for HTML
    event_list = []
    for event in events:
        event_list.append({
            'event': event.event,
            'user': event.user,
            'time': event.time.strftime('%Y-%m-%d %H:%M:%S'),
        })

    return render_template('readings.html', user=user, events=event_list)


@app.route('/update_profile', methods=['POST'])
def update_profile():
    data = request.get_json()
    user = User.query.get(session['user_id'])
    if user:
        user.username = data['username']
        user.email = data['email']
        user.first_name = data['first_name']
        user.last_name = data['last_name']
        user.password = data['password'] #consider hashing password
        db.session.commit()
        return jsonify({'success': True})
    else:
        return jsonify({'success': False})

@app.route('/update_user', methods=['POST'])
def update_user():
    
    data = request.get_json()
    user = User.query.get(data['userId'])
    if user:
        user.role = data['role']
        if data['password']:
            user.password = data['password']
        db.session.commit()
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'User not found'})

# Home route
@app.route('/')
def home():
    if 'user_id' not in session:
        flash('You need to log in first!', 'warning')
        return redirect(url_for('login'))
    
    # Fetch user information from session
    user = User.query.get(session['user_id'])
    checkbox_state = True
    global pumpstate
    global autopilot
    if autopilot == "OFF":
        checkbox_state = False
    
    return render_template('home.html', user=user, checkbox_state=checkbox_state, pump_state=pumpstate)

# Signup route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        phone = request.form['phone']
        role = request.form['role']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        password = request.form['password']
        
        # Check if the username or email already exists
        user_exists = User.query.filter((User.username == username) | (User.email == email)).first()
        if user_exists:
            flash('Username or email already exists!', 'danger')
            return redirect(url_for('signup'))

        # Hash the password before storing
        
        # Add user to the database
        new_user = User(username=username, email=email, phone=phone, role=role, 
                        first_name=first_name, last_name=last_name, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created successfully!', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.password == password:
            flash('Login successful!', 'success')
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))
    
    return render_template('login.html')
# Logout route
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash('You have been logged out!', 'info')
    return redirect(url_for('login'))
    
if __name__ == '__main__':
    app.run(debug=True)
