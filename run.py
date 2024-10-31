from app import app  # This imports the Flask app instance from app.py
from config import Config

if __name__ == '__main__':
    print('Starting Lovestock...')
    print(f"Open your browser to http://{Config.HOST}:{Config.PORT}")
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )