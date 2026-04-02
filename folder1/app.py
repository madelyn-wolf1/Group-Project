from flask import Flask, render_template, request, redirect, session, flash, jsonify, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime, date, time
from sqlalchemy import and_, or_, func
import ipaddress
from flask_bootstrap5 import Bootstrap

app = Flask(__name__)

# Configuration
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:password123@localhost/stock_trading"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = 'your-secret-key-here'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
bootstrap = Bootstrap(app)

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
    
    def __repr__(self):
        return f'<User {self.Email}>'

class Account(db.Model):
    __tablename__ = 'accounts'
    
    AcctID = db.Column(db.Integer, primary_key=True)
    UserID = db.Column(db.Integer, db.ForeignKey('users.UserID'), unique=True, nullable=False)
    CashBalance = db.Column(db.Float, default=0.0)
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow)
    UpdatedAt = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
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

#Seed Stock
@app.before_request
def seed_stock():
    if not Stock.query.first():
        test_stock = Stock(
            Tiker='TSLA',
            CompanyName='Tesla Inc.',
            CurrentPrice=150.00,
            OpeningPrice=145.00,
            TotalVolume=1000000,
            ActiveStatus=True,
        )
        db.session.add(test_stock)
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
            session['user_id'] = user.UserID
            session['is_admin'] = user.Admin
            
            user.LastLogin = datetime.utcnow()
            db.session.commit()
            
            log_audit('USER_LOGIN', user.UserID, 'User logged in')
            if user.Admin:
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('dashboard'))
        
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

    if user is None:
        session.clear()
        flash("Your session is invalid. Please log in again.")
        return redirect('/login')

    account = Account.query.filter_by(UserID=user.UserID).first()

    if account is None:
        flash("No account found for this user.")
        return redirect('/login')
    
    # Get recent transactions
    recent_transactions = CashTransaction.query.filter_by(AcctID=account.AcctID)\
        .order_by(CashTransaction.Timestamp.desc()).limit(5).all()
    
    # Get holdings w stock info
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

    
    total_stock_value = sum(h['value'] for h in holdings_data)
    net_worth = account.CashBalance + total_stock_value

    return render_template(
        'dashboard.html',
        user=user,
        account=account,
        holdings=holdings_data,
        transactions=recent_transactions,
        net_worth=net_worth
    )

@app.route('/cash-management')
def cash_management():
    if 'user_id' not in session:
        return redirect('/login')

    account = Account.query.filter_by(UserID=session['user_id']).first()

    if not account:
        flash("Account not found")
        return redirect('/dashboard')

    return render_template('cash_management.html', balance=account.CashBalance)

@app.route('/deposit', methods=['POST'])
def deposit():
    if 'user_id' not in session:
        return redirect('/login')

    account = Account.query.filter_by(UserID=session['user_id']).first()

    if not account:
        flash("Account not found")
        return redirect('/dashboard')

    try:
        amount = float(request.form.get('amount', 0))
    except:
        flash("Invalid amount")
        return redirect('/cash-management')

    if amount <= 0:
        flash("Amount must be greater than 0")
        return redirect('/cash-management')

    account.CashBalance += amount

    db.session.add(CashTransaction(
        AcctID=account.AcctID,
        TransactionType='DEPOSIT',
        Amount=amount
    ))

    db.session.commit()

    flash("Deposit successful")
    return redirect('/cash-management')

@app.route('/withdraw', methods=['POST'])
def withdraw():
    if 'user_id' not in session:
        return redirect('/login')

    account = Account.query.filter_by(UserID=session['user_id']).first()

    if not account:
        flash("Account not found")
        return redirect('/dashboard')

    try:
        amount = float(request.form.get('amount', 0))
    except:
        flash("Invalid amount")
        return redirect('/cash-management')

    confirm = request.form.get('confirm')

    if confirm != 'yes':
        flash("Withdrawal cancelled")
        return redirect('/cash-management')

    if amount <= 0:
        flash("Amount must be greater than 0")
        return redirect('/cash-management')

    if account.CashBalance < amount:
        flash("Not enough balance")
        return redirect('/cash-management')

    account.CashBalance -= amount

    db.session.add(CashTransaction(
        AcctID=account.AcctID,
        TransactionType='WITHDRAWAL',
        Amount=amount
    ))

    db.session.commit()

    flash("Withdrawal successful")
    return redirect('/cash-management')

@app.route('/transactions')
def transactions():
    return "Transactions coming soon"

