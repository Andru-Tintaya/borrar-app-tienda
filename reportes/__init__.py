from flask import Blueprint

reportes_bp = Blueprint("reportes", __name__, url_prefix="/reportes", template_folder="templates")

from app.reportes import routes  # noqa: E402,F401
