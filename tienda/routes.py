import os
import uuid
from datetime import datetime, timedelta
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app.models_all import Categoria, Subcategoria, Producto, Color, Banner

from app.tienda import tienda_bp
from app.tienda.forms import CheckoutForm
from app.tienda.utils_precios import calcular_precio_unitario
from app.tienda.utils_moneda import obtener_tipo_cambio
from app.tienda.utils_carrito import (
    agregar_al_carrito, actualizar_cantidad_carrito, eliminar_del_carrito,
    vaciar_carrito, calcular_resumen_carrito,
)
from app.productos.utils_imagenes import extension_permitida
from app.productos.utils_mas_vendidos import obtener_ids_mas_vendidos
from app.extensions import db
from app.models_all import (
    Producto, Categoria, Color, ConfiguracionPagoQR, ConfiguracionEmpresa, Pedido, ItemPedido,
    DIAS_PRODUCTO_NUEVO, MetodoEnvio,
)
from app.utilidades import requiere_rol

LIMITE_SECCIONES_HOME = 8


# ---------------------------------------------------------------------------
# Catálogo (también es la página de inicio de la tienda)
# ---------------------------------------------------------------------------
@tienda_bp.route("/")
def catalogo():
    consulta = Producto.query.filter(Producto.activo.is_(True))

    q = request.args.get("q", "").strip()
    if q:
        consulta = consulta.filter(
            db.or_(Producto.nombre.ilike(f"%{q}%"), Producto.descripcion.ilike(f"%{q}%"))
        )

    categoria_id = request.args.get("categoria_id", type=int)
    if categoria_id:
        consulta = consulta.filter(Producto.categoria_id == categoria_id)

    subcategoria_id = request.args.get("subcategoria_id", type=int)
    if subcategoria_id:
        consulta = consulta.filter(Producto.subcategoria_id == subcategoria_id)

    color_id = request.args.get("color_id", type=int)
    if color_id:
        consulta = consulta.filter(Producto.color_id == color_id)

    disponibilidad = request.args.get("disponibilidad")
    if disponibilidad == "en_existencia":
        consulta = consulta.filter(Producto.stock > 0)
    elif disponibilidad == "agotado":
        consulta = consulta.filter(Producto.stock <= 0)

    if request.args.get("nuevo"):
        limite_nuevo = datetime.utcnow() - timedelta(days=DIAS_PRODUCTO_NUEVO)
        consulta = consulta.filter(Producto.fecha_creacion >= limite_nuevo)
    if request.args.get("destacado"):
        consulta = consulta.filter(Producto.es_destacado.is_(True))
    if request.args.get("oferta"):
        consulta = consulta.filter(Producto.en_oferta.is_(True))

    ids_mas_vendidos = obtener_ids_mas_vendidos()
    if request.args.get("mas_vendido"):
        consulta = consulta.filter(Producto.id.in_(ids_mas_vendidos) if ids_mas_vendidos else db.false())

    orden = request.args.get("orden", "relevancia")
    if orden == "az":
        consulta = consulta.order_by(Producto.nombre.asc())
    elif orden == "za":
        consulta = consulta.order_by(Producto.nombre.desc())
    elif orden == "precio_asc":
        consulta = consulta.order_by(Producto.precio_minorista_usd.asc())
    elif orden == "precio_desc":
        consulta = consulta.order_by(Producto.precio_minorista_usd.desc())
    elif orden == "fecha":
        consulta = consulta.order_by(Producto.fecha_creacion.desc())
    else:
        consulta = consulta.order_by(Producto.fecha_creacion.desc())

    productos = consulta.all()
    categorias = Categoria.query.filter_by(activo=True).order_by(Categoria.nombre).all()
    colores = Color.query.order_by(Color.nombre).all()

    # Las secciones "Destacados" / "Novedades" de la portada solo se
    # muestran en la visita limpia a la tienda (sin filtros activos), para
    # no confundirlas con resultados de búsqueda/filtro.
    hay_filtros_activos = any([
        q, categoria_id, subcategoria_id, disponibilidad, color_id,
        request.args.get("nuevo"), request.args.get("destacado"),
        request.args.get("oferta"), request.args.get("mas_vendido"),
    ])
    destacados_home, novedades_home = [], []
    if not hay_filtros_activos:
        destacados_home = (
            Producto.query.filter_by(activo=True, es_destacado=True)
            .order_by(Producto.fecha_creacion.desc()).limit(LIMITE_SECCIONES_HOME).all()
        )
        novedades_home = (
            Producto.query.filter(
                Producto.activo.is_(True),
                Producto.fecha_creacion >= datetime.utcnow() - timedelta(days=DIAS_PRODUCTO_NUEVO),
            ).order_by(Producto.fecha_creacion.desc()).limit(LIMITE_SECCIONES_HOME).all()
        )

    # ════════════════════════════════════════════════════════════════
    # OBTENER BANNERS ACTIVOS PARA EL CARRUSEL
    # ════════════════════════════════════════════════════════════════
    banners = Banner.query.filter_by(activo=True).order_by(Banner.orden.asc()).all()

    return render_template(
        "tienda/catalogo.html",
        productos=productos,
        categorias=categorias,
        colores=colores,
        calcular_precio_unitario=calcular_precio_unitario,
        ids_mas_vendidos=ids_mas_vendidos,
        hay_filtros_activos=hay_filtros_activos,
        destacados_home=destacados_home,
        novedades_home=novedades_home,
        busqueda=q,
        categoria_id_actual=categoria_id,
        color_id_actual=color_id,
        categorias_home=categorias,
        banners=banners,  # ← NUEVO: Banners para el carrusel
    )


