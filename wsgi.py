#!/usr/bin/env python3
"""
Point d'entrée WSGI pour l'application Todo Hôtel
Utilisé par Gunicorn et autres serveurs WSGI
"""

import os
from app import create_app

# Créer l'instance de l'application Flask
app = create_app()

if __name__ == "__main__":
    # Mode développement local
    app.run(host='0.0.0.0', port=8081, debug=False)