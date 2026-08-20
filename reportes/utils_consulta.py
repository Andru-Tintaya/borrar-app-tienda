from app.extensions import db
from app.models_all import ItemPedido, Pedido, Producto, Categoria, NIVELES_PRECIO

VENTAS_VALIDAS = ("Pagado", "En preparación", "Entregado")


def consultar_ventas(fecha_desde=None, fecha_hasta=None, producto_id=None, categoria_id=None, canal=None):
    """Devuelve las líneas de venta (ItemPedido) que cumplen los filtros,
    considerando únicamente pedidos con pago verificado (Pagado, En
    preparación o Entregado); los Rechazados y Pendientes no cuentan como
    venta ni ingreso real."""
    consulta = (
        db.session.query(ItemPedido, Pedido, Producto)
        .join(Pedido, ItemPedido.pedido_id == Pedido.id)
        .join(Producto, ItemPedido.producto_id == Producto.id)
        .filter(Pedido.estado.in_(VENTAS_VALIDAS))
    )

    if fecha_desde:
        consulta = consulta.filter(Pedido.fecha_creacion >= fecha_desde)
    if fecha_hasta:
        consulta = consulta.filter(Pedido.fecha_creacion <= fecha_hasta)
    if producto_id:
        consulta = consulta.filter(ItemPedido.producto_id == producto_id)
    if categoria_id:
        consulta = consulta.filter(Producto.categoria_id == categoria_id)
    if canal:
        consulta = consulta.filter(ItemPedido.nivel_precio == canal)

    consulta = consulta.order_by(Pedido.fecha_creacion.desc())

    filas = []
    for item, pedido, producto in consulta.all():
        filas.append({
            "fecha": pedido.fecha_creacion,
            "pedido_id": pedido.id,
            "producto": producto.nombre,
            "categoria": producto.categoria.nombre if producto.categoria else "-",
            "canal": item.nivel_precio,
            "cantidad": item.cantidad,
            "precio_unitario": item.precio_unitario,
            "subtotal": item.subtotal,
        })
    return filas


def calcular_resumen(filas):
    resumen = {
        "total_ingresos": sum(f["subtotal"] for f in filas),
        "total_unidades": sum(f["cantidad"] for f in filas),
        "por_canal": {},
    }
    for canal in NIVELES_PRECIO:
        filas_canal = [f for f in filas if f["canal"] == canal]
        resumen["por_canal"][canal] = {
            "unidades": sum(f["cantidad"] for f in filas_canal),
            "ingresos": sum(f["subtotal"] for f in filas_canal),
        }
    return resumen
