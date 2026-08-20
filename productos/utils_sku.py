import random
import string
from app.models_all import Producto


def generar_sku() -> str:
    """Genera un código único NHR-XXXXXX (letras y números) para un
    producto nuevo. El usuario ya no lo escribe a mano."""
    caracteres = string.ascii_uppercase + string.digits
    while True:
        sufijo = "".join(random.choices(caracteres, k=6))
        sku = f"NHR-{sufijo}"
        if not Producto.query.filter_by(sku=sku).first():
            return sku
