# Application Configuration
class Config:
    PORT = 5000
    HOST = '127.0.0.1'
    DEBUG = True  # Set to False for production

    SECRET_KEY = 'test'

    DEFAULT_STOCKS = ['^GSPC', '^DJI', '^IXIC', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA']
    SECTORS = {
        'Technology': [
            'AAPL', 'MSFT', 'GOOGL', 'META', 'NVDA', 'ADBE', 'CRM', 'INTC', 'AMD', 'CSCO'
        ],
        'Healthcare': [
            'JNJ', 'UNH', 'PFE', 'ABT', 'TMO', 'MRK', 'ABBV', 'DHR', 'BMY', 'AMGN'
        ],
        'Financial': [
            'JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'BLK', 'SCHW', 'AXP', 'V'
        ],
        'Consumer': [
            'AMZN', 'WMT', 'HD', 'NKE', 'MCD', 'SBUX', 'TGT', 'COST', 'PG', 'KO'
        ],
        'Industrial': [
            'BA', 'CAT', 'GE', 'HON', 'UPS', 'MMM', 'LMT', 'RTX', 'UNP', 'DE'
        ],
        'Energy': [
            'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'PXD', 'MPC', 'PSX', 'VLO', 'OXY'
        ]
    }
    INDUSTRIES = {
        'Software': ['MSFT', 'ADBE', 'CRM', 'ORCL', 'INTU', 'NOW', 'SNPS', 'CDNS'],
        'Semiconductors': ['NVDA', 'AMD', 'INTC', 'QCOM', 'AVGO', 'TSM', 'MU', 'AMAT'],
        'E-commerce': ['AMZN', 'SHOP', 'ETSY', 'EBAY', 'MELI', 'JD', 'PDD', 'CPNG'],
        'Social Media': ['META', 'SNAP', 'PINS', 'TWTR', 'MTCH'],
        'Fintech': ['V', 'MA', 'PYPL', 'SQ', 'COIN', 'AFRM', 'SOFI'],
        'Electric Vehicles': ['TSLA', 'RIVN', 'LCID', 'NIO', 'LI', 'XPEV'],
        'Cybersecurity': ['CRWD', 'PANW', 'FTNT', 'ZS', 'OKTA', 'NET'],
        'Cloud Computing': ['AMZN', 'MSFT', 'GOOGL', 'NET', 'DDOG', 'SNOW']
    }

    MAX_WATCHLIST_ITEMS = 10
    CACHE_REFRESH_INTERVAL = 5


