DB_USERNAME = "admin"
DB_PASSWORD = "password123"
DB_HOST = "stock-trading-db.cvcoomom0bf1.us-east-2.rds.amazonaws.com"
DB_PORT = "3306"
DB_NAME = "stock_trading"

SQLALCHEMY_DATABASE_URI = (f"mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
SQLALCHEMY_TRACK_MODIFICATIONS = False
SECRET_KEY = "your-secret-key"
