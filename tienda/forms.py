from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, Optional

from app.models_all import ENTREGAS


class CheckoutForm(FlaskForm):
    tipo_entrega = SelectField("Entrega", choices=[(e, e) for e in ENTREGAS], validators=[DataRequired()])
    direccion_envio = StringField("Dirección de envío", validators=[Optional(), Length(max=255)])
    nota = TextAreaField("Nota con el pedido", validators=[Optional()])
    submit = SubmitField("Confirmar pedido")
