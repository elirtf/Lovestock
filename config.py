# Application Configuration
class Config:
    PORT = 5000
    HOST = '127.0.0.1'
    DEBUG = True  # Set to False for production

    SECRET_KEY = 'test'

    DEFAULT_STOCKS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA']
    # ^GSPC
    # ^DJI
    # ^IXIC

    CACHE_REFRESH_INTERVAL = 5
    MAX_WATCHLIST_ITEMS = 10

