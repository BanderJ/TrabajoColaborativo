"""CONTROLADOR · Catálogo de libros.

Recibe lo que hace el usuario (un clic, un formulario),
le pide al Modelo que cambie los datos y elige qué Vista mostrar.
"""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from models.errores import ReglaDeNegocio
from models.lector import Lector
from models.libro import GENEROS, Libro
from models.prestamo import Prestamo

bp = Blueprint("libros", __name__, url_prefix="/libros")


@bp.get("")
def lista():
    filtros = {
        "q": request.args.get("q", "").strip(),
        "estado": request.args.get("estado", ""),
        "genero": request.args.get("genero", ""),
    }
    return render_template(
        "libros/lista.html",
        libros=Libro.buscar(filtros["q"], filtros["estado"], filtros["genero"]),
        generos=Libro.generos_en_uso(),
        filtros=filtros,
    )


@bp.get("/<int:libro_id>")
def detalle(libro_id):
    libro = Libro.obtener(libro_id) or abort(404)
    return render_template(
        "libros/detalle.html",
        libro=libro,
        historial=Prestamo.del_libro(libro_id),
        lectores=Lector.buscar(),
        plazos=Prestamo.PLAZOS,
        plazo_normal=Prestamo.PLAZO_NORMAL,
        max_renovaciones=Prestamo.MAX_RENOVACIONES,
        max_prestamos=Lector.MAX_PRESTAMOS,
    )


@bp.route("/nuevo", methods=["GET", "POST"])
def nuevo():
    datos, errores = {}, {}
    if request.method == "POST":
        datos, errores = Libro.validar(request.form)
        if not errores:
            libro_id = Libro.crear(datos)
            flash(f"«{datos['titulo']}» se agregó al catálogo.", "ok")
            return redirect(url_for("libros.detalle", libro_id=libro_id))
    return render_template("libros/formulario.html", libro=datos, errores=errores, generos=GENEROS)


@bp.route("/<int:libro_id>/editar", methods=["GET", "POST"])
def editar(libro_id):
    libro = Libro.obtener(libro_id) or abort(404)
    errores = {}
    if request.method == "POST":
        datos, errores = Libro.validar(request.form)
        if not errores:
            Libro.actualizar(libro_id, datos)
            flash("Cambios guardados.", "ok")
            return redirect(url_for("libros.detalle", libro_id=libro_id))
        libro = {**libro, **datos}
    return render_template("libros/formulario.html", libro=libro, errores=errores, generos=GENEROS)


@bp.post("/<int:libro_id>/eliminar")
def eliminar(libro_id):
    libro = Libro.obtener(libro_id) or abort(404)
    try:
        Libro.eliminar(libro_id)
    except ReglaDeNegocio as regla:
        flash(str(regla), "error")
        return redirect(url_for("libros.detalle", libro_id=libro_id))
    flash(f"«{libro['titulo']}» se quitó del catálogo.", "ok")
    return redirect(url_for("libros.lista"))
