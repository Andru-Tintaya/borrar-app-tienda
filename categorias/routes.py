import os
import uuid
from flask import render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required

from app.categorias import categorias_bp
from app.categorias.forms import CategoriaForm, SubcategoriaForm, ColorForm
from app.productos.utils_imagenes import extension_permitida
from app.extensions import db
from app.models_all import Categoria, Subcategoria, Color, Producto
from app.utilidades import requiere_rol

ROLES_GESTION = ("Gerente", "Administrador", "Empleado")


def _guardar_imagen_categoria(categoria, archivo):
    if not archivo or not archivo.filename:
        return
    if not extension_permitida(archivo.filename):
        flash("La imagen de la categoría debe ser jpg, jpeg, png o webp.", "danger")
        return
    carpeta = os.path.join(current_app.config["UPLOAD_FOLDER"], "categorias")
    os.makedirs(carpeta, exist_ok=True)
    extension = archivo.filename.rsplit(".", 1)[1].lower()
    nombre_unico = f"{uuid.uuid4().hex}.{extension}"
    archivo.save(os.path.join(carpeta, nombre_unico))
    categoria.imagen = f"uploads/categorias/{nombre_unico}"


@categorias_bp.route("/")
@login_required
@requiere_rol(*ROLES_GESTION)
def listar():
    categorias = Categoria.query.order_by(Categoria.nombre).all()
    return render_template("categorias/listar.html", categorias=categorias)


@categorias_bp.route("/nueva", methods=["GET", "POST"])
@login_required
@requiere_rol(*ROLES_GESTION)
def nueva():
    formulario = CategoriaForm()
    if formulario.validate_on_submit():
        if Categoria.query.filter_by(nombre=formulario.nombre.data.strip()).first():
            flash("Ya existe una categoría con ese nombre.", "danger")
        else:
            categoria = Categoria(nombre=formulario.nombre.data.strip(), activo=formulario.activo.data)
            _guardar_imagen_categoria(categoria, request.files.get("imagen"))
            db.session.add(categoria)
            db.session.commit()
            flash("Categoría creada correctamente.", "success")
            return redirect(url_for("categorias.listar"))
    return render_template("categorias/formulario_categoria.html", formulario=formulario, modo="nueva")


@categorias_bp.route("/<int:categoria_id>/editar", methods=["GET", "POST"])
@login_required
@requiere_rol(*ROLES_GESTION)
def editar(categoria_id):
    categoria = Categoria.query.get_or_404(categoria_id)
    formulario = CategoriaForm(obj=categoria)
    if formulario.validate_on_submit():
        categoria.nombre = formulario.nombre.data.strip()
        categoria.activo = formulario.activo.data
        _guardar_imagen_categoria(categoria, request.files.get("imagen"))
        db.session.commit()
        flash("Categoría actualizada correctamente.", "success")
        return redirect(url_for("categorias.listar"))
    return render_template("categorias/formulario_categoria.html", formulario=formulario, modo="editar", categoria=categoria)


@categorias_bp.route("/subcategorias")
@login_required
@requiere_rol(*ROLES_GESTION)
def listar_subcategorias():
    subcategorias = Subcategoria.query.join(Categoria).order_by(Categoria.nombre, Subcategoria.nombre).all()
    return render_template("categorias/listar_subcategorias.html", subcategorias=subcategorias)


@categorias_bp.route("/subcategorias/nueva", methods=["GET", "POST"])
@login_required
@requiere_rol(*ROLES_GESTION)
def nueva_subcategoria():
    formulario = SubcategoriaForm()
    formulario.categoria_id.choices = [(c.id, c.nombre) for c in Categoria.query.order_by(Categoria.nombre).all()]

    if formulario.validate_on_submit():
        existe = Subcategoria.query.filter_by(
            nombre=formulario.nombre.data.strip(), categoria_id=formulario.categoria_id.data
        ).first()
        if existe:
            flash("Ya existe esa subcategoría dentro de la categoría seleccionada.", "danger")
        else:
            db.session.add(Subcategoria(
                nombre=formulario.nombre.data.strip(),
                categoria_id=formulario.categoria_id.data,
                activo=formulario.activo.data,
            ))
            db.session.commit()
            flash("Subcategoría creada correctamente.", "success")
            return redirect(url_for("categorias.listar_subcategorias"))

    return render_template("categorias/formulario_subcategoria.html", formulario=formulario, modo="nueva")


