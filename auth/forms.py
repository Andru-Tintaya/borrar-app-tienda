from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional, EqualTo


class LoginStaffForm(FlaskForm):
    """Login del personal interno: correo + contraseña."""
    correo = StringField("Correo", validators=[DataRequired(), Email()])
    password = PasswordField("Contraseña", validators=[DataRequired()])
    submit = SubmitField("Ingresar")


class SolicitarOTPForm(FlaskForm):
    """Paso 1 del login de clientes externos: pide el correo para
    enviarle un código OTP de 6 dígitos."""
    correo = StringField("Correo", validators=[DataRequired(), Email()])
    submit = SubmitField("Enviar código")


class VerificarOTPForm(FlaskForm):
    """Paso 2 del login de clientes externos: valida el código recibido."""
    correo = StringField("Correo", validators=[DataRequired(), Email()])
    codigo = StringField("Código de verificación", validators=[DataRequired(), Length(min=6, max=6)])
    submit = SubmitField("Verificar")


class RegistroClienteForm(FlaskForm):
    """Registro de clientes externos: Público, Minorista o Mayorista.
    Los campos B2B (NIT/CI, razón social) solo son obligatorios para
    Minorista/Mayorista; la validación cruzada se hace en la ruta.
    """
    nombre = StringField("Nombre completo", validators=[DataRequired(), Length(max=150)])
    correo = StringField("Correo", validators=[DataRequired(), Email()])
    telefono = StringField("Celular", validators=[DataRequired(), Length(max=30)])
    ciudad = StringField("Ciudad", validators=[Optional(), Length(max=100)])

    tipo_cliente = SelectField(
        "Tipo de cliente",
        choices=[
            ("Publico", "Público (precio Minorista)"),
            ("Minorista", "Minorista (B2B)"),
            ("Mayorista", "Mayorista (B2B)"),
            ("Franquicia", "Franquicia (B2B)"),
            ("Asesora Libre", "Asesora Libre (B2B)"),
        ],
        validators=[DataRequired()],
    )

    nit_ci = StringField("NIT / CI", validators=[Optional(), Length(max=30)])
    razon_social = StringField("Razón social", validators=[Optional(), Length(max=150)])

    submit = SubmitField("Registrarme")


# ---------------------------------------------------------------------------
# Recuperación de contraseña — personal interno
# ---------------------------------------------------------------------------
class SolicitarRecuperacionForm(FlaskForm):
    """Paso 1 de '¿Olvidaste tu contraseña?': pide el correo del personal
    interno para enviarle un código de verificación de 6 dígitos."""
    correo = StringField("Correo institucional", validators=[DataRequired(), Email()])
    submit = SubmitField("Enviar código de verificación")


class VerificarRecuperacionForm(FlaskForm):
    """Paso 2: valida el código de verificación recibido por correo."""
    correo = StringField("Correo", validators=[DataRequired(), Email()])
    codigo = StringField("Código de verificación", validators=[DataRequired(), Length(min=6, max=6)])
    submit = SubmitField("Verificar código")


class NuevaPasswordForm(FlaskForm):
    """Paso 3: define la nueva contraseña, ya con el código verificado."""
    password = PasswordField("Nueva contraseña", validators=[DataRequired(), Length(min=6, message="Mínimo 6 caracteres.")])
    confirmar_password = PasswordField(
        "Confirmar nueva contraseña",
        validators=[DataRequired(), EqualTo("password", message="Las contraseñas no coinciden.")],
    )
    submit = SubmitField("Guardar nueva contraseña")
