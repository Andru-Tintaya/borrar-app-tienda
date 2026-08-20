from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional, EqualTo


class FormularioPersonal(FlaskForm):
    """Alta y edición de personal interno. La contraseña es obligatoria al
    crear y opcional al editar (se deja vacía para no cambiarla)."""
    nombre = StringField("Nombre completo", validators=[DataRequired(), Length(max=150)])
    correo = StringField("Correo", validators=[DataRequired(), Email()])
    rol_id = SelectField("Rol", coerce=int, validators=[DataRequired()])
    activo = BooleanField("Cuenta activa", default=True)

    password = PasswordField(
        "Contraseña",
        validators=[Optional(), Length(min=6, message="Mínimo 6 caracteres.")],
    )
    confirmar_password = PasswordField(
        "Confirmar contraseña",
        validators=[Optional(), EqualTo("password", message="Las contraseñas no coinciden.")],
    )

    submit = SubmitField("Guardar")
