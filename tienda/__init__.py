from flask import Blueprint

tienda_bp = Blueprint("tienda", __name__, url_prefix="", template_folder="templates")

from app.tienda import routes  # noqa: E402,F401
