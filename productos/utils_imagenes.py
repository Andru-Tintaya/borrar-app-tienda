import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app

from app.extensions import db
from app.models_all import ProductoImagen


def extension_permitida(nombre_archivo: str) -> bool:
    if "." not in nombre_archivo:
        return False
    extension = nombre_archivo.rsplit(".", 1)[1].lower()
    return extension in current_app.config["EXTENSIONES_IMAGEN"]


def guardar_imagenes_producto(producto, archivos):
    """Guarda en disco cada archivo válido de `archivos` (request.files.getlist)
    dentro de app/static/uploads/productos/<id>/ y crea su ProductoImagen.
    La primera imagen del producto (si no tenía ninguna) queda como principal.
    """
    carpeta_producto = os.path.join(current_app.config["UPLOAD_FOLDER"], "productos", str(producto.id))
    os.makedirs(carpeta_producto, exist_ok=True)

    tiene_principal = any(img.es_principal for img in producto.imagenes)
    siguiente_orden = len(producto.imagenes)
    guardadas = 0

    for archivo in archivos:
        if not archivo or archivo.filename == "":
            continue
        if not extension_permitida(archivo.filename):
            continue

        extension = secure_filename(archivo.filename).rsplit(".", 1)[1].lower()
        nombre_unico = f"{uuid.uuid4().hex}.{extension}"
        archivo.save(os.path.join(carpeta_producto, nombre_unico))

        ruta_relativa = f"uploads/productos/{producto.id}/{nombre_unico}"
        imagen = ProductoImagen(
            producto_id=producto.id,
            ruta_archivo=ruta_relativa,
            orden=siguiente_orden,
            es_principal=(not tiene_principal),
        )
        db.session.add(imagen)

        tiene_principal = True
        siguiente_orden += 1
        guardadas += 1

    if guardadas:
        db.session.commit()
    return guardadas


def eliminar_imagen_producto(imagen):
    ruta_absoluta = os.path.join(current_app.root_path, "static", imagen.ruta_archivo)
    try:
        if os.path.exists(ruta_absoluta):
            os.remove(ruta_absoluta)
    except OSError:
        pass

    era_principal = imagen.es_principal
    producto = imagen.producto
    db.session.delete(imagen)
    db.session.commit()

    if era_principal:
        siguiente = ProductoImagen.query.filter_by(producto_id=producto.id).order_by(ProductoImagen.orden).first()
        if siguiente:
            siguiente.es_principal = True
            db.session.commit()
