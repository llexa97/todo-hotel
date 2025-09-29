from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
import logging
from logging.handlers import RotatingFileHandler
import sys
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()

def setup_logging(app):
    """Configure le système de logging pour l'application."""
    flask_env = os.getenv('FLASK_ENV', 'development')
    
    # Niveau de log selon l'environnement
    log_level = logging.INFO if flask_env == 'production' else logging.DEBUG
    
    # Format des logs
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    
    # Répertoire des logs
    if flask_env == 'production':
        log_dir = '/app/logs'
    else:
        basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        log_dir = os.path.join(basedir, 'logs')
    
    # Créer le répertoire s'il n'existe pas
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # Handler pour fichier principal
    main_handler = RotatingFileHandler(
        os.path.join(log_dir, 'todo_hotel.log'),
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    main_handler.setFormatter(formatter)
    main_handler.setLevel(log_level)
    
    # Handler pour la console (développement)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    
    # Configuration du logger principal de l'app
    app.logger.setLevel(log_level)
    app.logger.addHandler(main_handler)
    
    if flask_env == 'development':
        app.logger.addHandler(console_handler)
    
    # Configuration du logger SQLAlchemy (modéré)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    
    # Logger pour les requêtes HTTP
    werkzeug_logger = logging.getLogger('werkzeug')
    if flask_env == 'production':
        werkzeug_logger.setLevel(logging.WARNING)
    
    app.logger.info(f"🚀 Application Todo Hotel démarrée - Environnement: {flask_env}")
    app.logger.info(f"📊 Niveau de log: {logging.getLevelName(log_level)}")
    app.logger.info(f"📁 Répertoire logs: {log_dir}")


def create_app():
    app = Flask(__name__)
    
    # Configuration de la base de données selon l'environnement
    flask_env = os.getenv('FLASK_ENV', 'development')
    
    # Chemin par défaut selon l'environnement
    if flask_env == 'production':
        default_db_url = 'sqlite:////root/todo-hotel/instance/todo_hotel.db'
    else:
        # Utiliser un chemin absolu pour le développement
        basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        default_db_url = f'sqlite:///{os.path.join(basedir, "instance", "todo_hotel.db")}'
    
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', default_db_url)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Configuration du logging AVANT l'initialisation des extensions
    setup_logging(app)
    
    app.logger.info("🔧 Initialisation des extensions Flask")
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    
    app.logger.info("📁 Configuration base de données: %s", app.config['SQLALCHEMY_DATABASE_URI'].split('/')[-1])
    
    # Import models (needed for SQLAlchemy to register them)
    from . import models  # noqa: F401
    app.logger.info("📋 Modèles SQLAlchemy importés")
    
    # Register blueprints
    from .routes_main import main_bp
    from .routes_api import api_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    
    app.logger.info("🌐 Blueprints enregistrés (main_bp, api_bp)")
    app.logger.info("✅ Application Flask initialisée avec succès")
    
    return app