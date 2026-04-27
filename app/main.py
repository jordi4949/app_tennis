from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets

from app.database import get_connection

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/Static"), name="static")
templates = Jinja2Templates(directory="app/templates")
security = HTTPBasic()

def comprobar_admin(credentials: HTTPBasicCredentials = Depends(security)):
    usuario_correcto = secrets.compare_digest(credentials.username, "admin")
    password_correcto = secrets.compare_digest(credentials.password, "Jordi_Eduard")

    if not (usuario_correcto and password_correcto):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autorizado",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username

@app.get("/admin", response_class=HTMLResponse)
def inicio(request: Request, admin: str = Depends(comprobar_admin)):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request}
    )

@app.get("/admin/jugadores", response_class=HTMLResponse)
def jugadores(
    request: Request,
    buscar: str = "",
    admin: str = Depends(comprobar_admin)
):
    
    texto_busqueda = f"%{buscar.strip()}%"
    conn = get_connection()
    cur = conn.cursor()

    texto_busqueda = f"%{buscar.strip()}%"

    cur.execute("""
        SELECT id, nombre, apellido1, apellido2, club, ano_nacimiento, numero_licencia
        FROM jugadores
        WHERE
            nombre ILIKE %s
            OR apellido1 ILIKE %s
            OR COALESCE(apellido2, '') ILIKE %s
            OR club ILIKE %s
            OR COALESCE(numero_licencia, '') ILIKE %s
        ORDER BY apellido1, apellido2, nombre
    """, (texto_busqueda, texto_busqueda, texto_busqueda, texto_busqueda, texto_busqueda))

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


@app.post("/admin/jugadores")
def guardar_jugador(
    nombre: str = Form(...),
    apellido1: str = Form(...),
    apellido2: str = Form(""),
    club: str = Form(""),
    ano_nacimiento: int = Form(...),
    numero_licencia: str = Form(""),
    admin: str = Depends(comprobar_admin)
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO jugadores (nombre, apellido1, apellido2, club, ano_nacimiento, numero_licencia)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (nombre, apellido1, apellido2, club, ano_nacimiento, numero_licencia))

    conn.commit()

    cur.close()
    conn.close()

    return RedirectResponse(url="/admin/jugadores", status_code=303)

@app.get("/admin/jugadores/editar/{jugador_id}", response_class=HTMLResponse)
def editar_jugador_form(request: Request, jugador_id: int,
admin: str = Depends(comprobar_admin) 
):
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
        return RedirectResponse(url="/admin/jugadores", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="editar_jugador.html",
        context={
            "request": request,
            "jugador": jugador
        }
    )


@app.post("/admin/jugadores/editar/{jugador_id}")
def actualizar_jugador(
    jugador_id: int,
    nombre: str = Form(...),
    apellido1: str = Form(...),
    apellido2: str = Form(""),
    club: str = Form(""),
    ano_nacimiento: int = Form(...),
    numero_licencia: str = Form(""),
    admin: str = Depends(comprobar_admin)
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

    return RedirectResponse(url="/admin/jugadores", status_code=303)


@app.post("/admin/jugadores/borrar/{jugador_id}")
def borrar_jugador(jugador_id: int,
      admin: str = Depends(comprobar_admin)            
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM jugadores WHERE id = %s", (jugador_id,))

    conn.commit()
    cur.close()
    conn.close()

    return RedirectResponse(url="/admin/jugadores", status_code=303)

@app.get("/admin/importar-jugadores")
def ver_importados(request: Request):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, nombre, apellido1, apellido2, club, ano_nacimiento, numero_licencia
        FROM jugadores_importados
        ORDER BY id DESC
    """)

    jugadores = cur.fetchall()

    cur.close()
    conn.close()

    return templates.TemplateResponse(
        "importar_jugadores.html",
        {"request": request, "jugadores": jugadores}
    )

@app.get("/admin/torneos", response_class=HTMLResponse)
def ver_torneos(request: Request, admin: str = Depends(comprobar_admin)):
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


@app.post("/admin/torneos")
def guardar_torneo(
    nombre: str = Form(...),
    fecha_inicio: str = Form(...),
    categoria: str = Form(...),
    ubicacion: str = Form(...),
    admin: str = Depends(comprobar_admin),
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

    return RedirectResponse(url="/admin/torneos", status_code=303)
@app.get("/admin/torneos/editar/{torneo_id}", response_class=HTMLResponse)
def editar_torneo_form(request: Request, torneo_id: int,
admin: str = Depends(comprobar_admin)
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, nombre, fecha_inicio, categoria, ubicacion
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


@app.post("/admin/torneos/editar/{torneo_id}")
def actualizar_torneo(
    torneo_id: int,
    nombre: str = Form(...),
    fecha_inicio: str = Form(...),
    categoria: str = Form(...),
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
    """, (nombre, fecha_inicio, categoria, ubicacion, torneo_id))

    conn.commit()
    cur.close()
    conn.close()

    return RedirectResponse(url="/admin/torneos", status_code=303)


@app.post("/admin/torneos/borrar/{torneo_id}")
def borrar_torneo(torneo_id: int,
admin: str = Depends(comprobar_admin)
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM torneos WHERE id = %s", (torneo_id,))

    conn.commit()
    cur.close()
    conn.close()

    return RedirectResponse(url="/admin/torneos", status_code=303)

@app.get("/admin/partidos", response_class=HTMLResponse)
def ver_partidos(request: Request,admin: str = Depends(comprobar_admin)):
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

@app.post("/admin/partidos")
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

@app.get("/admin/partidos/editar/{partido_id}", response_class=HTMLResponse)
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


@app.post("/admin/partidos/editar/{partido_id}")
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


@app.post("/admin/partidos/borrar/{partido_id}")
def borrar_partido(partido_id: int,
admin: str = Depends(comprobar_admin)
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM partidos WHERE id = %s", (partido_id,))

    conn.commit()
    cur.close()
    conn.close()

    return RedirectResponse(url="/admin/partidos", status_code=303)

@app.get("/admin/sets", response_class=HTMLResponse)
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

@app.post("/admin/sets")
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

@app.get("/admin/sets/editar/{set_id}", response_class=HTMLResponse)
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


@app.post("/admin/sets/editar/{set_id}")
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


@app.post("/admin/sets/borrar/{set_id}")
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