@app.route('/portfolio')
def portfolio():
    return "Portfolio coming soon"

@app.route('/stocks')
def stocks():
    if 'user_id' not in session:
        return redirect('/login')

    q = (request.args.get('q') or '').strip()

    query = Stock.query.filter_by(ActiveStatus=True)

    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Stock.Ticker.ilike(like),
                Stock.CompanyName.ilike(like)
            )
        )

    stocks_list = query.order_by(Stock.Ticker.asc()).all()

    market_open = True

    return render_template(
        'stock_search.html',
        stocks=stocks_list,
        market_open=market_open
    )


@app.route('/stocks/<string:ticker>')
def stock_detail(ticker):
    if 'user_id' not in session:
        return redirect('/login')

    stock = Stock.query.filter_by(
        Ticker=ticker.upper(),
        ActiveStatus=True
    ).first_or_404()

    account = Account.query.filter_by(UserID=session['user_id']).first()
    holding = Holding.query.filter_by(
        UserID=session['user_id'],
        StockID=stock.StockID
    ).first()

    cash_balance = account.CashBalance if account else 0.0
    owned_shares = holding.Shares if holding else 0

    return render_template(
        'stock_detail.html',
        stock=stock,
        owned_shares=owned_shares,
        cash_balance=cash_balance
    )


@app.route('/trade/<string:ticker>', methods=['GET', 'POST'])
def trade(ticker):
    if 'user_id' not in session:
        return redirect('/login')

    stock = Stock.query.filter_by(
        Ticker=ticker.upper(),
        ActiveStatus=True
    ).first_or_404()

    account = Account.query.filter_by(UserID=session['user_id']).first()
    if not account:
        flash("Account not found")
        return redirect('/dashboard')

    holding = Holding.query.filter_by(
        UserID=session['user_id'],
        StockID=stock.StockID
    ).first()

    owned_shares = holding.Shares if holding else 0
    cash_balance = account.CashBalance
    market_open = True

    if request.method == 'POST':
        order_type = (request.form.get('order_type') or '').strip().upper()

        try:
            quantity = int(request.form.get('quantity', 0))
        except ValueError:
            quantity = 0

        if order_type not in ['BUY', 'SELL']:
            flash("Invalid order type")
            return redirect(url_for('trade', ticker=stock.Ticker))

        if quantity <= 0:
            flash("Quantity must be at least 1")
            return redirect(url_for('trade', ticker=stock.Ticker))

        order_price = stock.CurrentPrice
        total_amount = quantity * order_price

        if market_open:
            if order_type == 'BUY':
                if account.CashBalance < total_amount:
                    flash("Not enough cash")
                    return redirect(url_for('trade', ticker=stock.Ticker))

                account.CashBalance -= total_amount

                if not holding:
                    holding = Holding(
                        UserID=session['user_id'],
                        StockID=stock.StockID,
                        Shares=0
                    )
                    db.session.add(holding)

                holding.Shares += quantity

                order = Order(
                    UserID=session['user_id'],
                    StockID=stock.StockID,
                    OrderType='BUY',
                    Quantity=quantity,
                    OrderPrice=order_price,
                    Status='executed',
                    PlacedAt=datetime.utcnow(),
                    ExecutedAt=datetime.utcnow()
                )
                db.session.add(order)
                db.session.flush()

                trade_row = Trade(
                    OrderID=order.OrderID,
                    TradeType='BUY',
                    Quantity=quantity,
                    ExecutionPrice=order_price,
                    Amount=total_amount,
                    ExecutedAt=datetime.utcnow()
                )
                db.session.add(trade_row)
                db.session.flush()

                db.session.add(CashTransaction(
                    AcctID=account.AcctID,
                    TradeID=trade_row.TradeID,
                    TransactionType='TRADE_BUY',
                    Amount=total_amount
                ))

                db.session.commit()
                flash("Buy order executed successfully")
                return redirect(url_for('stock_detail', ticker=stock.Ticker))

            else:
                if owned_shares < quantity:
                    flash("Not enough shares")
                    return redirect(url_for('trade', ticker=stock.Ticker))

                account.CashBalance += total_amount
                holding.Shares -= quantity

                order = Order(
                    UserID=session['user_id'],
                    StockID=stock.StockID,
                    OrderType='SELL',
                    Quantity=quantity,
                    OrderPrice=order_price,
                    Status='executed',
                    PlacedAt=datetime.utcnow(),
                    ExecutedAt=datetime.utcnow()
                )
                db.session.add(order)
                db.session.flush()

                trade_row = Trade(
                    OrderID=order.OrderID,
                    TradeType='SELL',
                    Quantity=quantity,
                    ExecutionPrice=order_price,
                    Amount=total_amount,
                    ExecutedAt=datetime.utcnow()
                )
                db.session.add(trade_row)
                db.session.flush()

                db.session.add(CashTransaction(
                    AcctID=account.AcctID,
                    TradeID=trade_row.TradeID,
                    TransactionType='TRADE_SELL',
                    Amount=total_amount
                ))

                db.session.commit()
                flash("Sell order executed successfully")
                return redirect(url_for('stock_detail', ticker=stock.Ticker))

        else:
            if order_type == 'BUY' and account.CashBalance < total_amount:
                flash("Not enough cash to place this future buy order")
                return redirect(url_for('trade', ticker=stock.Ticker))

            if order_type == 'SELL' and owned_shares < quantity:
                flash("Not enough shares to place this future sell order")
                return redirect(url_for('trade', ticker=stock.Ticker))

            order = Order(
                UserID=session['user_id'],
                StockID=stock.StockID,
                OrderType=order_type,
                Quantity=quantity,
                OrderPrice=order_price,
                Status='pending',
                PlacedAt=datetime.utcnow(),
                EligibleAt=datetime.utcnow()
            )
            db.session.add(order)
            db.session.commit()

            flash("Market is closed. Order placed as pending.")
            return redirect(url_for('stock_detail', ticker=stock.Ticker))

    return render_template(
        'sell.html',
        stock=stock,
        cash_balance=cash_balance,
        owned_shares=owned_shares,
        market_open=market_open
    )

