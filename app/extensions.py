from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO
# TODO (Later): Import Celery when ready
# from celery import Celery

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address)
socketio = SocketIO(cors_allowed_origins="*")

# TODO (Later): Initialize Celery when ready
# def make_celery(app_name=__name__):
#     return Celery(app_name)
# 
# celery = make_celery()
