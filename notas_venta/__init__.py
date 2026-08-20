from flask import Blueprint

notas_venta_bp = Blueprint("notas_venta", __name__, url_prefix="/notas-venta")

from app.notas_venta import routes  # noqa: E402,F401
