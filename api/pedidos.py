from flask import request, jsonify
from app.extensions import db
from app.models_all import Pedido, Usuario
from app.api import api_bp

def obtener_usuario_autenticado():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ")[1]
    if token.startswith("token_dev_"):
        try:
            parts = token.split("_")
            usuario_id = int(parts[2])
            return db.session.get(Usuario, usuario_id)
        except (IndexError, ValueError):
            return None
    return None

@api_bp.route("/pedidos/mis-pedidos", methods=["GET"])
def mis_pedidos():
    usuario = obtener_usuario_autenticado()
    if not usuario:
        return jsonify({"error": "No autorizado. Token inválido o faltante."}), 401

    pedidos = Pedido.query.filter_by(usuario_id=usuario.id).order_by(Pedido.fecha_creacion.desc()).all()
    
    lista_pedidos = []
    for p in pedidos:
        lista_pedidos.append({
            "id_pedido": p.id,
            "estado": p.estado,
            "tipo_entrega": p.tipo_entrega,
            "costo_envio": float(p.costo_envio),
            "total": float(p.total),
            "fecha_creacion": p.fecha_creacion.strftime("%Y-%m-%d %H:%M"),
            "items_count": len(p.items)
        })

    return jsonify({
        "success": True,
        "pedidos": lista_pedidos
    })

@api_bp.route("/pedidos/<int:pedido_id>/tracking", methods=["GET"])
def tracking_pedido(pedido_id):
    usuario = obtener_usuario_autenticado()
    if not usuario:
        return jsonify({"error": "No autorizado. Token inválido o faltante."}), 401

    pedido = Pedido.query.filter_by(id=pedido_id, usuario_id=usuario.id).first()
    if not pedido:
        return jsonify({"error": "Pedido no encontrado."}), 404

    # Generamos la URL absoluta de la foto si existe
    foto_url = None
    if pedido.numero_guia_foto_url:
        foto_url = request.host_url.rstrip("/") + "/static/" + pedido.numero_guia_foto_url.lstrip("/")

    items_detalle = []
    for item in pedido.items:
        items_detalle.append({
            "nombre": item.nombre_producto,
            "cantidad": item.cantidad,
            "precio_unitario": float(item.precio_unitario),
            "subtotal": float(item.subtotal)
        })

    return jsonify({
        "success": True,
        "tracking": {
            "id_pedido": pedido.id,
            "estado": pedido.estado,
            "empresa_transporte": pedido.empresa_transporte,
            "numero_guia": pedido.numero_guia,
            "numero_guia_foto_url": foto_url,
            "fecha_creacion": pedido.fecha_creacion.strftime("%Y-%m-%d %H:%M"),
            "tipo_entrega": pedido.tipo_entrega,
            "direccion_envio": pedido.direccion_envio,
            "costo_envio": float(pedido.costo_envio),
            "subtotal": float(pedido.subtotal),
            "total": float(pedido.total),
            "items": items_detalle
        }
    })
