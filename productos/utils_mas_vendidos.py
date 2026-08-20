from app.extensions import db
from app.models_all import ItemPedido, Pedido

# Mismos estados que cuentan como venta real en app/reportes/utils_consulta.py
VENTAS_VALIDAS = ("Pagado", "En preparación", "Entregado")

# Cuántos productos entran en la etiqueta "Más Vendido"
LIMITE_MAS_VENDIDOS = 8


def obtener_ids_mas_vendidos(limite: int = LIMITE_MAS_VENDIDOS) -> set:
    """Devuelve el conjunto de IDs de producto con más unidades vendidas
    (sumando ItemPedido.cantidad de pedidos con pago verificado). Se
    recalcula en cada consulta: no hay bandera guardada en la base de
    datos para "más vendido"."""
    filas = (
        db.session.query(ItemPedido.producto_id, db.func.sum(ItemPedido.cantidad).label("unidades"))
        .join(Pedido, ItemPedido.pedido_id == Pedido.id)
        .filter(Pedido.estado.in_(VENTAS_VALIDAS))
        .group_by(ItemPedido.producto_id)
        .order_by(db.desc("unidades"))
        .limit(limite)
        .all()
    )
    return {producto_id for producto_id, _ in filas}
