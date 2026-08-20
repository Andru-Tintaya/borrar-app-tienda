from datetime import datetime
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app.pedidos import pedidos_bp
from app.pedidos.utils_notificaciones import notificar_cambio_estado
from app.notas_venta.utils_numeracion import siguiente_numero_nota
from app.extensions import db
from app.models_all import Pedido, ESTADOS_PEDIDO
from app.utilidades import requiere_rol

ROLES_GESTION = ("Gerente", "Administrador", "Empleado")


# ---------------------------------------------------------------------------
# Gestión interna de pedidos (Flujo C de la especificación)
# ---------------------------------------------------------------------------
@pedidos_bp.route("/")
@login_required
@requiere_rol(*ROLES_GESTION)
def listar():
    estado_filtro = request.args.get("estado")
    consulta = Pedido.query
    if estado_filtro:
        consulta = consulta.filter_by(estado=estado_filtro)
    pedidos = consulta.order_by(Pedido.fecha_creacion.desc()).all()
    return render_template("pedidos/listar.html", pedidos=pedidos, estados=ESTADOS_PEDIDO, estado_filtro=estado_filtro)


@pedidos_bp.route("/<int:pedido_id>")
@login_required
@requiere_rol(*ROLES_GESTION)
def detalle(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    return render_template("pedidos/detalle.html", pedido=pedido)


@pedidos_bp.route("/<int:pedido_id>/verificar-pago", methods=["POST"])
@login_required
@requiere_rol(*ROLES_GESTION)
def verificar_pago(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    if pedido.estado != "Pendiente":
        flash("Este pedido ya fue procesado.", "warning")
        return redirect(url_for("pedidos.detalle", pedido_id=pedido.id))

    pedido.estado = "Pagado"
    pedido.verificado_por_id = current_user.id
    pedido.fecha_verificacion = datetime.utcnow()
    if pedido.numero_nota is None:
        pedido.numero_nota = siguiente_numero_nota()
    db.session.commit()

    notificar_cambio_estado(pedido)
    flash(f"Pago verificado. Nota de Venta N° {pedido.numero_nota} generada.", "success")
    return redirect(url_for("pedidos.detalle", pedido_id=pedido.id))


@pedidos_bp.route("/<int:pedido_id>/rechazar", methods=["POST"])
@login_required
@requiere_rol(*ROLES_GESTION)
def rechazar(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    pedido.estado = "Rechazado"
    db.session.commit()
    notificar_cambio_estado(pedido)
    flash("Pedido rechazado.", "info")
    return redirect(url_for("pedidos.detalle", pedido_id=pedido.id))


import os
from werkzeug.utils import secure_filename
from flask import current_app

@pedidos_bp.route("/<int:pedido_id>/despachar", methods=["POST"])
@login_required
@requiere_rol(*ROLES_GESTION)
def despachar(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    if pedido.estado != "Pagado":
        flash("El pedido debe estar Pagado antes de ser despachado.", "warning")
        return redirect(url_for("pedidos.detalle", pedido_id=pedido.id))

    empresa = request.form.get("empresa_transporte")
    guia = request.form.get("numero_guia")
    foto = request.files.get("numero_guia_foto")

    if not empresa or not guia:
        flash("La empresa de transporte y el número de guía son obligatorios.", "danger")
        return redirect(url_for("pedidos.detalle", pedido_id=pedido.id))

    foto_ruta_relativa = None
    if foto and foto.filename != "":
        nombre_archivo = secure_filename(f"guia_{pedido.id}_{foto.filename}")
        carpeta_destino = os.path.join(current_app.config["UPLOAD_FOLDER"], "guias")
        os.makedirs(carpeta_destino, exist_ok=True)
        foto.save(os.path.join(carpeta_destino, nombre_archivo))
        foto_ruta_relativa = f"uploads/guias/{nombre_archivo}"

    pedido.estado = "Despachado"
    pedido.empresa_transporte = empresa
    pedido.numero_guia = guia
    if foto_ruta_relativa:
        pedido.numero_guia_foto_url = foto_ruta_relativa
    
    db.session.commit()
    notificar_cambio_estado(pedido)
    flash("Pedido marcado como Despachado.", "success")
    return redirect(url_for("pedidos.detalle", pedido_id=pedido.id))


@pedidos_bp.route("/<int:pedido_id>/en-transito", methods=["POST"])
@login_required
@requiere_rol(*ROLES_GESTION)
def en_transito(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    if pedido.estado != "Despachado":
        flash("El pedido debe estar Despachado antes de pasar a En Tránsito.", "warning")
    else:
        pedido.estado = "En Tránsito"
        db.session.commit()
        notificar_cambio_estado(pedido)
        flash("Pedido marcado como En Tránsito.", "success")
    return redirect(url_for("pedidos.detalle", pedido_id=pedido.id))


@pedidos_bp.route("/<int:pedido_id>/entregado", methods=["POST"])
@login_required
@requiere_rol(*ROLES_GESTION)
def entregado(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    pedido.estado = "Entregado"
    db.session.commit()
    notificar_cambio_estado(pedido)
    flash("Pedido marcado como Entregado.", "success")
    return redirect(url_for("pedidos.detalle", pedido_id=pedido.id))


# ---------------------------------------------------------------------------
# Panel del cliente: "Mis Pedidos"
# ---------------------------------------------------------------------------
@pedidos_bp.route("/mis-pedidos")
@login_required
def mis_pedidos():
    if current_user.rol.es_personal_interno:
        return redirect(url_for("pedidos.listar"))

    pedidos = Pedido.query.filter_by(usuario_id=current_user.id).order_by(Pedido.fecha_creacion.desc()).all()
    return render_template("pedidos/mis_pedidos.html", pedidos=pedidos)
