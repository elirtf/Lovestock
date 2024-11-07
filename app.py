from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import yfinance as yf
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
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
SECTORS = Config.SECTORS
INDUSTRIES = Config.INDUSTRIES
DEFAULT_STOCKS = Config.DEFAULT_STOCKS
MAX_WATCHLIST_ITEMS = Config.MAX_WATCHLIST_ITEMS

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

def is_market_day(date):
    """Check if date is a market trading day (excluding weekends)"""
    # Convert to datetime if it's not already
    if not isinstance(date, datetime):
        date = pd.to_datetime(date)
    return date.weekday() < 5  # 0-4 are Monday-Friday

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

        stockinfo = stock.info
        marketcap = stockinfo.get('marketCap', 0)
        marketcap = format_large_number(marketcap)

        if hist.empty:
            logger.warning(f"No data available for symbol: {symbol}")
            return None

        current_price = hist['Close'].iloc[-1]
        open_price = hist['Open'].iloc[0]
        price_change = current_price - open_price
        volume = hist['Volume'].sum()

        return {
            'symbol': symbol,
            'name': stock.info.get('longName', symbol),
            'price': round(current_price, 2),
            'change': round(price_change, 2),
            'percent_change': round((price_change / open_price) * 100, 2),
            'volume': format_large_number(volume),
            'marketCap': marketcap,
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

        timeframe_params = {
            '1d': ('1d', '5m'),
            '1w': ('5d', '15m'),
            '1m': ('1mo', '1h'),
            '3m': ('3mo', '1d'),
            '1y': ('1y', '1d'),
            '5y': ('5y', '1w')
        }
        period, interval = timeframe_params.get(timeframe, ('1d', '5m'))

        hist = stock.history(period=period, interval=interval)

        info = stock.info

        # Filter out weekends and after-hours for 1d timeframe
        if timeframe == '1d':
            market_hours = (hist.index.hour >= 9) & (hist.index.hour < 16) | \
                           ((hist.index.hour == 16) & (hist.index.minute == 0))
            hist = hist[market_hours]
        else:
            # Filter out weekends from other timeframes
            hist = hist[hist.index.map(is_market_day)]

        if hist.empty:
            return None

        # Format historical data
        hist_data = [{
            'date': index.isoformat(),
            'price': round(row['Close'], 2),
            'open': round(row['Open'], 2),
            'high': round(row['High'], 2),
            'low': round(row['Low'], 2),
            'close': round(row['Close'], 2),
            'volume': int(row['Volume'])
        } for index, row in hist.iterrows()]

        current_price = hist['Close'].iloc[-1]
        open_price = hist['Open'].iloc[0]
        price_change = current_price - open_price

        return {
            'symbol': symbol,
            'name': stock.info.get('longName', symbol),
            'price': round(current_price, 2),
            'change': round(price_change, 2),
            'percent_change': round((price_change / open_price) * 100, 2),
            'historical_data': hist_data,
            'details': {
                'Open': round(open_price, 2),
                'High': round(hist['High'].max(), 2),
                'Low': round(hist['Low'].min(), 2),
                'Volume': format_large_number(hist['Volume'].sum()),
                'Market Cap': format_large_number(stock.info.get('marketCap', 0)),
                'P/E Ratio': f"{stock.info.get('forwardPE', 'N/A'):.2f}" if isinstance(stock.info.get('forwardPE'), (int, float)) else 'N/A',
                'EPS': f"{stock.info.get('trailingEps', 'N/A'):.2f}" if isinstance(stock.info.get('trailingEps'), (int, float)) else 'N/A',
                'Beta': f"{stock.info.get('beta', 'N/A'):.2f}" if isinstance(stock.info.get('beta'), (int, float)) else 'N/A',
                'Dividend Yield': f"{stock.info.get('dividendYield', 0) * 100:.2f}%" if stock.info.get('dividendYield') else 'N/A',
                '52 Week High': round(stock.info.get('fiftyTwoWeekHigh', 0), 2) if stock.info.get('fiftyTwoWeekHigh') else 'N/A',
                '52 Week Low': round(stock.info.get('fiftyTwoWeekLow', 0), 2) if stock.info.get('fiftyTwoWeekLow') else 'N/A'
            }
        }
    except Exception as e:
        logger.error(f"Error fetching detailed data for {symbol}: {str(e)}")
        return None

def fetch_sector_data(sector_symbols):
    """Fetch data for all symbols in industry sectors"""
    sector_data = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_stock_data, symbol): symbol for symbol in sector_symbols}
        for future in futures:
            try:
                data = future.result()
                if data:
                    sector_data.append(data)
            except Exception as e:
                logger.error(f"Error fetching sector data: {str(e)}")
    return sector_data
