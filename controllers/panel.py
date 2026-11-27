"""CONTROLADOR · Panel de inicio."""
from datetime import date

from flask import Blueprint, render_template

from models.db import migraciones_aplicadas
from models.lector import Lector
from models.libro import Libro
from models.prestamo import Prestamo

bp = Blueprint("panel", __name__)


@bp.get("/")
def inicio():
    return render_template(
        "panel.html",
        hoy=date.today(),
        resumen=Prestamo.resumen(),
        proximos=Prestamo.proximos_a_vencer(),
        actividad=Prestamo.actividad_reciente(),
        populares=Libro.mas_prestados(),
        migraciones=migraciones_aplicadas(),
        max_prestamos=Lector.MAX_PRESTAMOS,
    )
