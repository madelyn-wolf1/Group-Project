from flask import Flask, render_template, request, redirect, session, flash
from models import db, User, CashAccount, Transaction, bcrypt
from datetime import datetime 

app = Flask(__name__)

# Configuration
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///stock_trader.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = 'your-secret-key-here'

db.init_app(app)
bcrypt.init_app(app)

with app.app_context():
    db.create_all() 

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect('/dashboard')
    return redirect('/login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if not all([full_name, username, email, password]):
            return "All fields are required"
            
        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            return "Username or Email already exists"

        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')

        new_user = User(full_name=full_name, username=username, email=email, password_hash=hashed_pw)
        db.session.add(new_user)
        db.session.commit()

        cash_account = CashAccount(user_id=new_user.id, balance=0.0)
        db.session.add(cash_account)
        db.session.commit()
        
        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            return redirect('/dashboard')
        return "Invalid credentials"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    
    user = User.query.get(session['user_id'])
    balance = user.cash_account.balance
    return render_template('dashboard.html', full_name=user.full_name, balance=balance)


@app.route('/withdraw', methods=['GET', 'POST'])
def withdraw():
    if 'user_id' not in session:
        flash("Please login first")
        return redirect('/login')

    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        try:
            amount = float(request.form['amount'])
            confirm = request.form.get('confirm')

            if amount <= 0:
                flash("Amount must be greater than 0")
                return redirect('/withdraw')

            if amount > user.cash_account.balance:
                flash("Insufficient funds")
                return redirect('/withdraw')

            if confirm != 'yes':
                flash("Withdrawal cancelled")
                return redirect('/withdraw')

            user.cash_account.balance -= amount

            transaction = Transaction(
                user_id=user.id,
                type='WITHDRAW',
                amount=amount
            )
            db.session.add(transaction)
            db.session.commit()

            flash(f"Successfully withdrew ${amount:.2f}")
            return redirect('/dashboard')

        except ValueError:
            flash("Invalid amount")
            return redirect('/withdraw')

    return render_template('cash_management.html', action='withdraw', balance=user.cash_account.balance)