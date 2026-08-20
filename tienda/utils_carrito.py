from flask import session
from app.models_all import Producto
from app.tienda.utils_precios import calcular_precio_unitario


def obtener_carrito_crudo():
    """Carrito en sesión: { "producto_id": cantidad }. Ya no se desglosa
    por talla (se venden productos variados, no solo calzado)."""
    return session.setdefault("carrito", {})


def agregar_al_carrito(producto_id, cantidad):
    carrito = obtener_carrito_crudo()
    clave = str(producto_id)
    carrito[clave] = carrito.get(clave, 0) + cantidad
    session.modified = True


def actualizar_cantidad_carrito(producto_id, cantidad):
    carrito = obtener_carrito_crudo()
    clave = str(producto_id)
    if cantidad <= 0:
        carrito.pop(clave, None)
    else:
        carrito[clave] = cantidad
    session.modified = True


def eliminar_del_carrito(producto_id):
    carrito = obtener_carrito_crudo()
    carrito.pop(str(producto_id), None)
    session.modified = True


def vaciar_carrito():
    session["carrito"] = {}
    session.modified = True


def calcular_resumen_carrito(usuario):
    """Arma la lista de líneas del carrito con precio dinámico aplicado
    (oferta + auto-descuento por docena) y el total general.
    """
    carrito = obtener_carrito_crudo()
    lineas = []
    total_general = 0
    productos_invalidos = []

    for producto_id_str, cantidad in carrito.items():
        producto_id = int(producto_id_str)
        producto = Producto.query.get(producto_id)
        if producto is None or not producto.activo:
            productos_invalidos.append(producto_id)
            continue

        precio_unitario, nivel_precio = calcular_precio_unitario(producto, usuario, cantidad)
        subtotal = precio_unitario * cantidad
        total_general += subtotal

        lineas.append({
            "producto": producto,
            "cantidad": cantidad,
            "precio_unitario": precio_unitario,
            "nivel_precio": nivel_precio,
            "subtotal": subtotal,
        })

    # Limpieza silenciosa de referencias a productos que ya no existen/están inactivos
    if productos_invalidos:
        carrito = obtener_carrito_crudo()
        for producto_id in productos_invalidos:
            carrito.pop(str(producto_id), None)
        session.modified = True

    return lineas, total_general


def cantidad_total_items():
    return sum(obtener_carrito_crudo().values())
