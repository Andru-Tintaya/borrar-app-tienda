from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length


class CategoriaForm(FlaskForm):
    nombre = StringField("Nombre de la categoría", validators=[DataRequired(), Length(max=100)])
    activo = BooleanField("Activa", default=True)
    submit = SubmitField("Guardar")


class SubcategoriaForm(FlaskForm):
    nombre = StringField("Nombre de la subcategoría", validators=[DataRequired(), Length(max=100)])
    categoria_id = SelectField("Categoría", coerce=int, validators=[DataRequired()])
    activo = BooleanField("Activa", default=True)
    submit = SubmitField("Guardar")


class ColorForm(FlaskForm):
    nombre = StringField("Nombre del color", validators=[DataRequired(), Length(max=50)])
    submit = SubmitField("Guardar")
