from datetime import datetime
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app.productos import productos_bp
from app.productos.forms import ProductoForm
from app.productos.utils_imagenes import guardar_imagenes_producto, eliminar_imagen_producto
from app.productos.utils_mas_vendidos import obtener_ids_mas_vendidos
from app.productos.utils_sku import generar_sku
from app.tienda.utils_moneda import obtener_tipo_cambio
from app.extensions import db
from app.models_all import Producto, ProductoImagen, Categoria, Subcategoria, Color, ItemPedido, NIVELES_PRECIO
from app.utilidades import requiere_rol

ROLES_GESTION = ("Gerente", "Administrador", "Empleado")
ROLES_COSTO = ("Gerente", "Administrador")  # solo ellos ven Precio de Compra
CAMPOS_PRECIO_VENTA = ["precio_minorista_usd", "precio_mayorista_usd", "precio_franquicia_usd", "precio_asesora_libre_usd"]


def _cargar_choices(formulario, categoria_id_actual=None):
    formulario.categoria_id.choices = [(c.id, c.nombre) for c in Categoria.query.order_by(Categoria.nombre).all()]
    subcats = Subcategoria.query
    if categoria_id_actual:
        subcats = subcats.filter_by(categoria_id=categoria_id_actual)
    formulario.subcategoria_id.choices = [(0, "— Sin subcategoría —")] + [
        (s.id, s.nombre) for s in subcats.order_by(Subcategoria.nombre).all()
    ]
    formulario.color_id.choices = [(0, "— Sin color —")] + [
        (c.id, c.nombre) for c in Color.query.order_by(Color.nombre).all()
    ]


def _precios_completos(formulario):
    return all(getattr(formulario, campo).data is not None for campo in ["precio_compra_usd"] + CAMPOS_PRECIO_VENTA)


@productos_bp.route("/")
@login_required
@requiere_rol(*ROLES_GESTION)
def listar():
    productos = Producto.query.order_by(Producto.fecha_creacion.desc()).all()
    ids_mas_vendidos = obtener_ids_mas_vendidos()
    return render_template(
        "productos/listar.html", productos=productos, ids_mas_vendidos=ids_mas_vendidos,
        puede_ver_costo=current_user.tiene_rol(*ROLES_COSTO), tipo_cambio=obtener_tipo_cambio(),
    )


@productos_bp.route("/nuevo", methods=["GET", "POST"])
@login_required
@requiere_rol(*ROLES_GESTION)
def nuevo():
    if not current_user.tiene_rol(*ROLES_COSTO):
        flash("Solo Gerencia/Administración pueden crear productos (definen el Precio de Compra).", "warning")
        return redirect(url_for("productos.listar"))

    formulario = ProductoForm()
    _cargar_choices(formulario, request.form.get("categoria_id", type=int))
    tipo_cambio = obtener_tipo_cambio()

    if formulario.validate_on_submit():
        if not _precios_completos(formulario):
            flash("Completa el Precio de Compra y los 4 precios de venta (Minorista, Mayorista, Franquicia, Asesora Libre).", "danger")
            return render_template("productos/formulario.html", formulario=formulario, modo="nuevo", puede_ver_costo=True, tipo_cambio=tipo_cambio)

        producto = Producto(
            nombre=formulario.nombre.data.strip(),
            sku=generar_sku(),
            descripcion=formulario.descripcion.data,
            categoria_id=formulario.categoria_id.data,
            subcategoria_id=formulario.subcategoria_id.data or None,
            color_id=formulario.color_id.data or None,
            precio_compra_usd=formulario.precio_compra_usd.data,
            tipo_cambio_al_comprar=tipo_cambio,
            fecha_actualizacion_compra=datetime.utcnow(),
            precio_minorista_usd=formulario.precio_minorista_usd.data,
            precio_mayorista_usd=formulario.precio_mayorista_usd.data,
            precio_franquicia_usd=formulario.precio_franquicia_usd.data,
            precio_asesora_libre_usd=formulario.precio_asesora_libre_usd.data,
            minorista_habilitado=formulario.minorista_habilitado.data,
            mayorista_habilitado=formulario.mayorista_habilitado.data,
            franquicia_habilitado=formulario.franquicia_habilitado.data,
            asesora_libre_habilitado=formulario.asesora_libre_habilitado.data,
            stock=formulario.stock.data,
            activo=formulario.activo.data,
            es_destacado=formulario.es_destacado.data,
            en_oferta=formulario.en_oferta.data,
            porcentaje_descuento=formulario.porcentaje_descuento.data if formulario.en_oferta.data else None,
            creado_por_id=current_user.id,
        )
        db.session.add(producto)
        db.session.commit()

        archivos = request.files.getlist("fotos")
        guardar_imagenes_producto(producto, archivos)

        flash(f"Producto '{producto.nombre}' creado con SKU {producto.sku}.", "success")
        return redirect(url_for("productos.editar", producto_id=producto.id))

    return render_template("productos/formulario.html", formulario=formulario, modo="nuevo", puede_ver_costo=True, tipo_cambio=tipo_cambio)