@tienda_bp.route("/producto/<int:producto_id>")
def producto_detalle(producto_id):
    producto = Producto.query.filter(Producto.id == producto_id, Producto.activo.is_(True)).first_or_404()

    precio_unitario, nivel_precio = calcular_precio_unitario(producto, current_user, 0)

    recomendados = (
        Producto.query.filter(
            Producto.categoria_id == producto.categoria_id,
            Producto.id != producto.id,
            Producto.activo.is_(True),
        ).limit(4).all()
    )

    return render_template(
        "tienda/producto_detalle.html",
        producto=producto,
        precio_unitario=precio_unitario,
        nivel_precio=nivel_precio,
        recomendados=recomendados,
        umbral_mayorista=current_app.config["UMBRAL_PRECIO_MAYORISTA"],
        ids_mas_vendidos=obtener_ids_mas_vendidos(),
    )


# ---------------------------------------------------------------------------
# Carrito (mini-cart deslizable)
# ---------------------------------------------------------------------------
@tienda_bp.route("/carrito/agregar", methods=["POST"])
def agregar_carrito():
    producto_id = request.form.get("producto_id", type=int)
    cantidad = request.form.get("cantidad", type=int) or 1

    producto = Producto.query.get_or_404(producto_id)

    if not producto.activo or producto.stock <= 0:
        flash("Ese producto no está disponible en este momento.", "danger")
    else:
        agregar_al_carrito(producto_id, cantidad)
        flash(f"'{producto.nombre}' agregado al carrito.", "success")

    return redirect(request.referrer or url_for("tienda.catalogo"))


@tienda_bp.route("/carrito/actualizar", methods=["POST"])
def actualizar_carrito():
    producto_id = request.form.get("producto_id", type=int)
    cantidad = request.form.get("cantidad", type=int) or 0
    actualizar_cantidad_carrito(producto_id, cantidad)
    return redirect(url_for("tienda.ver_carrito"))


@tienda_bp.route("/carrito/eliminar", methods=["POST"])
def eliminar_carrito():
    producto_id = request.form.get("producto_id", type=int)
    eliminar_del_carrito(producto_id)
    flash("Producto eliminado del carrito.", "info")
    return redirect(url_for("tienda.ver_carrito"))


@tienda_bp.route("/carrito")
def ver_carrito():
    lineas, total = calcular_resumen_carrito(current_user)
    return render_template("tienda/carrito.html", lineas=lineas, total=total, umbral_mayorista=current_app.config["UMBRAL_PRECIO_MAYORISTA"])


