"""Biblioteca MVC · punto de entrada.

Une las tres partes del proyecto:
  models/       el Modelo: habla con PostgreSQL
  views/        la Vista: las plantillas HTML que ve el usuario
  controllers/  el Controlador: recibe los clics y decide qué hacer

Para arrancar:  python app.py
"""
import hashlib
import os
import sys
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify

RAIZ = Path(__file__).resolve().parent
load_dotenv(RAIZ / ".env")

from controllers import registrar  # noqa: E402
from models.db import migrar, nombre_de_la_base, reiniciar  # noqa: E402

app = Flask(__name__, template_folder="views")
app.secret_key = os.getenv("CLAVE_SECRETA", "solo-para-la-demo")
app.config["TEMPLATES_AUTO_RELOAD"] = True
registrar(app)


# ---------------------------------------------------------------------------
# Formato de fechas para las Vistas:  {{ prestamo.vence_en | fecha }}
# ---------------------------------------------------------------------------
MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")


@app.template_filter("fecha")
def fecha(valor):
    return f"{valor.day} {MESES[valor.month - 1]} {valor.year}" if valor else "—"


@app.template_filter("hace")
def hace(valor):
    """«hoy», «ayer», «hace 5 días»..."""
    if not valor:
        return "—"
    dias = (date.today() - (valor.date() if isinstance(valor, datetime) else valor)).days
    if dias <= 0:
        return "hoy"
    if dias == 1:
        return "ayer"
    if dias < 30:
        return f"hace {dias} días"
    return fecha(valor)


def rama_actual():
    """Lee en qué rama de Git está esta carpeta, para mostrarla en la página."""
    head = RAIZ / ".git" / "HEAD"
    try:
        contenido = head.read_text(encoding="utf-8").strip()
    except OSError:
        return "sin Git"
    prefijo = "ref: refs/heads/"
    return contenido[len(prefijo):] if contenido.startswith(prefijo) else contenido[:7]


def persona_de_la_rama(rama):
    """Convención del equipo: cada rama empieza con el nombre de quien la trabaja (ana/…, luis/…)."""
    if rama == "main":
        return None
    return rama.split("/")[0].capitalize() if "/" in rama else None


@app.context_processor
def datos_del_entorno():
    rama = rama_actual()
    persona = persona_de_la_rama(rama)
    return {
        "rama": rama,
        "persona": persona,
        "color_rama": "principal" if rama == "main" else (persona or "otra").lower(),
        "base_de_datos": nombre_de_la_base(),
        "firma": firma_del_proyecto() if app.debug else "",
    }


# ---------------------------------------------------------------------------
# Modo demo: la página se recarga sola cuando cambia un archivo o la rama.
# ---------------------------------------------------------------------------
VIGILADOS = ("models", "views", "controllers", "static", "db")


def firma_del_proyecto():
    huella = hashlib.md5()
    for carpeta in VIGILADOS:
        for archivo in sorted((RAIZ / carpeta).rglob("*")):
            if archivo.is_file() and "__pycache__" not in archivo.parts:
                huella.update(f"{archivo}:{archivo.stat().st_mtime_ns}".encode())
    huella.update(rama_actual().encode())
    return huella.hexdigest()


@app.get("/__cambios")
def cambios():
    return jsonify(firma=firma_del_proyecto())


_migraciones_vistas = None


@app.before_request
def aplicar_migraciones_nuevas():
    """Si llegó un archivo nuevo a db/migraciones (por ejemplo, con un Pull), se aplica solo."""
    global _migraciones_vistas
    actuales = sorted(p.name for p in (RAIZ / "db" / "migraciones").glob("*.sql"))
    if actuales != _migraciones_vistas:
        migrar()
        _migraciones_vistas = actuales


if __name__ == "__main__":
    if "--reiniciar-bd" in sys.argv:
        reiniciar()
        print("Base de datos vacía. La próxima vez que arranques, se vuelve a crear desde db/migraciones.")
        sys.exit(0)
    puerto = int(os.getenv("PUERTO", "5000"))
    print(f"\n  Biblioteca MVC · http://localhost:{puerto}\n")
    app.run(debug=True, port=puerto)
