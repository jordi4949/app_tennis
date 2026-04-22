from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from app.database import get_connection

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
def inicio(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request}
    )


@app.get("/jugadores", response_class=HTMLResponse)
def ver_jugadores(request: Request, buscar: str = ""):
    conn = get_connection()
    cur = conn.cursor()

    texto_busqueda = f"%{buscar.strip()}%"

    cur.execute("""
        SELECT id, nombre, apellido1, apellido2, club, ano_nacimiento
        FROM jugadores
        WHERE
            nombre ILIKE %s
            OR apellido1 ILIKE %s
            OR COALESCE(apellido2, '') ILIKE %s
            OR club ILIKE %s
        ORDER BY apellido1, apellido2, nombre
    """, (texto_busqueda, texto_busqueda, texto_busqueda, texto_busqueda))

    jugadores = cur.fetchall()

    cur.close()
    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="jugadores.html",
        context={
            "request": request,
            "jugadores": jugadores,
            "buscar": buscar
        }
    )


@app.post("/jugadores")
def guardar_jugador(
    nombre: str = Form(...),
    apellido1: str = Form(...),
    apellido2: str = Form(""),
    club: str = Form(""),
    ano_nacimiento: int = Form(...),
    numero_licencia: str = Form("")
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO jugadores (nombre, apellido1, apellido2, club, ano_nacimiento, numero_licencia)
        VALUES (%s, %s, %s, %s, %s)
    """, (nombre, apellido1, apellido2, club, ano_nacimiento, numero_licencia))

    conn.commit()

    cur.close()
    conn.close()

    return RedirectResponse(url="/jugadores", status_code=303)

@app.get("/jugadores/editar/{jugador_id}", response_class=HTMLResponse)
def editar_jugador_form(request: Request, jugador_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, nombre, apellido1, apellido2, club, ano_nacimiento, numero_licencia
        FROM jugadores
        WHERE id = %s
    """, (jugador_id,))
    jugador = cur.fetchone()

    cur.close()
    conn.close()

    if not jugador:
        return RedirectResponse(url="/jugadores", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="editar_jugador.html",
        context={
            "request": request,
            "jugador": jugador
        }
    )


@app.post("/jugadores/editar/{jugador_id}")
def actualizar_jugador(
    jugador_id: int,
    nombre: str = Form(...),
    apellido1: str = Form(...),
    apellido2: str = Form(""),
    club: str = Form(""),
    ano_nacimiento: int = Form(...),
    numero_licencia: str = Form("")
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE jugadores
        SET nombre = %s,
            apellido1 = %s,
            apellido2 = %s,
            club = %s,
            ano_nacimiento = %s,
            numero_licencia = %s
        WHERE id = %s
    """, (nombre, apellido1, apellido2, club, ano_nacimiento, numero_licencia, jugador_id))

    conn.commit()
    cur.close()
    conn.close()

    return RedirectResponse(url="/jugadores", status_code=303)


@app.post("/jugadores/borrar/{jugador_id}")
def borrar_jugador(jugador_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM jugadores WHERE id = %s", (jugador_id,))

    conn.commit()
    cur.close()
    conn.close()

    return RedirectResponse(url="/jugadores", status_code=303)

@app.get("/torneos", response_class=HTMLResponse)
def ver_torneos(request: Request):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, nombre, fecha_inicio, categoria, ubicacion
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


@app.post("/torneos")
def guardar_torneo(
    nombre: str = Form(...),
    fecha_inicio: str = Form(...),
    categoria: str = Form(...),
    ubicacion: str = Form(...)
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO torneos (nombre, fecha_inicio, categoria, ubicacion)
        VALUES (%s, %s, %s, %s)
    """, (nombre, fecha_inicio, categoria, ubicacion))

    conn.commit()

    cur.close()
    conn.close()

    return RedirectResponse(url="/torneos", status_code=303)
@app.get("/partidos", response_class=HTMLResponse)
def ver_partidos(request: Request):
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
        SELECT
            p.id,
            t.nombre AS torneo,
            j1.nombre || ' ' || j1.apellido1 || ' ' || COALESCE(j1.apellido2, '') AS jugador1,
            j2.nombre || ' ' || j2.apellido1 || ' ' || COALESCE(j2.apellido2, '') AS jugador2,
            COALESCE(g.nombre || ' ' || g.apellido1 || ' ' || COALESCE(g.apellido2, ''),'') AS ganador,
            p.ronda,
            p.fecha_partido,
            p.resultado
        FROM partidos p
        JOIN torneos t ON p.torneo_id = t.id
        JOIN jugadores j1 ON p.jugador1_id = j1.id
        JOIN jugadores j2 ON p.jugador2_id = j2.id
        LEFT JOIN jugadores g ON p.ganador_id = g.id
        ORDER BY p.fecha_partido, p.id
    """)
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
            "partidos": partidos
        }
    )

@app.post("/partidos")
def guardar_partido(
    torneo_id: int = Form(...),
    fecha_partido: str = Form(...),
    jugador1_id: int = Form(...),
    jugador2_id: int = Form(...),
    ganador_id: int = Form(...),
    ronda: str = Form(...),
    resultado: str = Form(...)
):
    if jugador1_id == jugador2_id:
        return RedirectResponse(url="/partidos", status_code=303)
    if ganador_id not in (jugador1_id, jugador2_id):
        return RedirectResponse(url="/partidos", status_code=303)

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

    return RedirectResponse(url="/partidos", status_code=303)

@app.get("/sets", response_class=HTMLResponse)
def ver_sets(request: Request):
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

@app.post("/sets")
def guardar_set(
    partido_id: int = Form(...),
    numero_set: int = Form(...),
    juegos_jugador1: int = Form(...),
    juegos_jugador2: int = Form(...),
    tiebreak_jugador1: int = Form(None),
    tiebreak_jugador2: int = Form(None),
    tipo_set: int = Form(...)
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
        return RedirectResponse(url="/sets", status_code=303)

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

    return RedirectResponse(url="/sets", status_code=303)