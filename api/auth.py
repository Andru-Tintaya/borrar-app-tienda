from datetime import datetime
from flask import request, jsonify
from app.extensions import db, bcrypt
from app.models_all import Usuario, Rol
from app.auth.utils_otp import generar_codigo_otp, validar_codigo_otp
from app.api import api_bp

# Simulación de envío de OTP por WhatsApp
def enviar_whatsapp_otp(telefono: str, codigo: str) -> None:
    print(f"[NAHARA][WHATSAPP-OTP] Código para {telefono}: {codigo} (válido 10 min)")

@api_bp.route("/auth/registro", methods=["POST"])
def registro():
    datos = request.get_json() or {}
    nombre = datos.get("nombre")
    correo = datos.get("correo")
    telefono = datos.get("telefono")
    password = datos.get("password")
    tipo_cliente = datos.get("tipo_cliente", "Publico") # Publico | Mayorista
    ciudad = datos.get("ciudad")
    nit_ci = datos.get("nit_ci")
    razon_social = datos.get("razon_social")

    if not nombre or not correo or not telefono or not password:
        return jsonify({"error": "Nombre, correo, teléfono y contraseña son obligatorios."}), 400

    if Usuario.query.filter_by(correo=correo.lower().strip()).first():
        return jsonify({"error": "Ya existe una cuenta con ese correo electrónico."}), 400

    if Usuario.query.filter_by(telefono=telefono.strip()).first():
        return jsonify({"error": "Ya existe una cuenta con ese número de teléfono."}), 400

    es_b2b = tipo_cliente in ("Minorista", "Mayorista", "Franquicia", "Asesora Libre")
    if es_b2b and (not nit_ci or not razon_social):
        return jsonify({"error": "Para cuentas mayoristas, el NIT/CI y la Razón Social son requeridos."}), 400

    nombre_rol = f"Cliente {tipo_cliente}"
    rol = Rol.query.filter_by(nombre=nombre_rol).first()
    if not rol:
        # Fallback a Cliente Publico si el rol específico no se encuentra
        rol = Rol.query.filter_by(nombre="Cliente Publico").first()

    nuevo_usuario = Usuario(
        nombre=nombre.strip(),
        correo=correo.lower().strip(),
        telefono=telefono.strip(),
        password=bcrypt.generate_password_hash(password).decode("utf-8"),
        ciudad=ciudad.strip() if ciudad else None,
        rol_id=rol.id if rol else 1,
        activo=True,
        nit_ci=nit_ci.strip() if es_b2b else None,
        razon_social=razon_social.strip() if es_b2b else None,
        nivel_b2b_solicitado=tipo_cliente if es_b2b else None,
        estado_aprobacion_b2b="Pendiente" if es_b2b else None
    )

    db.session.add(nuevo_usuario)
    db.session.commit()

    return jsonify({
        "success": True,
        "mensaje": "Usuario registrado con éxito.",
        "usuario": {
            "id": nuevo_usuario.id,
            "nombre": nuevo_usuario.nombre,
            "correo": nuevo_usuario.correo,
            "telefono": nuevo_usuario.telefono,
            "rol": nuevo_usuario.rol.nombre if nuevo_usuario.rol else "Cliente Publico",
            "estado_aprobacion_b2b": nuevo_usuario.estado_aprobacion_b2b
        }
    }), 201

@api_bp.route("/auth/solicitar-otp", methods=["POST"])
def solicitar_otp():
    datos = request.get_json() or {}
    telefono = datos.get("telefono")

    if not telefono:
        return jsonify({"error": "El número de teléfono es obligatorio."}), 400

    usuario = Usuario.query.filter_by(telefono=telefono.strip()).first()
    if not usuario:
        return jsonify({"error": "No hay ningún usuario registrado con ese número de teléfono."}), 404

    # Generamos un código OTP usando el teléfono como identificador
    codigo = generar_codigo_otp(telefono.strip())
    enviar_whatsapp_otp(telefono.strip(), codigo)

    return jsonify({
        "success": True,
        "mensaje": "Código OTP enviado por WhatsApp."
    })

