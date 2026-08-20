from flask import Blueprint

productos_bp = Blueprint("productos", __name__, url_prefix="/productos", template_folder="templates")

from app.productos import routes  # noqa: E402,F401
