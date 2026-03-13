from flask import Flask, render_template, request, redirect, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime, date, time
from sqlalchemy import and_, or_, func
import ipaddress

app = Flask(__name__)

# Configuration
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///stock_trader.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = 'your-secret-key-here'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# Models
class User(db.Model):
    __tablename__ = 'users'
    
    UserID = db.Column(db.Integer, primary_key=True)
    FirstName = db.Column(db.String(50), nullable=False)
    LastName = db.Column(db.String(50), nullable=False)
    Email = db.Column(db.String(120), unique=True, nullable=False)
    Admin = db.Column(db.Boolean, default=False)
    Status = db.Column(db.String(20), default='active')
    HashPassword = db.Column(db.String(128), nullable=False)
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow)
    LastLogin = db.Column(db.DateTime)
    
    # Relationships
    account = db.relationship('Account', backref='user', uselist=False)
    orders = db.relationship('Order', backref='user', lazy='dynamic')
    holdings = db.relationship('Holding', backref='user', lazy='dynamic')
    audit_logs = db.relationship('AuditLog', backref='user', lazy='dynamic')
    
    # Admin managed entities
    managed_stocks = db.relationship('Stock', backref='admin', lazy='dynamic', 
                                   foreign_keys='Stock.AdminID')
    managed_configs = db.relationship('MarketConfig', backref='admin', lazy='dynamic',
                                    foreign_keys='MarketConfig.AdminID')
    managed_holidays = db.relationship('MarketHoliday', backref='admin', lazy='dynamic',
                                     foreign_keys='MarketHoliday.AdminID')
    
    @property
    def full_name(self):
        return f"{self.FirstName} {self.LastName}"
    
    def __repr__(self):
        return f'<User {self.Email}>'

class Account(db.Model):
    __tablename__ = 'accounts'
    
    AcctID = db.Column(db.Integer, primary_key=True)
    UserID = db.Column(db.Integer, db.ForeignKey('users.UserID'), unique=True, nullable=False)
    CashBalance = db.Column(db.Float, default=0.0)
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow)
    UpdatedAt = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    cash_transactions = db.relationship('CashTransaction', backref='account', lazy='dynamic')
    
    def __repr__(self):
        return f'<Account {self.AcctID}: ${self.CashBalance}>'

class CashTransaction(db.Model):
    __tablename__ = 'cash_transactions'
    
    TransactionID = db.Column(db.Integer, primary_key=True)
    AcctID = db.Column(db.Integer, db.ForeignKey('accounts.AcctID'), nullable=False)
    TradeID = db.Column(db.Integer, db.ForeignKey('trades.TradeID'), nullable=True)
    TransactionType = db.Column(db.String(20), nullable=False)  # DEPOSIT, WITHDRAWAL, TRADE_BUY, TRADE_SELL
    Amount = db.Column(db.Float, nullable=False)
    Timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<CashTransaction {self.TransactionType}: ${self.Amount}>'

class Stock(db.Model):
    __tablename__ = 'stocks'
    
    StockID = db.Column(db.Integer, primary_key=True)
    AdminID = db.Column(db.Integer, db.ForeignKey('users.UserID'), nullable=False)
    CompanyName = db.Column(db.String(100), nullable=False)
    Ticker = db.Column(db.String(10), unique=True, nullable=False)
    TotalVolume = db.Column(db.Integer, default=0)
    OpeningPrice = db.Column(db.Float, nullable=False)
    CurrentPrice = db.Column(db.Float, nullable=False)
    ActiveStatus = db.Column(db.Boolean, default=True)
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow)
    UpdatedAt = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    price_history = db.relationship('PriceHistory', backref='stock', lazy='dynamic')
    orders = db.relationship('Order', backref='stock', lazy='dynamic')
    holdings = db.relationship('Holding', backref='stock', lazy='dynamic')
    
    def __repr__(self):
        return f'<Stock {self.Ticker}: ${self.CurrentPrice}>'

class PriceHistory(db.Model):
    __tablename__ = 'price_history'
    
    HistoryID = db.Column(db.Integer, primary_key=True)
    StockID = db.Column(db.Integer, db.ForeignKey('stocks.StockID'), nullable=False)
    Price = db.Column(db.Float, nullable=False)
    RecordedAt = db.Column(db.DateTime, default=datetime.utcnow)
    TradingDate = db.Column(db.Date, default=date.today)
    
    def __repr__(self):
        return f'<PriceHistory {self.StockID}: ${self.Price} on {self.TradingDate}>'

class Order(db.Model):
    __tablename__ = 'orders'
    
    OrderID = db.Column(db.Integer, primary_key=True)
    UserID = db.Column(db.Integer, db.ForeignKey('users.UserID'), nullable=False)
    StockID = db.Column(db.Integer, db.ForeignKey('stocks.StockID'), nullable=False)
    OrderType = db.Column(db.String(10), nullable=False)  # BUY, SELL
    Quantity = db.Column(db.Integer, nullable=False)
    OrderPrice = db.Column(db.Float, nullable=False)
    Status = db.Column(db.String(20), default='pending')  # pending, eligible, cancelled, executed, rejected
    PlacedAt = db.Column(db.DateTime, default=datetime.utcnow)
    EligibleAt = db.Column(db.DateTime)
    CancelledAt = db.Column(db.DateTime)
    ExecutedAt = db.Column(db.DateTime)
    RejectedReason = db.Column(db.String(200))
    
    # Relationships
    trade = db.relationship('Trade', backref='order', uselist=False)
    
    def __repr__(self):
        return f'<Order {self.OrderID}: {self.OrderType} {self.Quantity} @ ${self.OrderPrice}>'

class Trade(db.Model):
    __tablename__ = 'trades'
    
    TradeID = db.Column(db.Integer, primary_key=True)
    OrderID = db.Column(db.Integer, db.ForeignKey('orders.OrderID'), unique=True, nullable=False)
    TradeType = db.Column(db.String(10), nullable=False)  # BUY, SELL
    Quantity = db.Column(db.Integer, nullable=False)
    ExecutionPrice = db.Column(db.Float, nullable=False)
    Amount = db.Column(db.Float, nullable=False)
    ExecutedAt = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    cash_transaction = db.relationship('CashTransaction', backref='trade', uselist=False)
    
    def __repr__(self):
        return f'<Trade {self.TradeID}: ${self.Amount}>'

class Holding(db.Model):
    __tablename__ = 'holdings'
    
    HoldingID = db.Column(db.Integer, primary_key=True)
    UserID = db.Column(db.Integer, db.ForeignKey('users.UserID'), nullable=False)
    StockID = db.Column(db.Integer, db.ForeignKey('stocks.StockID'), nullable=False)
    Shares = db.Column(db.Integer, default=0)
    UpdatedAt = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('UserID', 'StockID', name='unique_user_stock'),)
    
    def __repr__(self):
        return f'<Holding {self.UserID}-{self.StockID}: {self.Shares} shares>'

class MarketConfig(db.Model):
    __tablename__ = 'market_config'
    
    MarketConfigID = db.Column(db.Integer, primary_key=True)
    AdminID = db.Column(db.Integer, db.ForeignKey('users.UserID'), nullable=False)
    OpenTime = db.Column(db.Time, nullable=False)
    CloseTime = db.Column(db.Time, nullable=False)
    TimeZone = db.Column(db.String(50), default='UTC')
    WeekdaysOnly = db.Column(db.Boolean, default=True)
    UpdatedAt = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<MarketConfig: {self.OpenTime}-{self.CloseTime}>'

