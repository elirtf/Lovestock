# Application Configuration
class Config:
    # Server Settings
    PORT = 5000
    HOST = '127.0.0.1'  # localhost
    DEBUG = True  # Set to False for production

    # Security
    SECRET_KEY = 'test'

    # Stock Settings
    DEFAULT_STOCKS = ['AAPL', 'TSLA', 'AMZN', 'GOOGL', 'SBUX', 'MSFT', 'NFLX']
    CACHE_REFRESH_INTERVAL = 4  # seconds
    MAX_WATCHLIST_ITEMS = 10

    # Session Settings
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours