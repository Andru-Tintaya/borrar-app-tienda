from flask import Blueprint

categorias_bp = Blueprint("categorias", __name__, url_prefix="/categorias", template_folder="templates")

from app.categorias import routes  # noqa: E402,F401
