from app.models_all import Pedido


def siguiente_numero_nota() -> int:
    ultimo = Pedido.query.filter(Pedido.numero_nota.isnot(None)).order_by(Pedido.numero_nota.desc()).first()
    if ultimo is None:
        return 1000
    return ultimo.numero_nota + 1