# ---------------------------------------------------------------------------
# Checkout y pago por QR / Transferencia
# ---------------------------------------------------------------------------
@tienda_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    lineas, total = calcular_resumen_carrito(current_user)
    if not lineas:
        flash("Tu carrito está vacío.", "warning")
        return redirect(url_for("tienda.catalogo"))

    formulario = CheckoutForm()
    configuracion_qr = ConfiguracionPagoQR.query.first()
    metodos_envio = MetodoEnvio.query.filter_by(activo=True).order_by(MetodoEnvio.costo).all()

    if formulario.validate_on_submit():
        comprobante = request.files.get("comprobante")
        ruta_comprobante = None

        if comprobante and comprobante.filename:
            if not extension_permitida(comprobante.filename):
                flash("El comprobante debe ser una imagen (jpg, jpeg, png o webp).", "danger")
                return render_template(
                    "tienda/checkout.html", formulario=formulario, lineas=lineas, total=total,
                    configuracion_qr=configuracion_qr, metodos_envio=metodos_envio,
                )
            carpeta = os.path.join(current_app.config["UPLOAD_FOLDER"], "comprobantes")
            os.makedirs(carpeta, exist_ok=True)
            extension = comprobante.filename.rsplit(".", 1)[1].lower()
            nombre_unico = f"{uuid.uuid4().hex}.{extension}"
            comprobante.save(os.path.join(carpeta, nombre_unico))
            ruta_comprobante = f"uploads/comprobantes/{nombre_unico}"

        # Costo de envío: solo aplica si el cliente eligió "Envio" y escogió un método
        costo_envio = 0
        metodo_envio_nombre = None
        if formulario.tipo_entrega.data == "Envio":
            metodo_envio_id = request.form.get("metodo_envio_id", type=int)
            metodo = MetodoEnvio.query.filter_by(id=metodo_envio_id, activo=True).first() if metodo_envio_id else None
            if metodo:
                costo_envio = float(metodo.costo)
                metodo_envio_nombre = metodo.nombre

        total_con_envio = float(total) + costo_envio

        # Determina el nivel de precio predominante del pedido (el de mayor línea)
        nivel_precio_pedido = max(lineas, key=lambda l: l["subtotal"])["nivel_precio"] if lineas else "Minorista"
        tipo_cambio_hoy = obtener_tipo_cambio()

        pedido = Pedido(
            usuario_id=current_user.id,
            nivel_precio=nivel_precio_pedido,
            tipo_entrega=formulario.tipo_entrega.data,
            direccion_envio=formulario.direccion_envio.data,
            metodo_envio_nombre=metodo_envio_nombre,
            costo_envio=costo_envio,
            nota=formulario.nota.data,
            tipo_cambio_aplicado=tipo_cambio_hoy,
            subtotal=total,
            total=total_con_envio,
            comprobante_pago=ruta_comprobante,
            estado="Pendiente",
        )
        db.session.add(pedido)
        db.session.flush()

        for linea in lineas:
            producto_linea = linea["producto"]
            db.session.add(ItemPedido(
                pedido_id=pedido.id,
                producto_id=producto_linea.id,
                nombre_producto=producto_linea.nombre,
                cantidad=linea["cantidad"],
                precio_unitario=linea["precio_unitario"],
                precio_unitario_usd=producto_linea.precio_final_usd(linea["nivel_precio"]),
                precio_compra_unitario_usd=producto_linea.precio_compra_usd,
                subtotal=linea["subtotal"],
                nivel_precio=linea["nivel_precio"],
            ))

        db.session.commit()
        vaciar_carrito()

        flash("¡Pedido registrado! Verificaremos tu pago y te contactaremos.", "success")
        return redirect(url_for("tienda.confirmacion_pedido", pedido_id=pedido.id))

    return render_template(
        "tienda/checkout.html", formulario=formulario, lineas=lineas, total=total, configuracion_qr=configuracion_qr,
        metodos_envio=metodos_envio,
    )


@tienda_bp.route("/pedido/<int:pedido_id>/confirmacion")
@login_required
def confirmacion_pedido(pedido_id):
    pedido = Pedido.query.filter_by(id=pedido_id, usuario_id=current_user.id).first_or_404()
    return render_template("tienda/confirmacion.html", pedido=pedido)


# ---------------------------------------------------------------------------
# Configuración del QR institucional (Gerente / Administrador)
# ---------------------------------------------------------------------------
@tienda_bp.route("/actualizar-tipo-cambio", methods=["POST"])
@login_required
@requiere_rol("Gerente", "Administrador")
def actualizar_tipo_cambio():
    nuevo_valor = request.form.get("tipo_cambio_usd", type=float)
    if not nuevo_valor or nuevo_valor <= 0:
        flash("Ingresa un tipo de cambio válido.", "danger")
        return redirect(url_for("tienda.configurar_pago_qr"))

    empresa = ConfiguracionEmpresa.query.first()
    if empresa is None:
        empresa = ConfiguracionEmpresa()
        db.session.add(empresa)

    empresa.tipo_cambio_usd = nuevo_valor
    empresa.tipo_cambio_actualizado = datetime.utcnow()
    db.session.commit()
    flash(f"Tipo de cambio actualizado a {nuevo_valor} Bs./USD. Todos los precios en Bs. ya se recalcularon.", "success")
    return redirect(url_for("tienda.configurar_pago_qr"))


