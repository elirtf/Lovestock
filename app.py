from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import yfinance as yf
from datetime import datetime
import time
from datetime import time as datetime_time
from typing import Optional
import pytz
import threading
import logging
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

stock_cache = {}

def is_market_open() -> bool:
    """Check if the US stock market is currently open"""
    ny_tz = pytz.timezone('America/New_York')
    current_time = datetime.now(ny_tz)

    # Check if it's a weekday
    if current_time.weekday() >= 5:
        return False

    # Market hours: 9:30 AM - 4:00 PM EST
    market_open = datetime_time(9, 30)
    market_close = datetime_time(16, 0)
    current_time = current_time.time()

    return market_open <= current_time <= market_close

def format_large_number(number: float) -> str:
    """
    Format large numbers into human-readable format with suffixes (K, M, B, T)
    3430000000000 -> 3.43T
    1234567890 -> 1.23B
    1234567 -> 1.23M
    12345 -> 12.3K
    """
    suffixes = ['', 'K', 'M', 'B', 'T']
    sign = '-' if number < 0 else '' # Handle negative numbers
    number = abs(number)

    # Find the appropriate suffix
    magnitude = 0
    while number >= 1000 and magnitude < len(suffixes) - 1:
        magnitude += 1
        number /= 1000.0

    return f"{sign}{number:.2f}{suffixes[magnitude]}"

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
        volume = hist['Volume'].sum()
        info = stock.info

        return {
            'symbol': symbol,
            'name': info.get('longName', symbol),
            'price': round(current_price, 2),
            'change': round(price_change, 2),
            'percent_change': round((price_change / open_price) * 100, 2),
            'volume': format_large_number(volume),
            'chart_data': hist['Close'].tolist()[-100:],
            'updated_at': datetime.now().strftime('%H:%M:%S')
        }
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {str(e)}")
        return None

def fetch_detailed_stock_data(symbol: str, timeframe: str = '1d') -> Optional[dict]:
    """Fetch detailed stock data for the stock detail page"""
    try:
        stock = yf.Ticker(symbol)

        # Timeframe parameters
        timeframe_params = {
            '1d': ('1d', '5m'),
            '1w': ('5d', '1h'),
            '1m': ('1mo', '1d'),
            '3m': ('3mo', '1d'),
            '1y': ('1y', '1wk')
        }
        period, interval = timeframe_params.get(timeframe, ('1d', '5m'))

        hist = stock.history(period=period, interval=interval)
        info = stock.info

        if hist.empty:
            return None

        # Format historical data for charts
        hist_data = [{
            'date': index.strftime('%m-%d %H:%M:%S'),
            'price': round(row['Close'], 2)
        } for index, row in hist.iterrows()]

        current_price = hist['Close'].iloc[-1]
        open_price = hist['Open'].iloc[0]
        price_change = current_price - open_price

        return {
            'symbol': symbol,
            'name': info.get('longName', symbol),
            'price': round(current_price, 2),
            'change': round(price_change, 2),
            'percent_change': round((price_change / open_price) * 100, 2),
            'historical_data': hist_data,
            'details': {
                'Open': round(hist['Open'].iloc[0], 2),
                'High': round(hist['High'].max(), 2),
                'Low': round(hist['Low'].min(), 2),
                'Volume': format_large_number(hist['Volume'].sum()),
                'Market Cap': format_large_number(info.get('marketCap', 0)),
                'P/E Ratio': f"{info.get('forwardPE', 'N/A'):.2f}" if isinstance(info.get('forwardPE'), (int, float)) else 'N/A',
                'EPS': f"{info.get('trailingEps', 'N/A'):.2f}" if isinstance(info.get('trailingEps'), (int, float)) else 'N/A',
                'Beta': f"{info.get('beta', 'N/A'):.2f}" if isinstance(info.get('beta'), (int, float)) else 'N/A',
                'Dividend Yield': f"{info.get('dividendYield', 0) * 100:.2f}%" if info.get('dividendYield') else 'N/A',
                '52 Week High': round(info.get('fiftyTwoWeekHigh', 0), 2) if info.get('fiftyTwoWeekHigh') else 'N/A',
                '52 Week Low': round(info.get('fiftyTwoWeekLow', 0), 2) if info.get('fiftyTwoWeekLow') else 'N/A'
            }
        }
    except Exception as e:
        logger.error(f"Error fetching detailed data for {symbol}: {str(e)}")
        return None

