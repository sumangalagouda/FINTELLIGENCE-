import os
from dotenv import load_dotenv

# Load environment variables from .env file before importing from app
load_dotenv()

from app import create_app
from app.extensions import socketio

app = create_app(os.getenv('FLASK_ENV', 'development'))

if __name__ == '__main__':
    # Ensure upload folder exists
    upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads/')
    os.makedirs(upload_folder, exist_ok=True)
    
    # Run the application with SocketIO
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