class MarketHoliday(db.Model):
    __tablename__ = 'market_holidays'
    
    HolidayID = db.Column(db.Integer, primary_key=True)
    AdminID = db.Column(db.Integer, db.ForeignKey('users.UserID'), nullable=False)
    HolidayDate = db.Column(db.Date, unique=True, nullable=False)
    HolidayName = db.Column(db.String(100), nullable=False)
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<MarketHoliday: {self.HolidayName} on {self.HolidayDate}>'

class AuditLog(db.Model):
    __tablename__ = 'audit_log'
    
    AuditID = db.Column(db.Integer, primary_key=True)
    UserID = db.Column(db.Integer, db.ForeignKey('users.UserID'), nullable=True)
    EventType = db.Column(db.String(50), nullable=False)
    EventTime = db.Column(db.DateTime, default=datetime.utcnow)
    IPAddress = db.Column(db.String(45))  # IPv6 compatible
    ClientInfo = db.Column(db.String(200))
    Details = db.Column(db.Text)
    
    def __repr__(self):
        return f'<AuditLog: {self.EventType} at {self.EventTime}>'

# Create tables
with app.app_context():
    db.create_all()
    
    # Create default admin if not exists
    if not User.query.filter_by(Email='admin@stocktrader.com').first():
        admin = User(
            FirstName='Admin',
            LastName='User',
            Email='admin@stocktrader.com',
            Admin=True,
            Status='active',
            HashPassword=bcrypt.generate_password_hash('admin123').decode('utf-8')
        )
        db.session.add(admin)
        db.session.commit()
        
        # Create default market config
        config = MarketConfig(
            AdminID=admin.UserID,
            OpenTime=time(9, 30),
            CloseTime=time(16, 0),
            TimeZone='America/New_York',
            WeekdaysOnly=True
        )
        db.session.add(config)
        db.session.commit()