def calculate_industry_performance(industries):
    performance = {}
    for industry, symbols in industries.items():
        industry_data = fetch_sector_data(symbols)
        if industry_data:
            avg_change = sum(stock['percent_change'] for stock in industry_data) / len(industry_data)
            total_volume = sum(float(stock['volume'].replace('B', '000M').replace('M', '000K').replace('K', ''))
                               for stock in industry_data)
            performance[industry] = {
                'change': avg_change,
                'volume': format_large_number(total_volume),
                'stocks': len(industry_data)
            }
    return performance
def calculate_sector_performance(sectors):
    performance = {}
    for sector, symbols in sectors.items():
        sector_data = fetch_sector_data(symbols)
        if sector_data:
            avg_change = sum(stock['percent_change'] for stock in sector_data) / len(sector_data)
            total_volume = sum(float(stock['volume'].replace('B', '000M').replace('M', '000K').replace('K', ''))
                               for stock in sector_data)
            performance[sector] = {
                'change': avg_change,
                'volume': format_large_number(total_volume),
                'stocks': len(sector_data)
            }
    return performance

def fetch_stock_news(symbol: str) -> list:
    """Fetch news with preview for a specific stock"""
    try:
        stock = yf.Ticker(symbol)
        news = stock.news
        formatted_news = []

        for item in news[:5]:  # Limit to 5 most recent news items
            image_url = None
            if 'thumbnail' in item and 'resolutions' in item['thumbnail']:
                resolutions = item['thumbnail']['resolutions']
                if resolutions:
                    image_url = resolutions[-1].get('url')

            formatted_news.append({
                'title': item.get('title', ''),
                'publisher': item.get('publisher', ''),
                'link': item.get('link', ''),
                'published': datetime.fromtimestamp(item.get('providerPublishTime', 0)).strftime('%Y-%m-%d %H:%M %p'),
                'summary': item.get('summary', '')[:200] + '...' if item.get('summary') else '',
                'image_url': image_url
            })

        return formatted_news
    except Exception as e:
        logger.error(f"Error fetching news for {symbol}: {str(e)}")
        return []

def update_stock_cache():
    """Background task to update stock data"""
    while True:
        try:
            for symbol in DEFAULT_STOCKS:
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
        elif sort_by == 'name':
            stocks.sort(key=lambda x: x['name'], reverse=True)
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

        news_data = fetch_stock_news(symbol)
        watchlist = session.get('watchlist', [])

        return render_template('stock.html',
                               stock=stock_data,
                               timeframe=timeframe,
                               market_open=is_market_open(),
                               is_in_watchlist=symbol in watchlist,
                               max_watchlist=MAX_WATCHLIST_ITEMS,
                               news=news_data)
    except Exception as e:
        logger.error(f"Error in stock detail: {str(e)}")
        flash("Error loading stock details", "error")
        return redirect(url_for('index'))

