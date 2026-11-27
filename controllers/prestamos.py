"""CONTROLADOR · Préstamos: prestar, devolver y renovar."""
from flask import Blueprint, flash, redirect, render_template, request, url_for

from controllers import destino_seguro
from models.errores import ReglaDeNegocio
from models.lector import Lector
from models.libro import Libro
from models.prestamo import VISTAS, Prestamo

bp = Blueprint("prestamos", __name__, url_prefix="/prestamos")


@bp.get("")
def lista():
    vista = request.args.get("vista", "activos")
    vista = vista if vista in VISTAS else "activos"
    q = request.args.get("q", "").strip()
    return render_template(
        "prestamos/lista.html",
        prestamos=Prestamo.listar(vista, q),
        vista=vista,
        q=q,
        max_renovaciones=Prestamo.MAX_RENOVACIONES,
    )


@bp.route("/nuevo", methods=["GET", "POST"])
def nuevo():
    elegido = {
        "libro_id": request.values.get("libro_id", type=int),
        "lector_id": request.values.get("lector_id", type=int),
        "dias": request.values.get("dias", Prestamo.PLAZO_NORMAL, type=int),
    }
    if request.method == "POST":
        try:
            hecho = Prestamo.prestar(elegido["libro_id"], elegido["lector_id"], elegido["dias"])
        except ReglaDeNegocio as regla:
            flash(str(regla), "error")
            return redirect(destino_seguro(url_for("prestamos.nuevo", **elegido)))
        flash(f"«{hecho['titulo']}» prestado a {hecho['lector']}. Vence el {hecho['vence_en']:%d/%m/%Y}.", "ok")
        return redirect(destino_seguro(url_for("prestamos.lista")))
    return render_template(
        "prestamos/nuevo.html",
        libros=Libro.disponibles(),
        lectores=Lector.buscar(),
        elegido=elegido,
        plazos=Prestamo.PLAZOS,
        max_prestamos=Lector.MAX_PRESTAMOS,
    )


@bp.post("/<int:prestamo_id>/devolver")
def devolver(prestamo_id):
    try:
        hecho = Prestamo.devolver(prestamo_id)
    except ReglaDeNegocio as regla:
        flash(str(regla), "error")
    else:
        tarde = f" con {-hecho['dias_restantes']} día(s) de retraso" if hecho["vencido"] else ""
        flash(f"«{hecho['titulo']}» devuelto{tarde}.", "ok")
    return redirect(destino_seguro(url_for("prestamos.lista")))


@bp.post("/<int:prestamo_id>/renovar")
def renovar(prestamo_id):
    try:
        hecho = Prestamo.renovar(prestamo_id)
    except ReglaDeNegocio as regla:
        flash(str(regla), "error")
    else:
        flash(f"«{hecho['titulo']}» renovado hasta el {hecho['vence_en']:%d/%m/%Y}.", "ok")
    return redirect(destino_seguro(url_for("prestamos.lista")))
