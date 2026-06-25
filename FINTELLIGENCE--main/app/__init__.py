from flask import Flask
from flask_cors import CORS
from app.config import config
# TODO (Later): Import celery when ready
# from app.extensions import db, migrate, jwt, limiter, socketio, celery
from app.extensions import db, migrate, jwt, limiter, socketio

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize CORS
    CORS(app)

    # Initialize Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    limiter.init_app(app)
    socketio.init_app(app)

    # TODO (Later): Configure Celery when ready
    # celery.conf.update(app.config)
    
    # Import Models so they are registered with SQLAlchemy
    with app.app_context():
        db.create_all()
    
    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.upload import upload_bp
    from app.routes.transactions import transactions_bp
    from app.routes.cases import cases_bp
    from app.routes.health import health_bp
    from app.routes.graph import graph_bp
    from app.routes.detectors import detectors_bp
    from app.routes.ai import ai_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(upload_bp, url_prefix='/api/upload')
    app.register_blueprint(transactions_bp, url_prefix='/api/transactions')
    app.register_blueprint(cases_bp, url_prefix='/api/cases')
    app.register_blueprint(health_bp, url_prefix='/api/health')
    app.register_blueprint(graph_bp)
    app.register_blueprint(detectors_bp)
    app.register_blueprint(ai_bp)
    
    from app.intelligence.silent_engine import intelligence_bp
    from app.intelligence.suspicion_score import suspicion_bp
    from app.routes.governance import governance_bp
    from app.routes.evidence import evidence_bp
    from app.reports.report_generator import reports_bp

    # New additive route blueprints
    from app.routes.dashboard import dashboard_bp
    from app.routes.escalation import escalation_bp

    app.register_blueprint(intelligence_bp)
    app.register_blueprint(suspicion_bp)
    app.register_blueprint(governance_bp)
    app.register_blueprint(evidence_bp)
    app.register_blueprint(reports_bp)

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(escalation_bp)

    return app