@app.route('/api/stock/<symbol>/latest')
def get_latest_stock_data(symbol):
    try:
        data = stock_cache.get(symbol)
        if data:
            return jsonify(data)

        # If not in cache, fetch it
        data = fetch_stock_data(symbol)
        if data:
            stock_cache[symbol] = data
            return jsonify(data)

        return jsonify({'error': 'Stock not found'}), 404
    except Exception as e:
        logger.error(f"Error fetching latest stock data: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/screener')
def stock_screener():
    try:
        selected_sector = request.args.get('sector', 'Technology')
        selected_industry = request.args.get('industry')
        sort_by = request.args.get('sort_by', 'marketCap')
        view_type = request.args.get('view', 'sectors')  # 'sectors' or 'industries'

        if view_type == 'industries' and selected_industry:
            symbols = INDUSTRIES.get(selected_industry, [])
            stocks_data = fetch_sector_data(symbols)
            sector_performance = calculate_industry_performance(INDUSTRIES)
        else:
            symbols = SECTORS.get(selected_sector, [])
            stocks_data = fetch_sector_data(symbols)
            sector_performance = calculate_sector_performance(SECTORS)

        # Sort stocks based on criteria
        if stocks_data:
            if sort_by == 'price':
                stocks_data.sort(key=lambda x: x['price'], reverse=True)
            elif sort_by == 'percent_change':
                stocks_data.sort(key=lambda x: x['percent_change'], reverse=True)
            elif sort_by == 'volume':
                stocks_data.sort(
                    key=lambda x: float(x['volume'].replace('B', '000M').replace('M', '000K').replace('K', '')),
                    reverse=True
                )
            elif sort_by == 'marketCap':
                stocks_data.sort(
                    key=lambda x: float(
                        x['marketCap'].replace('T', '000B').replace('B', '000M').replace('M', '000K').replace('K', '')),
                    reverse=True
                )

        return render_template('screener.html',
                               sectors=SECTORS.keys(),
                               industries=INDUSTRIES.keys(),
                               selected_sector=selected_sector,
                               selected_industry=selected_industry,
                               view_type=view_type,
                               sector_performance=sector_performance,
                               stocks=stocks_data,
                               sort_by=sort_by)

    except Exception as e:
        logger.error(f"Error in screener route: {str(e)}")
    flash("Error loading screener data", "error")
    return redirect(url_for('index'))


@app.route('/add_to_watchlist', methods=['POST'])
def add_to_watchlist():
    try:
        symbol = request.form['symbol']
        return_to = request.form.get('return_to')
        watchlist = session.get('watchlist', [])

        if len(watchlist) >= MAX_WATCHLIST_ITEMS:
            flash(f'Watchlist is limited to {MAX_WATCHLIST_ITEMS} items', 'error')
            return redirect(url_for('index'))
        if symbol not in watchlist:
            watchlist.append(symbol)
            session['watchlist'] = watchlist
            flash(f'{symbol} added to watchlist', 'success')

        return redirect(return_to if return_to else url_for('index'))
    except Exception as e:
        logger.error(f"Error adding to watchlist: {str(e)}")
        flash('An error occurred while updating watchlist', 'error')
        return redirect(url_for('index'))

@app.route('/remove_from_watchlist', methods=['POST'])
def remove_from_watchlist():
    try:
        symbol = request.form['symbol']
        return_to = request.form.get('return_to')
        watchlist = session.get('watchlist', [])

        if symbol in watchlist:
            watchlist.remove(symbol)
            session['watchlist'] = watchlist
            flash(f'{symbol} removed from watchlist', 'success')

        return redirect(return_to if return_to else url_for('index'))
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

        # First check cache for exact matches
        cached_matches = [stock for stock in DEFAULT_STOCKS if query == stock]
        for symbol in cached_matches:
            data = stock_cache.get(symbol)
            if data:
                results.append(data)

        # If query is not in cache, try to fetch it directly
        if not results and len(query) >= 1:
            data = fetch_stock_data(query)
            if data:
                results.append(data)
                stock_cache[query] = data

        # If still no results, look for partial matches in cache
        if not results:
            partial_matches = [stock for stock in DEFAULT_STOCKS if query in stock]
            for symbol in partial_matches:
                data = stock_cache.get(symbol)
                if data:
                    results.append(data)

        # Remove duplicates while preserving order
        seen = set()
        unique_results = []
        for item in results:
            if item['symbol'] not in seen:
                seen.add(item['symbol'])
                unique_results.append(item)

        logger.info(f"Returning {len(unique_results)} results")
        return jsonify(unique_results[:5])

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