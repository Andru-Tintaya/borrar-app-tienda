UNIDADES = ["", "UN", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO", "NUEVE"]
DIEZ_A_DIECINUEVE = [
    "DIEZ", "ONCE", "DOCE", "TRECE", "CATORCE", "QUINCE", "DIECISEIS",
    "DIECISIETE", "DIECIOCHO", "DIECINUEVE",
]
DECENAS = [
    "", "", "VEINTE", "TREINTA", "CUARENTA", "CINCUENTA",
    "SESENTA", "SETENTA", "OCHENTA", "NOVENTA",
]
CENTENAS = [
    "", "CIENTO", "DOSCIENTOS", "TRESCIENTOS", "CUATROCIENTOS", "QUINIENTOS",
    "SEISCIENTOS", "SETECIENTOS", "OCHOCIENTOS", "NOVECIENTOS",
]


def _convertir_menor_1000(n: int) -> str:
    if n == 0:
        return ""
    if n == 100:
        return "CIEN"
    centena, resto = divmod(n, 100)
    partes = []
    if centena:
        partes.append(CENTENAS[centena])
    if resto:
        if resto < 10:
            partes.append(UNIDADES[resto])
        elif resto < 20:
            partes.append(DIEZ_A_DIECINUEVE[resto - 10])
        else:
            decena, unidad = divmod(resto, 10)
            if decena == 2 and unidad:
                partes.append(f"VEINTI{UNIDADES[unidad]}")
            else:
                texto_decena = DECENAS[decena]
                partes.append(f"{texto_decena} Y {UNIDADES[unidad]}" if unidad else texto_decena)
    return " ".join(partes)


def numero_a_letras(n: int) -> str:
    if n == 0:
        return "CERO"

    millones, resto = divmod(n, 1_000_000)
    miles, unidades = divmod(resto, 1000)

    partes = []
    if millones:
        partes.append("UN MILLON" if millones == 1 else f"{_convertir_menor_1000(millones)} MILLONES")
    if miles:
        partes.append("MIL" if miles == 1 else f"{_convertir_menor_1000(miles)} MIL")
    if unidades or not partes:
        partes.append(_convertir_menor_1000(unidades))

    return " ".join(p for p in partes if p).strip()


def monto_a_letras_bolivianos(monto) -> str:
    """Convierte un Decimal/float de Bs. a la leyenda 'SON: ... 00/100 BS.'"""
    entero = int(monto)
    centavos = round((float(monto) - entero) * 100)
    return f"{numero_a_letras(entero)} {centavos:02d}/100 BS."