def update_stock_cache():
    """Background task to update stock data"""
    while True:
        try:
            for symbol in Config.DEFAULT_STOCKS:
                data = fetch_stock_data(symbol)
                if data:
                    stock_cache[symbol] = data
            time.sleep(Config.CACHE_REFRESH_INTERVAL)
        except Exception as e:
            logger.error(f"Error in cache update thread: {str(e)}")
            time.sleep(Config.CACHE_REFRESH_INTERVAL * 2)  # Back off on error

# Start the background thread
update_thread = threading.Thread(target=update_stock_cache, daemon=True)
update_thread.start()

@app.route('/')
def index():
    sort_by = request.args.get('sort_by', 'symbol')
    try:
        stocks = list(stock_cache.values())

        if sort_by == 'price':
            stocks.sort(key=lambda x: x['price'], reverse=True)
        elif sort_by == 'percent_change':
            stocks.sort(key=lambda x: x['percent_change'], reverse=True)
        elif sort_by == 'volume':
            stocks.sort(key=lambda x: x['volume'], reverse=True)
        elif sort_by == 'marketCap':
            stocks.sort(key=lambda x: x['marketCap'], reverse=True)
        else:  # default to symbol
            stocks.sort(key=lambda x: x['symbol'])

        watchlist = session.get('watchlist', [])
        watchlist_data = [stock_cache.get(symbol) for symbol in watchlist
                          if stock_cache.get(symbol)]

        return render_template('index.html',
                               stocks=stocks,
                               watchlist=watchlist_data,
                               max_watchlist=Config.MAX_WATCHLIST_ITEMS)
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        flash("An error occurred while loading the data", "error")
        return render_template('index.html', stocks=[], watchlist=[])

@app.route('/stock/<symbol>')
def stock_detail(symbol):
    try:
        timeframe = request.args.get('timeframe', '1d')

        stock_data = fetch_detailed_stock_data(symbol, timeframe)

        if not stock_data:
            flash(f"Unable to fetch data for {symbol}", "error")
            return redirect(url_for('index'))

        watchlist = session.get('watchlist', [])

        return render_template('stock.html',
                               stock=stock_data,
                               timeframe=timeframe,
                               market_open=is_market_open(),
                               is_in_watchlist=symbol in watchlist,
                               max_watchlist=Config.MAX_WATCHLIST_ITEMS)
    except Exception as e:
        logger.error(f"Error in stock detail: {str(e)}")
        flash("Error loading stock details", "error")
        return redirect(url_for('index'))

@app.route('/add_to_watchlist', methods=['POST'])
def add_to_watchlist():
    try:
        symbol = request.form['symbol']
        watchlist = session.get('watchlist', [])

        if len(watchlist) >= Config.MAX_WATCHLIST_ITEMS:
            flash(f'Watchlist is limited to {Config.MAX_WATCHLIST_ITEMS} items', 'error')
            return redirect(url_for('index'))

        if symbol not in watchlist:
            watchlist.append(symbol)
            session['watchlist'] = watchlist
            flash(f'{symbol} added to watchlist', 'success')

        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error adding to watchlist: {str(e)}")
        flash('An error occurred while updating watchlist', 'error')
        return redirect(url_for('index'))

@app.route('/remove_from_watchlist', methods=['POST'])
def remove_from_watchlist():
    try:
        symbol = request.form['symbol']
        watchlist = session.get('watchlist', [])

        if symbol in watchlist:
            watchlist.remove(symbol)
            session['watchlist'] = watchlist
            flash(f'{symbol} removed from watchlist', 'success')

        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error removing from watchlist: {str(e)}")
        flash('An error occurred while updating watchlist', 'error')
        return redirect(url_for('index'))

@app.route('/search')
def search():
    query = request.args.get('q', '').strip().upper()
    if len(query) < 1:
        return jsonify([])

    try:
        logger.info(f"Searching for symbol: {query}")
        results = []

        if any(query in stock for stock in Config.DEFAULT_STOCKS):
            cached_matches = [stock for stock in Config.DEFAULT_STOCKS if query in stock]
            for symbol in cached_matches:
                data = stock_cache.get(symbol)
                if data:
                    results.append(data)

        # If query is not in cache, try to fetch it directly
        if len(query) >= 1 and query not in Config.DEFAULT_STOCKS:
            data = fetch_stock_data(query)
            if data:
                results.append(data)
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

# Error Handlers
@app.errorhandler(404)
def page_not_found(e):
    flash('Page not found', 'error')
    return redirect(url_for('index'))
@app.errorhandler(500)
def internal_server_error(e):
    logger.error(f"Server error: {str(e)}")
    flash('An internal server error occurred', 'error')
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )