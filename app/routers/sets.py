from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core import comprobar_admin, templates
from app.database import get_connection

router = APIRouter()

@router.get("/admin/sets", response_class=HTMLResponse)
def ver_sets(request: Request,
admin: str = Depends(comprobar_admin)
):
    conn = get_connection()
    cur = conn.cursor()

    # Traer sets ya preparados para mostrar bonito
    cur.execute("""
        SELECT
            s.id,
            s.partido_id,
            s.numero_set,
            s.juegos_jugador1,
            s.juegos_jugador2,
            COALESCE(s.tiebreak_jugador1, 0) AS tiebreak_jugador1,
            COALESCE(s.tiebreak_jugador2, 0) AS tiebreak_jugador2,
            s.tipo_set,

            p.jugador1_id,
            p.jugador2_id,
            p.ganador_id,
            p.ronda,

            j1.nombre || ' ' || j1.apellido1 || ' ' || COALESCE(j1.apellido2, '') AS jugador1,
            j2.nombre || ' ' || j2.apellido1 || ' ' || COALESCE(j2.apellido2, '') AS jugador2,
            g.nombre || ' ' || g.apellido1 || ' ' || COALESCE(g.apellido2, '') AS ganador
        FROM sets s
        JOIN partidos p ON s.partido_id = p.id
        JOIN jugadores j1 ON p.jugador1_id = j1.id
        JOIN jugadores j2 ON p.jugador2_id = j2.id
        JOIN jugadores g ON p.ganador_id = g.id
        ORDER BY s.partido_id, s.numero_set
    """)
    filas_sets = cur.fetchall()

    sets_bonitos = []

    for fila in filas_sets:
        (
            set_id,
            partido_id,
            numero_set,
            juegos_jugador1,
            juegos_jugador2,
            tiebreak_jugador1,
            tiebreak_jugador2,
            tipo_set,
            jugador1_id,
            jugador2_id,
            ganador_id,
            ronda,
            jugador1,
            jugador2,
            ganador
        ) = fila

        if ganador_id == jugador1_id:
            juegos_ganador = juegos_jugador1
            juegos_rival = juegos_jugador2
            tiebreak_ganador = tiebreak_jugador1
            tiebreak_rival = tiebreak_jugador2
        else:
            juegos_ganador = juegos_jugador2
            juegos_rival = juegos_jugador1
            tiebreak_ganador = tiebreak_jugador2
            tiebreak_rival = tiebreak_jugador1

        if tipo_set == 1:
            tipo_set_texto = "Set normal"
        elif tipo_set == 2:
            tipo_set_texto = "Set con tiebreak"
        elif tipo_set == 3:
            tipo_set_texto = "Super tiebreak"
        else:
            tipo_set_texto = "No definido"

        sets_bonitos.append({
            "id": set_id,
            "partido_id": partido_id,
            "partido": f"{jugador1.strip()} vs {jugador2.strip()}",
            "ganador": ganador.strip(),
            "ronda": ronda,
            "numero_set": numero_set,
            "juegos_ganador": juegos_ganador,
            "juegos_rival": juegos_rival,
            "resultado_set": f"{juegos_ganador}-{juegos_rival}",
            "tiebreak_ganador": tiebreak_ganador,
            "tiebreak_rival": tiebreak_rival,
            "tipo_set": tipo_set_texto
        })

    # Traer partidos para el desplegable del formulario
    cur.execute("""
        SELECT
            p.id,
            j1.nombre,
            j1.apellido1,
            j2.nombre,
            j2.apellido1,
            p.resultado,
            p.ronda,
            p.fecha_partido,
            g.nombre,
            g.apellido1
        FROM partidos p
        JOIN jugadores j1 ON p.jugador1_id = j1.id
        JOIN jugadores j2 ON p.jugador2_id = j2.id
        JOIN jugadores g ON p.ganador_id = g.id
        ORDER BY p.fecha_partido, p.id
    """)
    partidos = cur.fetchall()

    cur.close()
    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="sets.html",
        context={
            "request": request,
            "sets": sets_bonitos,
            "partidos": partidos
        }
    )