# Helper function to log audit events
def log_audit(event_type, user_id=None, details=None):
    audit = AuditLog(
        UserID=user_id,
        EventType=event_type,
        IPAddress=request.remote_addr,
        ClientInfo=request.user_agent.string,
        Details=details
    )
    db.session.add(audit)
    db.session.commit()

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect('/dashboard')
    return redirect('/login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not all([first_name, last_name, email, password]):
            flash("All fields are required")
            return redirect('/register')
            
        if User.query.filter_by(Email=email).first():
            flash("Email already exists")
            return redirect('/register')

        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')

        new_user = User(
            FirstName=first_name,
            LastName=last_name,
            Email=email,
            HashPassword=hashed_pw,
            Status='active'
        )
        db.session.add(new_user)
        db.session.commit()

        # Create cash account
        cash_account = Account(
            UserID=new_user.UserID,
            CashBalance=0.0
        )
        db.session.add(cash_account)
        db.session.commit()
        
        log_audit('USER_REGISTERED', new_user.UserID, f'New user registered: {email}')
        flash("Registration successful! Please login.")
        return redirect('/login')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(Email=email).first()
        if user and bcrypt.check_password_hash(user.HashPassword, password):
            if user.Status != 'active':
                flash("Account is not active")
                return redirect('/login')
                
            session['user_id'] = user.UserID
            session['is_admin'] = user.Admin
            
            user.LastLogin = datetime.utcnow()
            db.session.commit()
            
            log_audit('USER_LOGIN', user.UserID, 'User logged in')
            return redirect('/dashboard')
        
        flash("Invalid credentials")
        return redirect('/login')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    if 'user_id' in session:
        log_audit('USER_LOGOUT', session['user_id'], 'User logged out')
    session.clear()
    flash("You have been logged out")
    return redirect('/login')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    
    user = User.query.get(session['user_id'])
    account = Account.query.filter_by(UserID=user.UserID).first()
    
    # Get recent transactions
    recent_transactions = CashTransaction.query.filter_by(AcctID=account.AcctID)\
        .order_by(CashTransaction.Timestamp.desc()).limit(5).all()
    
    # Get holdings with stock info
    holdings = Holding.query.filter_by(UserID=user.UserID).all()
    holdings_data = []
    for holding in holdings:
        stock = Stock.query.get(holding.StockID)
        if stock and holding.Shares > 0:
            holdings_data.append({
                'ticker': stock.Ticker,
                'company': stock.CompanyName,
                'shares': holding.Shares,
                'current_price': stock.CurrentPrice,
                'value': holding.Shares * stock.CurrentPrice
            })
    
    return render_template('dashboard.html', 
                         user=user, 
                         account=account,
                         holdings=holdings_data,
                         transactions=recent_transactions)

@app.route('/deposit', methods=['GET', 'POST'])
def deposit():
    if 'user_id' not in session:
        flash("Please login first")
        return redirect('/login')

    user = User.query.get(session['user_id'])
    account = Account.query.filter_by(UserID=user.UserID).first()

    if request.method == 'POST':
        try:
            amount = float(request.form['amount'])

            if amount <= 0:
                flash("Amount must be greater than 0")
                return redirect('/deposit')

            # Update account balance
            account.CashBalance += amount
            account.UpdatedAt = datetime.utcnow()

            # Create transaction record
            transaction = CashTransaction(
                AcctID=account.AcctID,
                TransactionType='DEPOSIT',
                Amount=amount
            )
            db.session.add(transaction)
            db.session.commit()

            log_audit('DEPOSIT', user.UserID, f'Deposited ${amount:.2f}')
            flash(f"Successfully deposited ${amount:.2f}")
            return redirect('/dashboard')

        except ValueError:
            flash("Invalid amount")
            return redirect('/deposit')

    return render_template('cash_management.html', action='deposit', balance=account.CashBalance)

@app.route('/withdraw', methods=['GET', 'POST'])
def withdraw():
    if 'user_id' not in session:
        flash("Please login first")
        return redirect('/login')

    user = User.query.get(session['user_id'])
    account = Account.query.filter_by(UserID=user.UserID).first()

    if request.method == 'POST':
        try:
            amount = float(request.form['amount'])

            if amount <= 0:
                flash("Amount must be greater than 0")
                return redirect('/withdraw')

            if amount > account.CashBalance:
                flash("Insufficient funds")
                return redirect('/withdraw')

            # Update account balance
            account.CashBalance -= amount
            account.UpdatedAt = datetime.utcnow()

            # Create transaction record
            transaction = CashTransaction(
                AcctID=account.AcctID,
                TransactionType='WITHDRAWAL',
                Amount=amount
            )
            db.session.add(transaction)
            db.session.commit()

            log_audit('WITHDRAWAL', user.UserID, f'Withdrew ${amount:.2f}')
            flash(f"Successfully withdrew ${amount:.2f}")
            return redirect('/dashboard')

        except ValueError:
            flash("Invalid amount")
            return redirect('/withdraw')

    return render_template('cash_management.html', action='withdraw', balance=account.CashBalance)

@app.route('/transactions')
def transactions():
    if 'user_id' not in session:
        return redirect('/login')
    
    user = User.query.get(session['user_id'])
    account = Account.query.filter_by(UserID=user.UserID).first()
    
    page = request.args.get('page', 1, type=int)
    transactions = CashTransaction.query.filter_by(AcctID=account.AcctID)\
        .order_by(CashTransaction.Timestamp.desc())\
        .paginate(page=page, per_page=20)
    
    return render_template('transactions.html', transactions=transactions)

# Admin routes
@app.route('/admin/stocks')
def admin_stocks():
    if 'user_id' not in session or not session.get('is_admin'):
        flash("Admin access required")
        return redirect('/dashboard')
    
    stocks = Stock.query.all()
    return render_template('admin/stocks.html', stocks=stocks)

@app.route('/admin/stock/add', methods=['GET', 'POST'])
def add_stock():
    if 'user_id' not in session or not session.get('is_admin'):
        flash("Admin access required")
        return redirect('/dashboard')
    
    if request.method == 'POST':
        ticker = request.form['ticker'].upper()
        company = request.form['company_name']
        opening_price = float(request.form['opening_price'])
        
        if Stock.query.filter_by(Ticker=ticker).first():
            flash("Stock with this ticker already exists")
            return redirect('/admin/stock/add')
        
        stock = Stock(
            AdminID=session['user_id'],
            CompanyName=company,
            Ticker=ticker,
            OpeningPrice=opening_price,
            CurrentPrice=opening_price,
            TotalVolume=0,
            ActiveStatus=True
        )
        db.session.add(stock)
        db.session.commit()
        
        # Add initial price history
        price_history = PriceHistory(
            StockID=stock.StockID,
            Price=opening_price,
            TradingDate=date.today()
        )
        db.session.add(price_history)
        db.session.commit()
        
        log_audit('STOCK_ADDED', session['user_id'], f'Added stock: {ticker}')
        flash(f"Stock {ticker} added successfully")
        return redirect('/admin/stocks')
    
    return render_template('admin/add_stock.html')

@app.route('/admin/market-config', methods=['GET', 'POST'])
def market_config():
    if 'user_id' not in session or not session.get('is_admin'):
        flash("Admin access required")
        return redirect('/dashboard')
    
    config = MarketConfig.query.first()
    
    if request.method == 'POST':
        if config:
            config.OpenTime = datetime.strptime(request.form['open_time'], '%H:%M').time()
            config.CloseTime = datetime.strptime(request.form['close_time'], '%H:%M').time()
            config.TimeZone = request.form['timezone']
            config.WeekdaysOnly = 'weekdays_only' in request.form
        else:
            config = MarketConfig(
                AdminID=session['user_id'],
                OpenTime=datetime.strptime(request.form['open_time'], '%H:%M').time(),
                CloseTime=datetime.strptime(request.form['close_time'], '%H:%M').time(),
                TimeZone=request.form['timezone'],
                WeekdaysOnly='weekdays_only' in request.form
            )
            db.session.add(config)
        
        db.session.commit()
        log_audit('MARKET_CONFIG_UPDATED', session['user_id'], 'Market configuration updated')
        flash("Market configuration updated")
        return redirect('/admin/market-config')
    
    holidays = MarketHoliday.query.order_by(MarketHoliday.HolidayDate).all()
    return render_template('admin/market_config.html', config=config, holidays=holidays)

@app.route('/admin/holiday/add', methods=['POST'])
def add_holiday():
    if 'user_id' not in session or not session.get('is_admin'):
        flash("Admin access required")
        return redirect('/dashboard')
    
    holiday_date = datetime.strptime(request.form['holiday_date'], '%Y-%m-%d').date()
    holiday_name = request.form['holiday_name']
    
    if MarketHoliday.query.filter_by(HolidayDate=holiday_date).first():
        flash("Holiday already exists for this date")
        return redirect('/admin/market-config')
    
    holiday = MarketHoliday(
        AdminID=session['user_id'],
        HolidayDate=holiday_date,
        HolidayName=holiday_name
    )
    db.session.add(holiday)
    db.session.commit()
    
    log_audit('HOLIDAY_ADDED', session['user_id'], f'Added holiday: {holiday_name} on {holiday_date}')
    flash("Holiday added")
    return redirect('/admin/market-config')

@app.route('/admin/holiday/delete/<int:holiday_id>')
def delete_holiday(holiday_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash("Admin access required")
        return redirect('/dashboard')
    
    holiday = MarketHoliday.query.get_or_404(holiday_id)
    db.session.delete(holiday)
    db.session.commit()
    
    log_audit('HOLIDAY_DELETED', session['user_id'], f'Deleted holiday: {holiday.HolidayName}')
    flash("Holiday deleted")
    return redirect('/admin/market-config')

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect('/login')
    
    user = User.query.get(session['user_id'])
    return render_template('profile.html', user=user)

if __name__ == '__main__':
    app.run(debug=True)