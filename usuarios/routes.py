from flask import render_template, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from app.usuarios import usuarios_bp
from app.usuarios.forms import FormularioPersonal
from app.extensions import db, bcrypt
from app.models_all import Usuario, Rol, Pedido
from app.utilidades import requiere_rol


def _roles_personal_interno():
    return Rol.query.filter_by(es_personal_interno=True).all()


# ---------------------------------------------------------------------------
# Personal interno (CRUD) — solo Gerente y Administrador
# ---------------------------------------------------------------------------
@usuarios_bp.route("/")
@login_required
@requiere_rol("Gerente", "Administrador")
def listar_personal():
    personal = (
        Usuario.query.join(Rol)
        .filter(Rol.es_personal_interno.is_(True))
        .order_by(Usuario.nombre)
        .all()
    )
    return render_template("usuarios/listar_personal.html", personal=personal)


@usuarios_bp.route("/nuevo", methods=["GET", "POST"])
@login_required
@requiere_rol("Gerente", "Administrador")
def nuevo_personal():
    formulario = FormularioPersonal()
    formulario.rol_id.choices = [(r.id, r.nombre) for r in _roles_personal_interno()]

    if formulario.validate_on_submit():
        correo = formulario.correo.data.lower().strip()

        if Usuario.query.filter_by(correo=correo).first():
            flash("Ya existe una cuenta con ese correo.", "danger")
        elif not formulario.password.data:
            flash("La contraseña es obligatoria para crear un nuevo usuario de personal.", "danger")
        else:
            nuevo = Usuario(
                nombre=formulario.nombre.data.strip(),
                correo=correo,
                password=bcrypt.generate_password_hash(formulario.password.data).decode("utf-8"),
                rol_id=formulario.rol_id.data,
                activo=formulario.activo.data,
            )
            db.session.add(nuevo)
            db.session.commit()
            flash(f"Usuario de personal '{nuevo.nombre}' creado correctamente.", "success")
            return redirect(url_for("usuarios.listar_personal"))

    return render_template("usuarios/formulario_personal.html", formulario=formulario, modo="nuevo")


@usuarios_bp.route("/<int:usuario_id>/editar", methods=["GET", "POST"])
@login_required
@requiere_rol("Gerente", "Administrador")
def editar_personal(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    if usuario.es_cliente_externo():
        abort(404)

    formulario = FormularioPersonal(obj=usuario)
    formulario.rol_id.choices = [(r.id, r.nombre) for r in _roles_personal_interno()]

    if formulario.validate_on_submit():
        correo_nuevo = formulario.correo.data.lower().strip()
        existente = Usuario.query.filter_by(correo=correo_nuevo).first()
        if existente and existente.id != usuario.id:
            flash("Ese correo ya está en uso por otra cuenta.", "danger")
            return render_template("usuarios/formulario_personal.html", formulario=formulario, modo="editar", usuario=usuario)

        usuario.nombre = formulario.nombre.data.strip()
        usuario.correo = correo_nuevo
        usuario.rol_id = formulario.rol_id.data
        usuario.activo = formulario.activo.data
        if formulario.password.data:
            usuario.password = bcrypt.generate_password_hash(formulario.password.data).decode("utf-8")

        db.session.commit()
        flash(f"Usuario '{usuario.nombre}' actualizado correctamente.", "success")
        return redirect(url_for("usuarios.listar_personal"))

    return render_template("usuarios/formulario_personal.html", formulario=formulario, modo="editar", usuario=usuario)


@usuarios_bp.route("/<int:usuario_id>/alternar-estado", methods=["POST"])
@login_required
@requiere_rol("Gerente", "Administrador")
def alternar_estado_personal(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    if usuario.es_cliente_externo():
        abort(404)
    if usuario.id == current_user.id:
        flash("No puedes desactivar tu propia cuenta.", "warning")
        return redirect(url_for("usuarios.listar_personal"))

    usuario.activo = not usuario.activo
    db.session.commit()
    estado = "activada" if usuario.activo else "desactivada"
    flash(f"Cuenta de '{usuario.nombre}' {estado}.", "info")
    return redirect(url_for("usuarios.listar_personal"))


# ---------------------------------------------------------------------------
# Aprobación de cuentas B2B (Minorista / Mayorista) — Gerente y Administrador
# ---------------------------------------------------------------------------
@usuarios_bp.route("/aprobaciones-b2b")
@login_required
@requiere_rol("Gerente", "Administrador")
def aprobaciones_b2b():
    pendientes = (
        Usuario.query.filter_by(estado_aprobacion_b2b="Pendiente")
        .order_by(Usuario.fecha_creacion)
        .all()
    )
    return render_template("usuarios/aprobaciones_b2b.html", pendientes=pendientes)


@usuarios_bp.route("/aprobaciones-b2b/<int:usuario_id>/aprobar", methods=["POST"])
@login_required
@requiere_rol("Gerente", "Administrador")
def aprobar_b2b(usuario_id):
    cliente = Usuario.query.get_or_404(usuario_id)
    cliente.estado_aprobacion_b2b = "Aprobado"
    db.session.commit()
    flash(f"Cuenta B2B de '{cliente.nombre}' aprobada.", "success")
    return redirect(url_for("usuarios.aprobaciones_b2b"))


@usuarios_bp.route("/aprobaciones-b2b/<int:usuario_id>/rechazar", methods=["POST"])
@login_required
@requiere_rol("Gerente", "Administrador")
def rechazar_b2b(usuario_id):
    cliente = Usuario.query.get_or_404(usuario_id)
    cliente.estado_aprobacion_b2b = "Rechazado"
    db.session.commit()
    flash(f"Cuenta B2B de '{cliente.nombre}' rechazada.", "info")
    return redirect(url_for("usuarios.aprobaciones_b2b"))


@usuarios_bp.route("/<int:usuario_id>/eliminar", methods=["POST"])
@login_required
@requiere_rol("Gerente", "Administrador")
def eliminar_personal(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    if usuario.es_cliente_externo():
        abort(404)
    if usuario.id == current_user.id:
        flash("No puedes eliminar tu propia cuenta.", "warning")
        return redirect(url_for("usuarios.listar_personal"))

    tiene_verificaciones = Pedido.query.filter_by(verificado_por_id=usuario.id).first() is not None
    if tiene_verificaciones:
        flash(
            f"'{usuario.nombre}' no se puede eliminar: tiene pedidos verificados a su nombre (queda en el historial). "
            "Puedes desactivarlo en su lugar.",
            "danger",
        )
        return redirect(url_for("usuarios.listar_personal"))

    nombre = usuario.nombre
    db.session.delete(usuario)
    db.session.commit()
    flash(f"Usuario '{nombre}' eliminado.", "info")
    return redirect(url_for("usuarios.listar_personal"))
