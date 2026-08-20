from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, DecimalField, IntegerField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class ProductoForm(FlaskForm):
    nombre = StringField("Nombre del producto", validators=[DataRequired(), Length(max=150)])
    # SKU ya no lo escribe el usuario: se genera solo (ver utils_sku.py)
    descripcion = TextAreaField("Descripción", validators=[Optional()])

    categoria_id = SelectField("Categoría", coerce=int, validators=[DataRequired()])
    subcategoria_id = SelectField("Subcategoría", coerce=int, validators=[Optional()])
    color_id = SelectField("Color (opcional)", coerce=int, validators=[Optional()])

    # Todos los precios se guardan en USD (ver Producto en models_all.py).
    # El formulario permite escribir en USD o en Bs. — el JS del template
    # recalcula el otro campo con el tipo de cambio del día.
    precio_compra_usd = DecimalField("Precio de Compra (USD)", places=2, validators=[Optional(), NumberRange(min=0)])
    precio_minorista_usd = DecimalField("Precio Minorista (USD)", places=2, validators=[Optional(), NumberRange(min=0)])
    precio_mayorista_usd = DecimalField("Precio Mayorista (USD)", places=2, validators=[Optional(), NumberRange(min=0)])
    precio_franquicia_usd = DecimalField("Precio Franquicia (USD)", places=2, validators=[Optional(), NumberRange(min=0)])
    precio_asesora_libre_usd = DecimalField("Precio Asesora Libre (USD)", places=2, validators=[Optional(), NumberRange(min=0)])

    minorista_habilitado = BooleanField("Vender a Minorista", default=True)
    mayorista_habilitado = BooleanField("Vender a Mayorista", default=True)
    franquicia_habilitado = BooleanField("Vender a Franquicia", default=True)
    asesora_libre_habilitado = BooleanField("Vender a Asesora Libre", default=True)

    stock = IntegerField("Stock", validators=[DataRequired(), NumberRange(min=0)])

    # Visibilidad: si está desmarcado, solo el personal interno lo ve (como "Inactivo")
    activo = BooleanField("Activo (visible para clientes)", default=True)

    # Banderas de estado combinables. "Nuevo" no está aquí: se calcula
    # solo durante los primeros 30 días desde la creación del producto.
    es_destacado = BooleanField("Destacado")
    en_oferta = BooleanField("En oferta")
    porcentaje_descuento = DecimalField(
        "% de descuento", places=2, validators=[Optional(), NumberRange(min=0, max=95)]
    )

    submit = SubmitField("Guardar producto")