@router.post("/admin/sets")
def guardar_set(
    partido_id: int = Form(...),
    numero_set: int = Form(...),
    juegos_jugador1: int = Form(...),
    juegos_jugador2: int = Form(...),
    tiebreak_jugador1: int = Form(None),
    tiebreak_jugador2: int = Form(None),
    tipo_set: int = Form(...),
    admin: str = Depends(comprobar_admin)
):
    conn = get_connection()
    cur = conn.cursor()
    # Comprobar si ya existe ese set para ese partido
    cur.execute("""
        SELECT id
        FROM sets
        WHERE partido_id = %s AND numero_set = %s
    """, (partido_id, numero_set))

    set_existente = cur.fetchone()

    if set_existente:
        cur.close()
        conn.close()
        return RedirectResponse(url="/admin/sets", status_code=303)

    cur.execute("""
        INSERT INTO sets (
            partido_id,
            numero_set,
            juegos_jugador1,
            juegos_jugador2,
            tiebreak_jugador1,
            tiebreak_jugador2,
            tipo_set
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        partido_id,
        numero_set,
        juegos_jugador1,
        juegos_jugador2,
        tiebreak_jugador1,
        tiebreak_jugador2,
        tipo_set
    ))

    conn.commit()
    cur.close()
    conn.close()

    return RedirectResponse(url="/admin/sets", status_code=303)

@router.get("/admin/sets/editar/{set_id}", response_class=HTMLResponse)
def editar_set_form(request: Request, set_id: int,
admin: str = Depends(comprobar_admin)
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            p.id,
            j1.nombre || ' ' || j1.apellido1 || ' ' || COALESCE(j1.apellido2, '') AS jugador1,
            j2.nombre || ' ' || j2.apellido1 || ' ' || COALESCE(j2.apellido2, '') AS jugador2,
            p.resultado,
            p.ronda,
            p.fecha_partido
        FROM partidos p
        JOIN jugadores j1 ON p.jugador1_id = j1.id
        JOIN jugadores j2 ON p.jugador2_id = j2.id
        ORDER BY p.fecha_partido, p.id
    """)
    partidos = cur.fetchall()

    cur.execute("""
        SELECT
            id,
            partido_id,
            numero_set,
            juegos_jugador1,
            juegos_jugador2,
            COALESCE(tiebreak_jugador1, 0),
            COALESCE(tiebreak_jugador2, 0),
            tipo_set
        FROM sets
        WHERE id = %s
    """, (set_id,))
    set_item = cur.fetchone()

    cur.close()
    conn.close()

    if not set_item:
        return RedirectResponse(url="/admin/sets", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="editar_set.html",
        context={
            "request": request,
            "set_item": set_item,
            "partidos": partidos
        }
    )


@router.post("/admin/sets/editar/{set_id}")
def actualizar_set(
    set_id: int,
    partido_id: int = Form(...),
    numero_set: int = Form(...),
    juegos_jugador1: int = Form(...),
    juegos_jugador2: int = Form(...),
    tiebreak_jugador1: int = Form(0),
    tiebreak_jugador2: int = Form(0),
    tipo_set: int = Form(...),
    admin: str = Depends(comprobar_admin)
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id
        FROM sets
        WHERE partido_id = %s
          AND numero_set = %s
          AND id <> %s
    """, (partido_id, numero_set, set_id))
    set_duplicado = cur.fetchone()

    if set_duplicado:
        cur.close()
        conn.close()
        return RedirectResponse(url="/admin/sets", status_code=303)

    cur.execute("""
        UPDATE sets
        SET partido_id = %s,
            numero_set = %s,
            juegos_jugador1 = %s,
            juegos_jugador2 = %s,
            tiebreak_jugador1 = %s,
            tiebreak_jugador2 = %s,
            tipo_set = %s
        WHERE id = %s
    """, (
        partido_id,
        numero_set,
        juegos_jugador1,
        juegos_jugador2,
        tiebreak_jugador1,
        tiebreak_jugador2,
        tipo_set,
        set_id
    ))

    conn.commit()
    cur.close()
    conn.close()

    return RedirectResponse(url="/admin/sets", status_code=303)


@router.post("/admin/sets/borrar/{set_id}")
def borrar_set(set_id: int,
admin: str = Depends(comprobar_admin)
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM sets WHERE id = %s", (set_id,))

    conn.commit()
    cur.close()
    conn.close()

    return RedirectResponse(url="/admin/sets", status_code=303)