@categorias_bp.route("/subcategorias/<int:subcategoria_id>/editar", methods=["GET", "POST"])
@login_required
@requiere_rol(*ROLES_GESTION)
def editar_subcategoria(subcategoria_id):
    subcategoria = Subcategoria.query.get_or_404(subcategoria_id)
    formulario = SubcategoriaForm(obj=subcategoria)
    formulario.categoria_id.choices = [(c.id, c.nombre) for c in Categoria.query.order_by(Categoria.nombre).all()]

    if formulario.validate_on_submit():
        subcategoria.nombre = formulario.nombre.data.strip()
        subcategoria.categoria_id = formulario.categoria_id.data
        subcategoria.activo = formulario.activo.data
        db.session.commit()
        flash("Subcategoría actualizada correctamente.", "success")
        return redirect(url_for("categorias.listar_subcategorias"))

    return render_template(
        "categorias/formulario_subcategoria.html", formulario=formulario, modo="editar", subcategoria=subcategoria
    )


@categorias_bp.route("/api/subcategorias-por-categoria/<int:categoria_id>")
@login_required
@requiere_rol(*ROLES_GESTION)
def api_subcategorias_por_categoria(categoria_id):
    """Usado por JS en el formulario de productos: al elegir una
    categoría, recarga solo las subcategorías de esa categoría (antes
    mostraba todas, sin importar la categoría elegida)."""
    subcategorias = (
        Subcategoria.query.filter_by(categoria_id=categoria_id, activo=True)
        .order_by(Subcategoria.nombre).all()
    )
    return jsonify([{"id": s.id, "nombre": s.nombre} for s in subcategorias])


@categorias_bp.route("/<int:categoria_id>/eliminar", methods=["POST"])
@login_required
@requiere_rol(*ROLES_GESTION)
def eliminar(categoria_id):
    categoria = Categoria.query.get_or_404(categoria_id)
    if Producto.query.filter_by(categoria_id=categoria.id).first():
        flash(f"'{categoria.nombre}' no se puede eliminar: todavía tiene productos asociados. Puedes desactivarla en su lugar.", "danger")
        return redirect(url_for("categorias.listar"))
    if categoria.subcategorias:
        flash(f"'{categoria.nombre}' no se puede eliminar: primero elimina sus subcategorías.", "danger")
        return redirect(url_for("categorias.listar"))

    nombre = categoria.nombre
    db.session.delete(categoria)
    db.session.commit()
    flash(f"Categoría '{nombre}' eliminada.", "info")
    return redirect(url_for("categorias.listar"))


@categorias_bp.route("/subcategorias/<int:subcategoria_id>/eliminar", methods=["POST"])
@login_required
@requiere_rol(*ROLES_GESTION)
def eliminar_subcategoria(subcategoria_id):
    subcategoria = Subcategoria.query.get_or_404(subcategoria_id)
    if Producto.query.filter_by(subcategoria_id=subcategoria.id).first():
        flash(f"'{subcategoria.nombre}' no se puede eliminar: todavía tiene productos asociados. Puedes desactivarla en su lugar.", "danger")
        return redirect(url_for("categorias.listar_subcategorias"))

    nombre = subcategoria.nombre
    db.session.delete(subcategoria)
    db.session.commit()
    flash(f"Subcategoría '{nombre}' eliminada.", "info")
    return redirect(url_for("categorias.listar_subcategorias"))


# ---------------------------------------------------------------------------
# Colores (catálogo reutilizable, evita escribir "Rojo"/"rojo" a mano cada vez)
# ---------------------------------------------------------------------------
@categorias_bp.route("/colores", methods=["GET", "POST"])
@login_required
@requiere_rol(*ROLES_GESTION)
def colores():
    formulario = ColorForm()
    if formulario.validate_on_submit():
        nombre = formulario.nombre.data.strip()
        if Color.query.filter_by(nombre=nombre).first():
            flash("Ese color ya existe.", "danger")
        else:
            db.session.add(Color(nombre=nombre))
            db.session.commit()
            flash(f"Color '{nombre}' agregado.", "success")
        return redirect(url_for("categorias.colores"))

    lista_colores = Color.query.order_by(Color.nombre).all()
    return render_template("categorias/colores.html", colores=lista_colores, formulario=formulario)


@categorias_bp.route("/colores/<int:color_id>/eliminar", methods=["POST"])
@login_required
@requiere_rol(*ROLES_GESTION)
def eliminar_color(color_id):
    color = Color.query.get_or_404(color_id)
    if Producto.query.filter_by(color_id=color.id).first():
        flash(f"'{color.nombre}' no se puede eliminar: hay productos usándolo.", "danger")
        return redirect(url_for("categorias.colores"))

    nombre = color.nombre
    db.session.delete(color)
    db.session.commit()
    flash(f"Color '{nombre}' eliminado.", "info")
    return redirect(url_for("categorias.colores"))
