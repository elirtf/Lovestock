from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import yfinance as yf
from datetime import datetime
from typing import Optional
import threading
import time
import logging
from functools import wraps
from config import Config

# Configure logging
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY

DEFAULT_STOCKS = Config.DEFAULT_STOCKS
CACHE_REFRESH_INTERVAL = Config.CACHE_REFRESH_INTERVAL
MAX_WATCHLIST_ITEMS = Config.MAX_WATCHLIST_ITEMS

stock_cache = {}
users = {}  # In-memory user storage

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to access this page', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def fetch_stock_data(symbol: str) -> Optional[dict]:
    """Fetch current stock data with error handling"""
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period="1d", interval="1m")

        if hist.empty:
            logger.warning(f"No data available for symbol: {symbol}")
            return None

        current_price = hist['Close'].iloc[-1]
        open_price = hist['Open'].iloc[0]
        price_change = current_price - open_price

        return {
            'symbol': symbol,
            'price': round(current_price, 2),
            'change': round(price_change, 2),
            'percent_change': round((price_change / open_price) * 100, 2),
            'volume': int(hist['Volume'].sum()),
            'chart_data': hist['Close'].tolist()[-100:],
            'updated_at': datetime.now().strftime('%H:%M:%S')
        }
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {str(e)}")
        return None

def update_stock_cache():
    """Background task to update stock data"""
    while True:
        try:
            for symbol in DEFAULT_STOCKS:
                data = fetch_stock_data(symbol)
                if data:
                    stock_cache[symbol] = data
            time.sleep(CACHE_REFRESH_INTERVAL)
        except Exception as e:
            logger.error(f"Error in cache update thread: {str(e)}")
            time.sleep(CACHE_REFRESH_INTERVAL * 2)  # Back off on error

# Start the background thread
update_thread = threading.Thread(target=update_stock_cache, daemon=True)
update_thread.start()

@app.route('/')
@login_required
def index():
    sort_by = request.args.get('sort_by', 'symbol')
    try:
        stocks = list(stock_cache.values())

        # Sort stocks based on user preference
        if sort_by == 'price':
            stocks.sort(key=lambda x: x['price'], reverse=True)
        elif sort_by == 'change':
            stocks.sort(key=lambda x: x['change'], reverse=True)
        else:  # default to symbol
            stocks.sort(key=lambda x: x['symbol'])

        watchlist = session.get('watchlist', [])
        watchlist_data = [stock_cache.get(symbol) for symbol in watchlist
                          if stock_cache.get(symbol)]

        return render_template('index.html',
                               stocks=stocks,
                               watchlist=watchlist_data,
                               max_watchlist=MAX_WATCHLIST_ITEMS)
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        flash("An error occurred while loading the page", "error")


@app.route('/stock/<symbol>')
@login_required
def stock_detail(symbol):
    try:
        timeframe = request.args.get('timeframe', '1d')
        stock = yf.Ticker(symbol)

        # Mapping of timeframes to yfinance parameters
        timeframe_params = {
            '1d': ('1d', '5m'),
            '1w': ('5d', '1h'),
            '1m': ('1mo', '1d'),
            '3m': ('3mo', '1d'),
            '1y': ('1y', '1wk')
        }

        period, interval = timeframe_params.get(timeframe, ('1d', '5m'))
        hist = stock.history(period=period, interval=interval)

        if hist.empty:
            flash(f"No data available for {symbol}", "warning")
            return redirect(url_for('index'))

        # Convert historical data for the chart
        hist_data = []
        for index, row in hist.iterrows():
            hist_data.append({
                'date': index.strftime('%Y-%m-%d %H:%M:%S'),
                'price': round(row['Close'], 2)
            })

        info = stock.info
        stock_data = {
            'symbol': symbol,
            'name': info.get('longName', symbol),
            'price': round(hist['Close'].iloc[-1], 2),
            'change': round(hist['Close'].iloc[-1] - hist['Open'].iloc[0], 2),
            'change_percent': round((hist['Close'].iloc[-1] - hist['Open'].iloc[0]) / hist['Open'].iloc[0] * 100, 2),
            'details': {
                'Open': round(hist['Open'].iloc[0], 2),
                'High': round(hist['High'].max(), 2),
                'Low': round(hist['Low'].min(), 2),
                'Volume': int(hist['Volume'].sum()),
                'Market Cap': f"${info.get('marketCap', 0):,}" if info.get('marketCap') else 'N/A',
                'P/E Ratio': f"{info.get('forwardPE', 'N/A'):.2f}" if isinstance(info.get('forwardPE'), (int, float)) else 'N/A',
                'EPS': f"{info.get('trailingEps', 'N/A'):.2f}" if isinstance(info.get('trailingEps'), (int, float)) else 'N/A',
                'Beta': f"{info.get('beta', 'N/A'):.2f}" if isinstance(info.get('beta'), (int, float)) else 'N/A',
                'Dividend Yield': f"{info.get('dividendYield', 0) * 100:.2f}%" if info.get('dividendYield') else 'N/A',
                '52 Week High': round(info.get('fiftyTwoWeekHigh', 0), 2) if info.get('fiftyTwoWeekHigh') else 'N/A',
                '52 Week Low': round(info.get('fiftyTwoWeekLow', 0), 2) if info.get('fiftyTwoWeekLow') else 'N/A'
            }
        }

        return render_template('stock.html',
                               stock=stock_data,
                               timeframe=timeframe,
                               hist_data=hist_data)
    except Exception as e:
        logger.error(f"Error in stock detail route: {str(e)}")
        flash("An error occurred while fetching stock data", "error")
        return redirect(url_for('index'))