@productos_bp.route("/<int:producto_id>/editar", methods=["GET", "POST"])
@login_required
@requiere_rol(*ROLES_GESTION)
def editar(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    puede_ver_costo = current_user.tiene_rol(*ROLES_COSTO)
    tipo_cambio = obtener_tipo_cambio()

    formulario = ProductoForm(obj=producto)
    if request.method == "GET":
        formulario.subcategoria_id.data = producto.subcategoria_id or 0
        formulario.color_id.data = producto.color_id or 0

    _cargar_choices(formulario, request.form.get("categoria_id", type=int) or producto.categoria_id)

    if formulario.validate_on_submit():
        # Los precios son obligatorios SOLO para quien puede verlos
        # (Gerente/Administrador); un Empleado edita todo lo demás sin
        # tocar el Precio de Compra ni los 4 precios de venta.
        if puede_ver_costo and not _precios_completos(formulario):
            flash("Completa el Precio de Compra y los 4 precios de venta.", "danger")
            return render_template(
                "productos/formulario.html", formulario=formulario, modo="editar", producto=producto,
                puede_ver_costo=puede_ver_costo, tipo_cambio=tipo_cambio,
            )

        producto.nombre = formulario.nombre.data.strip()
        producto.descripcion = formulario.descripcion.data
        producto.categoria_id = formulario.categoria_id.data
        producto.subcategoria_id = formulario.subcategoria_id.data or None
        producto.color_id = formulario.color_id.data or None
        if puede_ver_costo:
            if float(formulario.precio_compra_usd.data) != float(producto.precio_compra_usd):
                producto.tipo_cambio_al_comprar = tipo_cambio
                producto.fecha_actualizacion_compra = datetime.utcnow()
            producto.precio_compra_usd = formulario.precio_compra_usd.data
            producto.precio_minorista_usd = formulario.precio_minorista_usd.data
            producto.precio_mayorista_usd = formulario.precio_mayorista_usd.data
            producto.precio_franquicia_usd = formulario.precio_franquicia_usd.data
            producto.precio_asesora_libre_usd = formulario.precio_asesora_libre_usd.data
            producto.minorista_habilitado = formulario.minorista_habilitado.data
            producto.mayorista_habilitado = formulario.mayorista_habilitado.data
            producto.franquicia_habilitado = formulario.franquicia_habilitado.data
            producto.asesora_libre_habilitado = formulario.asesora_libre_habilitado.data
        producto.stock = formulario.stock.data
        producto.activo = formulario.activo.data
        producto.es_destacado = formulario.es_destacado.data
        producto.en_oferta = formulario.en_oferta.data
        producto.porcentaje_descuento = formulario.porcentaje_descuento.data if formulario.en_oferta.data else None

        db.session.commit()

        archivos = request.files.getlist("fotos")
        guardar_imagenes_producto(producto, archivos)

        flash(f"Producto '{producto.nombre}' actualizado correctamente.", "success")
        return redirect(url_for("productos.editar", producto_id=producto.id))

    return render_template(
        "productos/formulario.html", formulario=formulario, modo="editar", producto=producto,
        puede_ver_costo=puede_ver_costo, tipo_cambio=tipo_cambio,
    )


@productos_bp.route("/<int:producto_id>/eliminar", methods=["POST"])
@login_required
@requiere_rol(*ROLES_COSTO)
def eliminar(producto_id):
    producto = Producto.query.get_or_404(producto_id)

    ya_vendido = ItemPedido.query.filter_by(producto_id=producto.id).first() is not None
    if ya_vendido:
        flash(
            f"'{producto.nombre}' no se puede eliminar: ya tiene ventas registradas. "
            "Puedes desactivarlo en su lugar (Activo = No).",
            "danger",
        )
        return redirect(url_for("productos.listar"))

    nombre = producto.nombre
    db.session.delete(producto)
    db.session.commit()
    flash(f"Producto '{nombre}' eliminado.", "info")
    return redirect(url_for("productos.listar"))


@productos_bp.route("/<int:producto_id>/imagenes/<int:imagen_id>/eliminar", methods=["POST"])
@login_required
@requiere_rol(*ROLES_GESTION)
def eliminar_imagen(producto_id, imagen_id):
    imagen = ProductoImagen.query.filter_by(id=imagen_id, producto_id=producto_id).first_or_404()
    eliminar_imagen_producto(imagen)
    flash("Fotografía eliminada.", "info")
    return redirect(url_for("productos.editar", producto_id=producto_id))


@productos_bp.route("/<int:producto_id>/imagenes/<int:imagen_id>/marcar-principal", methods=["POST"])
@login_required
@requiere_rol(*ROLES_GESTION)
def marcar_principal(producto_id, imagen_id):
    ProductoImagen.query.filter_by(producto_id=producto_id).update({"es_principal": False})
    imagen = ProductoImagen.query.filter_by(id=imagen_id, producto_id=producto_id).first_or_404()
    imagen.es_principal = True
    db.session.commit()
    flash("Foto principal actualizada.", "success")
    return redirect(url_for("productos.editar", producto_id=producto_id))


# ---------------------------------------------------------------------------
# Promociones masivas: seleccionar varios productos y aplicar/quitar un
# descuento porcentual a los 4 niveles de precio a la vez.
# ---------------------------------------------------------------------------
@productos_bp.route("/promociones", methods=["GET", "POST"])
@login_required
@requiere_rol(*ROLES_GESTION)
def promociones():
    if request.method == "POST":
        ids_seleccionados = request.form.getlist("producto_id", type=int)
        accion = request.form.get("accion")

        if not ids_seleccionados:
            flash("Selecciona al menos un producto.", "warning")
            return redirect(url_for("productos.promociones"))

        if accion == "aplicar":
            porcentaje = request.form.get("porcentaje", type=float)
            if not porcentaje or porcentaje <= 0 or porcentaje > 95:
                flash("Ingresa un porcentaje de descuento válido (1-95).", "danger")
                return redirect(url_for("productos.promociones"))

            Producto.query.filter(Producto.id.in_(ids_seleccionados)).update(
                {"en_oferta": True, "porcentaje_descuento": porcentaje}, synchronize_session=False
            )
            db.session.commit()
            flash(f"Descuento de {porcentaje:.0f}% aplicado a {len(ids_seleccionados)} producto(s).", "success")

        elif accion == "quitar":
            Producto.query.filter(Producto.id.in_(ids_seleccionados)).update(
                {"en_oferta": False, "porcentaje_descuento": None}, synchronize_session=False
            )
            db.session.commit()
            flash(f"Oferta retirada de {len(ids_seleccionados)} producto(s).", "info")

        return redirect(url_for("productos.promociones"))

    productos = Producto.query.order_by(Producto.en_oferta.desc(), Producto.nombre).all()
    return render_template("productos/promociones.html", productos=productos, tipo_cambio=obtener_tipo_cambio())
