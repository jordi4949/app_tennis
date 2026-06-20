from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core import comprobar_admin, templates
from app.database import get_connection

router = APIRouter()

@router.get("/admin/torneos", response_class=HTMLResponse)
def ver_torneos(request: Request, admin: str = Depends(comprobar_admin)):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, nombre, fecha_inicio, ubicacion
        FROM torneos
        ORDER BY id;
    """)
    torneos = cur.fetchall()

    cur.close()
    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="torneos.html",
        context={
            "request": request,
            "torneos": torneos
        }
    )


@router.post("/admin/torneos")
def guardar_torneo(
    nombre: str = Form(...),
    fecha_inicio: str = Form(...),
    ubicacion: str = Form(...),
    admin: str = Depends(comprobar_admin)
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO torneos (nombre, fecha_inicio, categoria, ubicacion)
        VALUES (%s, %s, %s, %s)
    """, (nombre, fecha_inicio, "", ubicacion))

    conn.commit()

    cur.close()
    conn.close()

    return RedirectResponse(url="/admin/torneos", status_code=303)
@router.get("/admin/torneos/editar/{torneo_id}", response_class=HTMLResponse)
def editar_torneo_form(request: Request, torneo_id: int,
admin: str = Depends(comprobar_admin)
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, nombre, fecha_inicio, ubicacion
        FROM torneos
        WHERE id = %s
    """, (torneo_id,))

    torneo = cur.fetchone()

    cur.close()
    conn.close()

    if not torneo:
        return RedirectResponse(url="/admin/torneos", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="editar_torneo.html",
        context={
            "request": request,
            "torneo": torneo
        }
    )


@router.post("/admin/torneos/editar/{torneo_id}")
def actualizar_torneo(
    torneo_id: int,
    nombre: str = Form(...),
    fecha_inicio: str = Form(...),
    ubicacion: str = Form(...),
    admin: str = Depends(comprobar_admin)
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE torneos
        SET nombre = %s,
            fecha_inicio = %s,
            categoria = %s,
            ubicacion = %s
        WHERE id = %s
    """, (nombre, fecha_inicio, "", ubicacion, torneo_id))

    conn.commit()
    cur.close()
    conn.close()

    return RedirectResponse(url="/admin/torneos", status_code=303)


@router.post("/admin/torneos/borrar/{torneo_id}")
def borrar_torneo(torneo_id: int,
admin: str = Depends(comprobar_admin)
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*)
        FROM cuadros
        WHERE torneo_id = %s
    """, (torneo_id,))
    cuadros_relacionados = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM partidos
        WHERE torneo_id = %s
    """, (torneo_id,))
    partidos_relacionados = cur.fetchone()[0]

    if cuadros_relacionados or partidos_relacionados:
        cur.close()
        conn.close()
        return RedirectResponse(url="/admin/torneos", status_code=303)

    cur.execute("DELETE FROM torneos WHERE id = %s", (torneo_id,))

    conn.commit()
    cur.close()
    conn.close()

    return RedirectResponse(url="/admin/torneos", status_code=303)