@app.route('/api/stock/<symbol>/latest')
@login_required
def get_latest_stock_data(symbol):
    try:
        data = stock_cache.get(symbol)
        if data:
            return jsonify(data)
        return jsonify({'error': 'Stock not found'}), 404
    except Exception as e:
        logger.error(f"Error fetching latest stock data: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/add_to_watchlist', methods=['POST'])
@login_required
def add_to_watchlist():
    try:
        symbol = request.form['symbol']
        watchlist = session.get('watchlist', [])

        if len(watchlist) >= MAX_WATCHLIST_ITEMS:
            flash(f'Watchlist is limited to {MAX_WATCHLIST_ITEMS} items', 'error')
            return redirect(request.referrer or url_for('index'))

        if symbol not in watchlist:
            watchlist.append(symbol)
            session['watchlist'] = watchlist
            flash(f'{symbol} added to watchlist', 'success')

        return redirect(request.referrer or url_for('index'))
    except Exception as e:
        logger.error(f"Error adding to watchlist: {str(e)}")
        flash("An error occurred while updating watchlist", "error")
        return redirect(url_for('index'))
@app.route('/remove_from_watchlist', methods=['POST'])
@login_required
def remove_from_watchlist():
    try:
        symbol = request.form['symbol']
        watchlist = session.get('watchlist', [])

        if symbol in watchlist:
            watchlist.remove(symbol)
            session['watchlist'] = watchlist
            flash(f'{symbol} removed from watchlist', 'success')

        return redirect(request.referrer or url_for('index'))
    except Exception as e:
        logger.error(f"Error removing from watchlist: {str(e)}")
        flash("An error occurred while updating watchlist", "error")
        return redirect(url_for('index'))


@app.route('/search')
@login_required
def search():
    query = request.args.get('q', '').strip().upper()
    if len(query) < 1:
        return jsonify([])

    try:
        logger.info(f"Searching for symbol: {query}")
        results = []

        # First check cache for quick results
        if any(query in stock for stock in DEFAULT_STOCKS):
            cached_matches = [stock for stock in DEFAULT_STOCKS if query in stock]
            for symbol in cached_matches:
                data = stock_cache.get(symbol)
                if data:
                    results.append(data)

        # If query is not in cache, try to fetch it directly
        if len(query) >= 1 and query not in DEFAULT_STOCKS:
            data = fetch_stock_data(query)
            if data:
                # Add to results if valid stock found
                results.append(data)
                # Optionally add to cache
                stock_cache[query] = data

        # Remove duplicates while preserving order
        seen = set()
        unique_results = []
        for item in results:
            if item['symbol'] not in seen:
                seen.add(item['symbol'])
                unique_results.append(item)

        logger.info(f"Returning {len(unique_results)} results")
        return jsonify(unique_results)

    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Username and password are required', 'error')
            return redirect(url_for('register'))

        if username in users:
            flash('Username already exists', 'error')
            return redirect(url_for('register'))

        users[username] = generate_password_hash(password)
        session['username'] = username
        session['watchlist'] = []
        flash('Registration successful!', 'success')
        return redirect(url_for('index'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Username and password are required', 'error')
            return redirect(url_for('login'))

        stored_password = users.get(username)
        if stored_password and check_password_hash(stored_password, password):
            session['username'] = username
            if 'watchlist' not in session:
                session['watchlist'] = []
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )