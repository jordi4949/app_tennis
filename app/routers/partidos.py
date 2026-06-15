from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core import comprobar_admin, templates
from app.database import get_connection

router = APIRouter()

@router.get("/admin/partidos", response_class=HTMLResponse)
def ver_partidos(
    request: Request,
    buscar: str = "",
    buscar_jugador: str = "",
    buscar_rival: str = "",
    admin: str = Depends(comprobar_admin)
):
    conn = get_connection()
    cur = conn.cursor()

    condiciones = []
    parametros = []

    def texto_jugador(alias: str) -> str:
        return (
            f"{alias}.nombre || ' ' || "
            f"{alias}.apellido1 || ' ' || "
            f"COALESCE({alias}.apellido2, '')"
        )

    def condicion_jugador(alias: str) -> str:
        return f"""
            (
                {alias}.nombre ILIKE %s
                OR {alias}.apellido1 ILIKE %s
                OR COALESCE({alias}.apellido2, '') ILIKE %s
                OR ({texto_jugador(alias)}) ILIKE %s
            )
        """

    if buscar.strip():
        texto_busqueda = f"%{buscar.strip()}%"
        condiciones.append(f"""
            (
                t.nombre ILIKE %s
                OR COALESCE(c.nombre, '') ILIKE %s
                OR COALESCE(cat.nombre, '') ILIKE %s
                OR COALESCE(gen.nombre, '') ILIKE %s
                OR {condicion_jugador("j1")}
                OR {condicion_jugador("j2")}
                OR COALESCE(g.nombre, '') ILIKE %s
                OR COALESCE(g.apellido1, '') ILIKE %s
                OR COALESCE(g.apellido2, '') ILIKE %s
                OR ({texto_jugador("g")}) ILIKE %s
                OR COALESCE(p.ronda, '') ILIKE %s
                OR COALESCE(p.resultado, '') ILIKE %s
            )
        """)
        parametros.extend([texto_busqueda] * 18)

    if buscar_jugador.strip() and buscar_rival.strip():
        texto_jugador_busqueda = f"%{buscar_jugador.strip()}%"
        texto_rival_busqueda = f"%{buscar_rival.strip()}%"
        condiciones.append(f"""
            (
                ({condicion_jugador("j1")} AND {condicion_jugador("j2")})
                OR
                ({condicion_jugador("j2")} AND {condicion_jugador("j1")})
            )
        """)
        parametros.extend(
            [texto_jugador_busqueda] * 4
            + [texto_rival_busqueda] * 4
            + [texto_jugador_busqueda] * 4
            + [texto_rival_busqueda] * 4
        )
    elif buscar_jugador.strip():
        texto_jugador_busqueda = f"%{buscar_jugador.strip()}%"
        condiciones.append(f"""
            (
                {condicion_jugador("j1")}
                OR {condicion_jugador("j2")}
            )
        """)
        parametros.extend([texto_jugador_busqueda] * 8)
    elif buscar_rival.strip():
        texto_rival_busqueda = f"%{buscar_rival.strip()}%"
        condiciones.append(f"""
            (
                {condicion_jugador("j1")}
                OR {condicion_jugador("j2")}
            )
        """)
        parametros.extend([texto_rival_busqueda] * 8)

    where_sql = ""
    if condiciones:
        where_sql = "WHERE " + " AND ".join(condiciones)

    cur.execute("""
        SELECT id, nombre, fecha_inicio, categoria, ubicacion
        FROM torneos
        ORDER BY id
    """)
    torneos = cur.fetchall()

    cur.execute("""
        SELECT id, nombre, apellido1, apellido2
        FROM jugadores
        ORDER BY apellido1, apellido2, nombre
    """)
    jugadores = cur.fetchall()

    cur.execute("""
        SELECT
            p.id,
            t.nombre AS torneo,
            COALESCE(c.nombre, '') AS cuadro,
            COALESCE(cat.nombre, '') AS categoria,
            COALESCE(gen.nombre, '') AS genero,
            j1.nombre || ' ' || j1.apellido1 || ' ' || COALESCE(j1.apellido2, '') AS jugador1,
            j2.nombre || ' ' || j2.apellido1 || ' ' || COALESCE(j2.apellido2, '') AS jugador2,
            COALESCE(g.nombre || ' ' || g.apellido1 || ' ' || COALESCE(g.apellido2, ''),'') AS ganador,
            CASE
                WHEN p.ronda ILIKE 'Treintaidosavos' THEN '1/32'
                WHEN p.ronda ILIKE 'Dieciseisavos' THEN '1/16'
                WHEN p.ronda ILIKE 'Octavos' THEN '1/8'
                WHEN p.ronda ILIKE 'Cuartos' THEN '1/4'
                WHEN p.ronda ILIKE 'Semifinal' THEN 'SF'
                WHEN p.ronda ILIKE 'Final' THEN 'F'
                ELSE p.ronda
            END AS ronda_corta,
            p.fecha_partido,
            p.resultado
        FROM partidos p
        JOIN torneos t ON p.torneo_id = t.id
        LEFT JOIN cuadros c ON p.cuadro_id = c.id
        LEFT JOIN categorias cat ON c.categoria_id = cat.id
        LEFT JOIN generos gen ON c.genero_id = gen.id
        JOIN jugadores j1 ON p.jugador1_id = j1.id
        JOIN jugadores j2 ON p.jugador2_id = j2.id
        LEFT JOIN jugadores g ON p.ganador_id = g.id
        {where_sql}
        ORDER BY p.fecha_partido DESC, t.nombre, c.nombre, p.ronda_numero, p.posicion_ronda
    """, parametros)
                
    partidos = cur.fetchall()

    cur.close()
    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="partidos.html",
        context={
        
            "request": request,
            "torneos": torneos,
            "jugadores": jugadores,
            "partidos": partidos,
            "buscar": buscar,
            "buscar_jugador": buscar_jugador,
            "buscar_rival": buscar_rival
        }
    )

@router.post("/admin/partidos")
def guardar_partido(
    torneo_id: int = Form(...),
    fecha_partido: str = Form(...),
    jugador1_id: int = Form(...),
    jugador2_id: int = Form(...),
    ganador_id: int = Form(...),
    ronda: str = Form(...),
    resultado: str = Form(...),
    admin: str = Depends(comprobar_admin)
):
    if jugador1_id == jugador2_id:
        return RedirectResponse(url="/admin/partidos", status_code=303)
    if ganador_id not in (jugador1_id, jugador2_id):
        return RedirectResponse(url="/admin/partidos", status_code=303)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO partidos (
            torneo_id,
            fecha_partido,
            jugador1_id,
            jugador2_id,
            ganador_id,
            ronda,
            resultado
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        torneo_id,
        fecha_partido,
        jugador1_id,
        jugador2_id,
        ganador_id,
        ronda,
        resultado
    ))

    conn.commit()
    cur.close()
    conn.close()

    return RedirectResponse(url="/admin/partidos", status_code=303)

@router.get("/admin/partidos/editar/{partido_id}", response_class=HTMLResponse)
def editar_partido_form(request: Request, partido_id: int,
admin: str = Depends(comprobar_admin)
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, nombre, fecha_inicio, categoria, ubicacion
        FROM torneos
        ORDER BY id
    """)
    torneos = cur.fetchall()

    cur.execute("""
        SELECT id, nombre, apellido1, apellido2
        FROM jugadores
        ORDER BY apellido1, apellido2, nombre
    """)
    jugadores = cur.fetchall()

    cur.execute("""
        SELECT id, torneo_id, fecha_partido, jugador1_id, jugador2_id, ganador_id, ronda, resultado
        FROM partidos
        WHERE id = %s
    """, (partido_id,))
    partido = cur.fetchone()

    cur.close()
    conn.close()

    if not partido:
        return RedirectResponse(url="/admin/partidos", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="editar_partido.html",
        context={
            "request": request,
            "partido": partido,
            "torneos": torneos,
            "jugadores": jugadores
        }
    )


@router.post("/admin/partidos/editar/{partido_id}")
def actualizar_partido(
    partido_id: int,
    torneo_id: int = Form(...),
    fecha_partido: str = Form(...),
    jugador1_id: int = Form(...),
    jugador2_id: int = Form(...),
    ganador_id: int = Form(...),
    ronda: str = Form(...),
    resultado: str = Form(...),
    admin: str = Depends(comprobar_admin)
):
    if jugador1_id == jugador2_id:
        return RedirectResponse(url="/admin/partidos", status_code=303)
    if ganador_id not in (jugador1_id, jugador2_id):
        return RedirectResponse(url="/admin/partidos", status_code=303)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE partidos
        SET torneo_id = %s,
            fecha_partido = %s,
            jugador1_id = %s,
            jugador2_id = %s,
            ganador_id = %s,
            ronda = %s,
            resultado = %s
        WHERE id = %s
    """, (torneo_id, fecha_partido, jugador1_id, jugador2_id, ganador_id, ronda, resultado, partido_id))

    conn.commit()
    cur.close()
    conn.close()

    return RedirectResponse(url="/admin/partidos", status_code=303)


@router.post("/admin/partidos/borrar/{partido_id}")
def borrar_partido(partido_id: int,
admin: str = Depends(comprobar_admin)
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*)
        FROM sets
        WHERE partido_id = %s
    """, (partido_id,))
    sets_relacionados = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM rondas_cuadro
        WHERE partido_id = %s
    """, (partido_id,))
    rondas_relacionadas = cur.fetchone()[0]

    if sets_relacionados or rondas_relacionadas:
        cur.close()
        conn.close()
        return RedirectResponse(url="/admin/partidos", status_code=303)

    cur.execute("DELETE FROM partidos WHERE id = %s", (partido_id,))

    conn.commit()
    cur.close()
    conn.close()

    return RedirectResponse(url="/admin/partidos", status_code=303)