# Administrator routes
@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('user_id') or not session.get('is_admin'):
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))

    total_stocks = Stock.query.count()
    active_stocks = Stock.query.filter_by(ActiveStatus=True).count()
    holiday_count = MarketHoliday.query.count()
    recent_stocks = Stock.query.order_by(Stock.CreatedAt.desc()).limit(5).all()
    recent_logs = AuditLog.query.order_by(AuditLog.EventTime.desc()).limit(5).all()

    market_config = MarketConfig.query.first()
    market_open = True

    return render_template(
        'admin/admin_dashboard.html',
        total_stocks=total_stocks,
        active_stocks=active_stocks,
        holiday_count=holiday_count,
        recent_stocks=recent_stocks,
        recent_logs=recent_logs,
        market_open=market_open
    )

@app.route('/admin/stocks')
def admin_stocks():
    if not session.get('user_id') or not session.get('is_admin'):
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))

    stocks = Stock.query.all()
    return render_template('admin/admin_stocks.html', stocks=stocks)

@app.route('/admin/stocks/add', methods=['POST'])
def add_stock():
    if not session.get('user_id') or not session.get('is_admin'):
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))

    stock = Stock(
        CompanyName=request.form['company_name'],
        Ticker=request.form['ticker'].upper(),
        TotalVolume=int(request.form['total_volume']),
        OpeningPrice=float(request.form['opening_price']),
        CurrentPrice=float(request.form['opening_price']),
        ActiveStatus=True,
        AdminID=session['user_id']
    )

    db.session.add(stock)
    db.session.commit()
    flash('Stock added successfully.', 'success')
    return redirect(url_for('admin_stocks'))

@app.route('/admin/stocks/edit/<int:stock_id>', methods=['GET', 'POST'])
def edit_stock(stock_id):
    if not session.get('user_id') or not session.get('is_admin'):
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))

    stock = Stock.query.get_or_404(stock_id)

    if request.method == 'POST':
        stock.CompanyName = request.form['company_name']
        stock.Ticker = request.form['ticker'].upper()
        stock.TotalVolume = int(request.form['total_volume'])
        stock.CurrentPrice = float(request.form['current_price'])
        stock.ActiveStatus = bool(int(request.form['active_status']))

        db.session.commit()
        flash('Stock updated successfully.', 'success')
        return redirect(url_for('admin_stocks'))

    return render_template('admin/edit_stock.html', stock=stock)

@app.route('/admin/stocks/delete/<int:stock_id>', methods=['POST'])
def delete_stock(stock_id):
    if not session.get('user_id') or not session.get('is_admin'):
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))

    stock = Stock.query.get_or_404(stock_id)
    db.session.delete(stock)
    db.session.commit()

    flash('Stock deleted successfully.', 'success')
    return redirect(url_for('admin_stocks'))


if __name__ == '__main__':
    app.run(debug=True)