@api_bp.route("/auth/verificar-otp", methods=["POST"])
def verificar_otp():
    datos = request.get_json() or {}
    telefono = datos.get("telefono")
    codigo = datos.get("codigo")

    if not telefono or not codigo:
        return jsonify({"error": "El teléfono y el código son obligatorios."}), 400

    if not validar_codigo_otp(telefono.strip(), codigo.strip()):
        return jsonify({"error": "Código OTP inválido o expirado."}), 400

    usuario = Usuario.query.filter_by(telefono=telefono.strip()).first()
    if not usuario:
        return jsonify({"error": "Usuario no encontrado."}), 404

    if not usuario.activo:
        return jsonify({"error": "Esta cuenta está desactivada."}), 403

    # Retornar datos de sesión. Generamos un token simulado para el cliente Flutter.
    token = f"token_dev_{usuario.id}_{int(datetime.utcnow().timestamp())}"

    return jsonify({
        "success": True,
        "token": token,
        "usuario": {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "correo": usuario.correo,
            "telefono": usuario.telefono,
            "rol": usuario.rol.nombre if usuario.rol else "Cliente Publico",
            "estado_aprobacion_b2b": usuario.estado_aprobacion_b2b
        }
    })

@api_bp.route("/auth/login-telefono", methods=["POST"])
def login_telefono():
    datos = request.get_json() or {}
    telefono = datos.get("telefono")
    password = datos.get("password")

    if not telefono or not password:
        return jsonify({"error": "El teléfono y la contraseña son obligatorios."}), 400

    usuario = Usuario.query.filter_by(telefono=telefono.strip()).first()
    if not usuario or not usuario.password:
        return jsonify({"error": "Teléfono o contraseña incorrectos."}), 401

    if not bcrypt.check_password_hash(usuario.password, password):
        return jsonify({"error": "Teléfono o contraseña incorrectos."}), 401

    if not usuario.activo:
        return jsonify({"error": "Esta cuenta está desactivada."}), 403

    token = f"token_dev_{usuario.id}_{int(datetime.utcnow().timestamp())}"

    return jsonify({
        "success": True,
        "token": token,
        "usuario": {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "correo": usuario.correo,
            "telefono": usuario.telefono,
            "rol": usuario.rol.nombre if usuario.rol else "Cliente Publico",
            "estado_aprobacion_b2b": usuario.estado_aprobacion_b2b
        }
    })

@api_bp.route("/auth/google", methods=["POST"])
def login_google():
    datos = request.get_json() or {}
    correo = datos.get("correo")
    nombre = datos.get("nombre")
    google_id = datos.get("google_id")

    if not correo or not google_id or not nombre:
        return jsonify({"error": "Correo, nombre y google_id son requeridos."}), 400

    # Buscar usuario por google_id o por correo
    usuario = Usuario.query.filter(
        (Usuario.google_id == google_id) | (Usuario.correo == correo.lower().strip())
    ).first()

    if not usuario:
        # Registrar nuevo usuario público
        rol = Rol.query.filter_by(nombre="Cliente Publico").first()
        usuario = Usuario(
            nombre=nombre.strip(),
            correo=correo.lower().strip(),
            google_id=google_id,
            rol_id=rol.id if rol else 1,
            activo=True
        )
        db.session.add(usuario)
        db.session.commit()
    else:
        # Si ya existía por correo pero no tenía google_id, lo vinculamos
        if not usuario.google_id:
            usuario.google_id = google_id
            db.session.commit()

    if not usuario.activo:
        return jsonify({"error": "Esta cuenta está desactivada."}), 403

    token = f"token_dev_{usuario.id}_{int(datetime.utcnow().timestamp())}"

    return jsonify({
        "success": True,
        "token": token,
        "usuario": {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "correo": usuario.correo,
            "telefono": usuario.telefono,
            "rol": usuario.rol.nombre if usuario.rol else "Cliente Publico",
            "estado_aprobacion_b2b": usuario.estado_aprobacion_b2b
        }
    })
