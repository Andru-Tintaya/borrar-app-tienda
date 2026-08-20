from flask import Blueprint

api_bp = Blueprint("api", __name__, url_prefix="/api")

# Importar las rutas para registrarlas con el blueprint
from app.api import auth, pedidos
