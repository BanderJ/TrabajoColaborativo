"""CONTROLADOR · Lectores registrados."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from models.errores import ReglaDeNegocio
from models.lector import Lector
from models.prestamo import Prestamo

bp = Blueprint("lectores", __name__, url_prefix="/lectores")


@bp.get("")
def lista():
    q = request.args.get("q", "").strip()
    return render_template(
        "lectores/lista.html",
        lectores=Lector.buscar(q),
        q=q,
        max_prestamos=Lector.MAX_PRESTAMOS,
    )


@bp.get("/<int:lector_id>")
def detalle(lector_id):
    lector = Lector.obtener(lector_id) or abort(404)
    return render_template(
        "lectores/detalle.html",
        lector=lector,
        prestamos=Prestamo.del_lector(lector_id),
        max_prestamos=Lector.MAX_PRESTAMOS,
        max_renovaciones=Prestamo.MAX_RENOVACIONES,
    )


@bp.route("/nuevo", methods=["GET", "POST"])
def nuevo():
    datos, errores = {}, {}
    if request.method == "POST":
        datos, errores = Lector.validar(request.form)
        if not errores:
            lector_id = Lector.crear(datos)
            flash(f"{datos['nombre']} quedó registrado.", "ok")
            return redirect(url_for("lectores.detalle", lector_id=lector_id))
    return render_template("lectores/formulario.html", lector=datos, errores=errores)


@bp.route("/<int:lector_id>/editar", methods=["GET", "POST"])
def editar(lector_id):
    lector = Lector.obtener(lector_id) or abort(404)
    errores = {}
    if request.method == "POST":
        datos, errores = Lector.validar(request.form)
        if not errores:
            Lector.actualizar(lector_id, datos)
            flash("Cambios guardados.", "ok")
            return redirect(url_for("lectores.detalle", lector_id=lector_id))
        lector = {**lector, **datos}
    return render_template("lectores/formulario.html", lector=lector, errores=errores)


@bp.post("/<int:lector_id>/eliminar")
def eliminar(lector_id):
    lector = Lector.obtener(lector_id) or abort(404)
    try:
        Lector.eliminar(lector_id)
    except ReglaDeNegocio as regla:
        flash(str(regla), "error")
        return redirect(url_for("lectores.detalle", lector_id=lector_id))
    flash(f"{lector['nombre']} se eliminó.", "ok")
    return redirect(url_for("lectores.lista"))