@tienda_bp.route("/configurar-pago-qr", methods=["GET", "POST"])
@login_required
@requiere_rol("Gerente", "Administrador")
def configurar_pago_qr():
    configuracion = ConfiguracionPagoQR.query.first()
    if configuracion is None:
        configuracion = ConfiguracionPagoQR()
        db.session.add(configuracion)
        db.session.commit()

    empresa = ConfiguracionEmpresa.query.first()
    if empresa is None:
        empresa = ConfiguracionEmpresa()
        db.session.add(empresa)
        db.session.commit()

    if request.method == "POST":
        configuracion.nombre_beneficiario = request.form.get("nombre_beneficiario", "").strip()
        configuracion.numero_cuenta = request.form.get("numero_cuenta", "").strip()
        configuracion.banco = request.form.get("banco", "").strip()

        empresa.nombre_comercial = request.form.get("nombre_comercial", "NAHARA").strip() or "NAHARA"
        empresa.direccion = request.form.get("direccion", "").strip()
        empresa.nit = request.form.get("nit", "").strip()
        empresa.celular = request.form.get("celular_empresa", "").strip()
        empresa.ciudad = request.form.get("ciudad_empresa", "").strip()

        archivo_qr = request.files.get("imagen_qr")
        if archivo_qr and archivo_qr.filename:
            if extension_permitida(archivo_qr.filename):
                carpeta = os.path.join(current_app.config["UPLOAD_FOLDER"], "qr")
                os.makedirs(carpeta, exist_ok=True)
                extension = archivo_qr.filename.rsplit(".", 1)[1].lower()
                nombre_unico = f"{uuid.uuid4().hex}.{extension}"
                archivo_qr.save(os.path.join(carpeta, nombre_unico))
                configuracion.ruta_imagen_qr = f"uploads/qr/{nombre_unico}"
            else:
                flash("La imagen del QR debe ser jpg, jpeg, png o webp.", "danger")

        db.session.commit()
        flash("Configuración actualizada.", "success")
        return redirect(url_for("tienda.configurar_pago_qr"))

    return render_template("tienda/configurar_qr.html", configuracion=configuracion, empresa=empresa)


# ---------------------------------------------------------------------------
# Métodos de envío (Gerente / Administrador): costo terrestre/aéreo, se
# actualiza manualmente según lo que cobren las empresas de transporte.
# ---------------------------------------------------------------------------
@tienda_bp.route("/metodos-envio", methods=["GET", "POST"])
@login_required
@requiere_rol("Gerente", "Administrador")
def metodos_envio():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        costo = request.form.get("costo", type=float)
        if not nombre or costo is None or costo < 0:
            flash("Ingresa un nombre y un costo válido.", "danger")
        else:
            db.session.add(MetodoEnvio(nombre=nombre, costo=costo, activo=True))
            db.session.commit()
            flash(f"Método de envío '{nombre}' agregado.", "success")
        return redirect(url_for("tienda.metodos_envio"))

    metodos = MetodoEnvio.query.order_by(MetodoEnvio.activo.desc(), MetodoEnvio.nombre).all()
    return render_template("tienda/metodos_envio.html", metodos=metodos)


@tienda_bp.route("/metodos-envio/<int:metodo_id>/actualizar-costo", methods=["POST"])
@login_required
@requiere_rol("Gerente", "Administrador")
def actualizar_costo_envio(metodo_id):
    metodo = MetodoEnvio.query.get_or_404(metodo_id)
    costo = request.form.get("costo", type=float)
    if costo is None or costo < 0:
        flash("Ingresa un costo válido.", "danger")
    else:
        metodo.costo = costo
        db.session.commit()
        flash(f"Costo de '{metodo.nombre}' actualizado a Bs. {costo:.2f}.", "success")
    return redirect(url_for("tienda.metodos_envio"))


@tienda_bp.route("/metodos-envio/<int:metodo_id>/alternar", methods=["POST"])
@login_required
@requiere_rol("Gerente", "Administrador")
def alternar_metodo_envio(metodo_id):
    metodo = MetodoEnvio.query.get_or_404(metodo_id)
    metodo.activo = not metodo.activo
    db.session.commit()
    flash(f"'{metodo.nombre}' {'activado' if metodo.activo else 'desactivado'}.", "info")
    return redirect(url_for("tienda.metodos_envio"))


@tienda_bp.route("/politica-privacidad")
def politica_privacidad():
    return render_template("tienda/politica_privacidad.html")