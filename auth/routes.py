from flask import render_template, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user

from app.auth import auth_bp
from app.auth.forms import (
    LoginStaffForm, SolicitarOTPForm, VerificarOTPForm, RegistroClienteForm,
    SolicitarRecuperacionForm, VerificarRecuperacionForm, NuevaPasswordForm,
)
from app.auth.utils_otp import generar_codigo_otp, enviar_correo_otp, validar_codigo_otp
from app.extensions import db, bcrypt
from app.models_all import Usuario, Rol


@auth_bp.route("/")
def portal():
    """Portal de acceso: elegir entre ingreso de personal interno o de clientes."""
    if current_user.is_authenticated:
        if current_user.rol.es_personal_interno:
            return redirect(url_for("dashboard.index"))
        else:
            return redirect(url_for("tienda.catalogo"))
    return render_template("auth/portal.html")


# ---------------------------------------------------------------------------
# Personal interno (Gerente, Administrador, Empleado): correo + contraseña
# ---------------------------------------------------------------------------
@auth_bp.route("/personal/login", methods=["GET", "POST"])
def login_staff():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    formulario = LoginStaffForm()
    if formulario.validate_on_submit():
        usuario = Usuario.query.filter_by(correo=formulario.correo.data.lower().strip()).first()

        credenciales_validas = (
            usuario is not None
            and usuario.password is not None
            and bcrypt.check_password_hash(usuario.password, formulario.password.data)
        )

        if not credenciales_validas or usuario.es_cliente_externo():
            flash("Correo o contraseña incorrectos.", "danger")
        elif not usuario.activo:
            flash("Tu cuenta de personal está desactivada. Contacta a Gerencia.", "warning")
        else:
            login_user(usuario)
            flash(f"Bienvenido/a, {usuario.nombre}.", "success")
            return redirect(url_for("dashboard.index"))

    return render_template("auth/login_staff.html", formulario=formulario)


# ---------------------------------------------------------------------------
# Recuperación de contraseña — personal interno
# ("¿Olvidaste tu contraseña?" -> código de verificación por correo -> nueva contraseña)
# ---------------------------------------------------------------------------
@auth_bp.route("/personal/olvide-password", methods=["GET", "POST"])
def olvide_password():
    """Paso 1: el empleado/gerente/administrador escribe su correo y se le
    envía un código de verificación de 6 dígitos (misma infraestructura que
    el OTP de clientes; ver el comentario en utils_otp.enviar_correo_otp
    para conectar el envío real por Gmail/SMTP)."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    formulario = SolicitarRecuperacionForm()
    if formulario.validate_on_submit():
        correo = formulario.correo.data.lower().strip()
        usuario = Usuario.query.filter_by(correo=correo).first()

        if usuario is None or usuario.es_cliente_externo():
            flash("No encontramos una cuenta de personal con ese correo.", "danger")
            return render_template("auth/olvide_password.html", formulario=formulario)

        codigo = generar_codigo_otp(correo)
        enviar_correo_otp(correo, codigo)
        session["recuperacion_correo_pendiente"] = correo

        flash("Te enviamos un código de verificación a tu correo.", "info")
        return redirect(url_for("auth.verificar_recuperacion"))

    return render_template("auth/olvide_password.html", formulario=formulario)


@auth_bp.route("/personal/verificar-recuperacion", methods=["GET", "POST"])
def verificar_recuperacion():
    """Paso 2: valida el código recibido. Al confirmarlo, habilita (por
    sesión) el acceso de un solo uso al formulario de nueva contraseña."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    formulario = VerificarRecuperacionForm()
    if not formulario.correo.data:
        formulario.correo.data = session.get("recuperacion_correo_pendiente", "")

    if formulario.validate_on_submit():
        correo = formulario.correo.data.lower().strip()

        if not validar_codigo_otp(correo, formulario.codigo.data.strip()):
            flash("Código inválido o expirado. Solicita uno nuevo.", "danger")
            return render_template("auth/verificar_recuperacion.html", formulario=formulario)

        # Código correcto: se habilita, por sesión, el cambio de contraseña
        # para este correo (de un solo uso, se limpia al guardar la nueva).
        session["recuperacion_correo_verificado"] = correo
        session.pop("recuperacion_correo_pendiente", None)
        return redirect(url_for("auth.nueva_password"))

    return render_template("auth/verificar_recuperacion.html", formulario=formulario)


@auth_bp.route("/personal/nueva-password", methods=["GET", "POST"])
def nueva_password():
    """Paso 3: define la nueva contraseña. Solo accesible tras verificar el
    código del paso anterior en esta misma sesión de navegador."""
    correo = session.get("recuperacion_correo_verificado")
    if not correo:
        flash("Primero debes verificar tu código de recuperación.", "warning")
        return redirect(url_for("auth.olvide_password"))

    usuario = Usuario.query.filter_by(correo=correo).first()
    if usuario is None:
        session.pop("recuperacion_correo_verificado", None)
        return redirect(url_for("auth.olvide_password"))

    formulario = NuevaPasswordForm()
    if formulario.validate_on_submit():
        usuario.password = bcrypt.generate_password_hash(formulario.password.data).decode("utf-8")
        db.session.commit()
        session.pop("recuperacion_correo_verificado", None)
        flash("Contraseña actualizada. Ya puedes iniciar sesión.", "success")
        return redirect(url_for("auth.login_staff"))

    return render_template("auth/nueva_password.html", formulario=formulario)


# ---------------------------------------------------------------------------
# Clientes externos (Público, Minorista, Mayorista): registro + login OTP
# ---------------------------------------------------------------------------
@auth_bp.route("/cliente/registro", methods=["GET", "POST"])
def registro_cliente():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    formulario = RegistroClienteForm()
    if formulario.validate_on_submit():
        correo = formulario.correo.data.lower().strip()

        if Usuario.query.filter_by(correo=correo).first():
            flash("Ya existe una cuenta registrada con ese correo.", "danger")
            return render_template("auth/registro_cliente.html", formulario=formulario)

        tipo = formulario.tipo_cliente.data  # Publico | Minorista | Mayorista
        es_b2b = tipo in ("Minorista", "Mayorista", "Franquicia", "Asesora Libre")

        if es_b2b and (not formulario.nit_ci.data or not formulario.razon_social.data):
            flash("Para cuentas Minorista/Mayorista el NIT/CI y la razón social son obligatorios.", "danger")
            return render_template("auth/registro_cliente.html", formulario=formulario)

        rol = Rol.query.filter_by(nombre=f"Cliente {tipo}").first()

        cliente = Usuario(
            nombre=formulario.nombre.data.strip(),
            correo=correo,
            telefono=formulario.telefono.data.strip(),
            ciudad=formulario.ciudad.data.strip() if formulario.ciudad.data else None,
            rol_id=rol.id,
            activo=True,
            nit_ci=formulario.nit_ci.data.strip() if es_b2b else None,
            razon_social=formulario.razon_social.data.strip() if es_b2b else None,
            nivel_b2b_solicitado=tipo if es_b2b else None,
            estado_aprobacion_b2b="Pendiente" if es_b2b else None,
        )
        db.session.add(cliente)
        db.session.commit()

        if es_b2b:
            flash(
                "Registro recibido. Tu cuenta B2B queda pendiente de aprobación por Gerencia/Administración "
                "antes de poder acceder a precios Minorista/Mayorista.",
                "info",
            )
        else:
            flash("Registro exitoso. Ya puedes iniciar sesión con tu correo.", "success")
        return redirect(url_for("auth.login_cliente"))

    return render_template("auth/registro_cliente.html", formulario=formulario)


@auth_bp.route("/cliente/login", methods=["GET", "POST"])
def login_cliente():
    """Paso 1: el cliente pide un código OTP a su correo."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    formulario = SolicitarOTPForm()
    if formulario.validate_on_submit():
        correo = formulario.correo.data.lower().strip()
        usuario = Usuario.query.filter_by(correo=correo).first()

        if usuario is None or not usuario.es_cliente_externo():
            flash("No encontramos una cuenta de cliente con ese correo. ¿Ya te registraste?", "danger")
            return render_template("auth/login_cliente.html", formulario=formulario)

        codigo = generar_codigo_otp(correo)
        enviar_correo_otp(correo, codigo)
        session["otp_correo_pendiente"] = correo

        flash("Te enviamos un código de verificación a tu correo.", "info")
        return redirect(url_for("auth.verificar_otp"))

    return render_template("auth/login_cliente.html", formulario=formulario)


@auth_bp.route("/cliente/verificar", methods=["GET", "POST"])
def verificar_otp():
    """Paso 2: el cliente ingresa el código OTP recibido para iniciar sesión."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    formulario = VerificarOTPForm()
    if not formulario.correo.data:
        formulario.correo.data = session.get("otp_correo_pendiente", "")

    if formulario.validate_on_submit():
        correo = formulario.correo.data.lower().strip()

        if not validar_codigo_otp(correo, formulario.codigo.data.strip()):
            flash("Código inválido o expirado. Solicita uno nuevo.", "danger")
            return render_template("auth/verificar_otp.html", formulario=formulario)

        usuario = Usuario.query.filter_by(correo=correo).first()
        if usuario is None or not usuario.es_cliente_externo():
            flash("Cuenta de cliente no encontrada.", "danger")
            return redirect(url_for("auth.login_cliente"))

        if not usuario.activo:
            flash("Tu cuenta está desactivada. Contacta con la tienda.", "warning")
            return redirect(url_for("auth.login_cliente"))

        login_user(usuario)
        session.pop("otp_correo_pendiente", None)
        flash(f"Bienvenido/a, {usuario.nombre}.", "success")
        if usuario.rol.es_personal_interno:
            return redirect(url_for("dashboard.index"))
        else:
            return redirect(url_for("tienda.catalogo"))

    return render_template("auth/verificar_otp.html", formulario=formulario)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("auth.portal"))
