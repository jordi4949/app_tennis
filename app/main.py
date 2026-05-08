from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
from rapidfuzz import process, fuzz
import unicodedata
import re
import os
from dotenv import load_dotenv
load_dotenv()
from fastapi import UploadFile, File
from openpyxl import load_workbook


from app.database import get_connection

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/Static"), name="static")
templates = Jinja2Templates(directory="app/templates")
security = HTTPBasic()

def comprobar_admin(credentials: HTTPBasicCredentials = Depends(security)):
    ADMIN_USER = os.getenv("ADMIN_USER")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

    usuario_correcto = secrets.compare_digest(credentials.username, ADMIN_USER)
    password_correcto = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)

    if not (usuario_correcto and password_correcto):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autorizado",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username

def normalizar_club_para_comparar(texto: str) -> str:
    if not texto:
        return ""

    texto = texto.upper().strip()

    # Quitar acentos
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")

    # Errores típicos OCR
    texto = texto.replace("0", "O")
    texto = texto.replace("1", "I")

    # Separar comas pegadas: "BARCINO,CT" -> "BARCINO CT"
    texto = texto.replace(",", " ")

    # Quitar símbolos raros: puntos, guiones, apóstrofes, etc.
    texto = re.sub(r"[^A-Z0-9 ]", " ", texto)

    # Normalizar abreviaturas frecuentes
    texto = re.sub(r"\bC T\b", "CT", texto)
    texto = re.sub(r"\bT\b", "CT", texto)

    # Espacios repetidos
    texto = re.sub(r"\s+", " ", texto).strip()

    return texto

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
    ordenar: str = "apellido",
    admin: str = Depends(comprobar_admin)
):
    texto_busqueda = f"%{buscar.strip()}%"

    if ordenar == "club":
        order_by = "club, apellido1, apellido2, nombre"
    elif ordenar == "licencia":
        order_by = "NULLIF(numero_licencia, '') NULLS LAST, apellido1, apellido2, nombre"
    else:
        order_by = "apellido1, apellido2, nombre"

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(f"""
        SELECT id, nombre, apellido1, apellido2, club, ano_nacimiento, numero_licencia
        FROM jugadores
        WHERE
            nombre ILIKE %s
            OR apellido1 ILIKE %s
            OR COALESCE(apellido2, '') ILIKE %s
            OR club ILIKE %s
            OR COALESCE(numero_licencia, '') ILIKE %s
        ORDER BY {order_by}
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
            "buscar": buscar,
            "ordenar": ordenar
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
def ver_importados(
    request: Request,
    buscar: str = "",
    ordenar: str = "apellido",
    admin: str = Depends(comprobar_admin)
):
    if ordenar == "club":
        order_by = "club, apellido1, apellido2, nombre"
    elif ordenar == "licencia":
        order_by = "NULLIF(numero_licencia, '') NULLS LAST, apellido1, apellido2, nombre"
    else:
        order_by = "apellido1, apellido2, nombre"

    conn = get_connection()
    cur = conn.cursor()

    if buscar:
        texto_busqueda = f"%{buscar.strip()}%"

        cur.execute(f"""
            SELECT id, nombre, apellido1, apellido2, club, ano_nacimiento, numero_licencia
            FROM jugadores_importados
            WHERE nombre ILIKE %s
               OR apellido1 ILIKE %s
               OR COALESCE(apellido2, '') ILIKE %s
               OR club ILIKE %s
               OR COALESCE(numero_licencia, '') ILIKE %s
            ORDER BY {order_by}
        """, (texto_busqueda, texto_busqueda, texto_busqueda, texto_busqueda, texto_busqueda))
    else:
        cur.execute(f"""
            SELECT id, nombre, apellido1, apellido2, club, ano_nacimiento, numero_licencia
            FROM jugadores_importados
            ORDER BY {order_by}
        """)

    jugadores = cur.fetchall()

    cur.close()
    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="importar_jugadores.html",
        context={
            "request": request,
            "jugadores": jugadores,
            "buscar": buscar,
            "ordenar": ordenar
        }
    )

@app.post("/admin/importar-jugadores/corregir-clubs")
def corregir_clubs_importados(admin: str = Depends(comprobar_admin)):
    conn = get_connection()
    cur = conn.cursor()

    # Clubs distintos que vienen del OCR
    cur.execute("""
        SELECT DISTINCT club
        FROM jugadores_importados
        WHERE club IS NOT NULL
          AND TRIM(club) <> ''
    """)
    clubs_importados = [fila[0] for fila in cur.fetchall()]

    # Clubs buenos desde tabla clubs
    cur.execute("""
        SELECT nombre
        FROM clubs
        WHERE nombre IS NOT NULL
          AND TRIM(nombre) <> ''
    """)
    clubs_tabla = [fila[0] for fila in cur.fetchall()]

    # Clubs buenos desde jugadores ya aprobados
    cur.execute("""
        SELECT DISTINCT club
        FROM jugadores
        WHERE club IS NOT NULL
          AND TRIM(club) <> ''
    """)
    clubs_jugadores = [fila[0] for fila in cur.fetchall()]

    clubs_buenos = sorted(set(clubs_tabla + clubs_jugadores))

    if not clubs_importados or not clubs_buenos:
        cur.close()
        conn.close()
        return RedirectResponse(
            url="/admin/importar-jugadores?ordenar=club",
            status_code=303
        )

    clubs_buenos_normalizados = {
        normalizar_club_para_comparar(club): club
        for club in clubs_buenos
    }

    for club_importado in clubs_importados:
        club_importado_norm = normalizar_club_para_comparar(club_importado)

        mejor = process.extractOne(
            club_importado_norm,
            list(clubs_buenos_normalizados.keys()),
            scorer=fuzz.WRatio
        )

        if not mejor:
            continue

        club_bueno_norm, puntuacion, _ = mejor
        club_bueno = clubs_buenos_normalizados[club_bueno_norm]

        # Umbral alto para evitar cambios peligrosos.
        # Si corrige poco, luego bajamos a 85.
        if puntuacion >= 88 and club_importado != club_bueno:
            cur.execute("""
                UPDATE jugadores_importados
                SET club = %s
                WHERE club = %s
            """, (club_bueno, club_importado))

    conn.commit()
    cur.close()
    conn.close()

    return RedirectResponse(
        url="/admin/importar-jugadores?ordenar=club",
        status_code=303
    )

    
@app.get("/admin/importar-jugadores/aprobar/{jugador_id}")
def aprobar_jugador_importado(
    jugador_id: int,
    admin: str = Depends(comprobar_admin)
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT nombre, apellido1, apellido2, club, ano_nacimiento, numero_licencia
        FROM jugadores_importados
        WHERE id = %s
    """, (jugador_id,))

    jugador = cur.fetchone()

    if jugador:
        cur.execute("""
            INSERT INTO clubs (nombre)
            VALUES (%s)
            ON CONFLICT (nombre) DO NOTHING
        """, (jugador[3],))
        
        cur.execute("""
            INSERT INTO jugadores
            (nombre, apellido1, apellido2, club, ano_nacimiento, numero_licencia)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (numero_licencia) DO NOTHING
        """, jugador)

        cur.execute("""
            DELETE FROM jugadores_importados
            WHERE id = %s
        """, (jugador_id,))

        conn.commit()

    cur.close()
    conn.close()

    return RedirectResponse(url="/admin/importar-jugadores", status_code=303)

@app.get("/admin/importar-jugadores/borrar/{jugador_id}")
def borrar_importado(
    jugador_id: int,
    admin: str = Depends(comprobar_admin)
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM jugadores_importados
        WHERE id = %s
    """, (jugador_id,))

    conn.commit()

    cur.close()
    conn.close()

    return RedirectResponse(url="/admin/importar-jugadores", status_code=303)

@app.get("/admin/importar-jugadores/editar/{jugador_id}")
def editar_importado(
    request: Request,
    jugador_id: int,
    admin: str = Depends(comprobar_admin)
):
    conn = get_connection()
    cur = conn.cursor()

    # jugador
    cur.execute("""
        SELECT id, nombre, apellido1, apellido2, club, ano_nacimiento, numero_licencia
        FROM jugadores_importados
        WHERE id = %s
    """, (jugador_id,))
    jugador = cur.fetchone()

    # lista de clubs existentes
    cur.execute("""
    SELECT nombre
    FROM clubs
    ORDER BY nombre ASC
""")
    
    clubs = cur.fetchall()

    cur.close()
    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="editar_jugador_importado.html",
        context={
            "request": request,
            "jugador": jugador,
            "clubs": clubs
        }
    )
@app.post("/admin/importar-jugadores/editar/{jugador_id}")
def guardar_importado(
    jugador_id: int,
    nombre: str = Form(...),
    apellido1: str = Form(...),
    apellido2: str = Form(""),
    club_existente: str = Form(""),
    club_nuevo: str = Form(""),
    ano_nacimiento: int = Form(...),
    numero_licencia: str = Form(...),
    admin: str = Depends(comprobar_admin)
):
    conn = get_connection()
    cur = conn.cursor()

    club_final = club_nuevo.strip() if club_nuevo.strip() else club_existente
    cur.execute("""
        INSERT INTO clubs (nombre)
        VALUES (%s)
        ON CONFLICT (nombre) DO NOTHING
    """, (club_final,))


    cur.execute("""
        UPDATE jugadores_importados
        SET nombre=%s, apellido1=%s, apellido2=%s,
            club=%s, ano_nacimiento=%s, numero_licencia=%s
        WHERE id=%s
    """, (
        nombre, apellido1, apellido2,
        club_final, ano_nacimiento, numero_licencia,
        jugador_id
    ))

    conn.commit()
    cur.close()
    conn.close()

    return RedirectResponse("/admin/importar-jugadores", status_code=303)

@app.post("/admin/importar-jugadores/aprobar-seleccionados")
def aprobar_seleccionados(
    jugadores_ids: list[int] = Form(...),
    admin: str = Depends(comprobar_admin)
):
    conn = get_connection()
    cur = conn.cursor()

    for jugador_id in jugadores_ids:

        cur.execute("""
            SELECT nombre, apellido1, apellido2, club, ano_nacimiento, numero_licencia
            FROM jugadores_importados
            WHERE id = %s
        """, (jugador_id,))

        jugador = cur.fetchone()

        if jugador:
            # Insertar club
            cur.execute("""
                INSERT INTO clubs (nombre)
                VALUES (%s)
                ON CONFLICT (nombre) DO NOTHING
            """, (jugador[3],))

            # Insertar jugador
            cur.execute("""
                INSERT INTO jugadores
                (nombre, apellido1, apellido2, club, ano_nacimiento, numero_licencia)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (numero_licencia) DO NOTHING
            """, jugador)

            # Borrar importado
            cur.execute("""
                DELETE FROM jugadores_importados
                WHERE id = %s
            """, (jugador_id,))

    conn.commit()
    cur.close()
    conn.close()

    return RedirectResponse("/admin/importar-jugadores", status_code=303)

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

@app.get("/admin/cuadros", response_class=HTMLResponse)
def ver_cuadros(
    request: Request,
    torneo_id: int = 0
    admin: str = Depends(comprobar_admin)
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, nombre, fecha_inicio, categoria, ubicacion
        FROM torneos
        ORDER BY fecha_inicio DESC, nombre
    """)
    torneos = cur.fetchall()

    if torneo_id != 0:
        cur.execute("""
            SELECT
                c.id,
                c.nombre,
                c.tamano,
                c.numero_jugadores,
                COALESCE(c.observaciones, ''),
                t.nombre,
                t.fecha_inicio,
                t.categoria,
                t.ubicacion
            FROM cuadros c
            JOIN torneos t ON c.torneo_id = t.id
            WHERE c.torneo_id = %s
            ORDER BY c.nombre
        """, (torneo_id,))
    else:
        cur.execute("""
            SELECT
                c.id,
                c.nombre,
                c.tamano,
                c.numero_jugadores,
                COALESCE(c.observaciones, ''),
                t.nombre,
                t.fecha_inicio,
                t.categoria,
                t.ubicacion
            FROM cuadros c
            JOIN torneos t ON c.torneo_id = t.id
            ORDER BY t.fecha_inicio DESC, t.nombre, c.nombre
        """)

    cuadros = cur.fetchall()

    cur.close()
    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="cuadros.html",
        context={
            "request": request,
            "torneos": torneos,
            "cuadros": cuadros,
            "torneo_id": torneo_id
        }
    )

@app.get("/admin/cuadros/{cuadro_id}/inscritos", response_class=HTMLResponse)
def ver_inscritos(
    cuadro_id: int,
    request: Request,
    admin: str = Depends(comprobar_admin)
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            ci.id,
            ci.numero_licencia,
            ci.nombre_excel,
            j.id,
            j.nombre,
            j.apellido1,
            j.apellido2,
            ci.estado
        FROM cuadro_inscritos ci
        LEFT JOIN jugadores j ON ci.jugador_id = j.id
        WHERE ci.cuadro_id = %s
        ORDER BY ci.id
    """, (cuadro_id,))

    inscritos = cur.fetchall()

    cur.close()
    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="inscritos.html",
        context={
            "request": request,
            "inscritos": inscritos,
            "cuadro_id": cuadro_id
        }
    )

@app.post("/admin/cuadros/{cuadro_id}/importar-inscritos")
def importar_inscritos_desde_excel(
    cuadro_id: int,
    admin: str = Depends(comprobar_admin)
):
    conn = get_connection()
    cur = conn.cursor()

    # Buscar ruta_excel del cuadro
    cur.execute("""
        SELECT ruta_excel
        FROM cuadros
        WHERE id = %s
    """, (cuadro_id,))
    fila = cur.fetchone()

    if not fila or not fila[0]:
        cur.close()
        conn.close()
        return RedirectResponse(
            url=f"/admin/cuadros/{cuadro_id}/inscritos",
            status_code=303
        )

    ruta_excel = fila[0]

    # Si la ruta es relativa, la convertimos a absoluta desde la raíz del proyecto
    if not os.path.isabs(ruta_excel):
        ruta_excel = os.path.join(os.getcwd(), ruta_excel)

    wb = load_workbook(ruta_excel)
    ws = wb.active

    # Limpiar inscritos anteriores de ese cuadro para no duplicar
    cur.execute("""
        DELETE FROM cuadro_inscritos
        WHERE cuadro_id = %s
    """, (cuadro_id,))

    for fila_excel in ws.iter_rows(min_row=2):
        licencia = fila_excel[1].value  # Columna B
        nombre_excel = fila_excel[2].value  # Columna C

        if not licencia:
            continue

        licencia = str(licencia).strip().replace(".0", "")

        cur.execute("""
            SELECT id
            FROM jugadores
            WHERE TRIM(numero_licencia) = %s
        """, (licencia,))

        jugador = cur.fetchone()

        if jugador:
            jugador_id = jugador[0]
            estado = "encontrado"
        else:
            jugador_id = None
            estado = "no_encontrado"

        cur.execute("""
            INSERT INTO cuadro_inscritos
            (cuadro_id, jugador_id, numero_licencia, nombre_excel, estado)
            VALUES (%s, %s, %s, %s, %s)
        """, (cuadro_id, jugador_id, licencia, nombre_excel, estado))

    conn.commit()
    cur.close()
    conn.close()

    return RedirectResponse(
        url=f"/admin/cuadros/{cuadro_id}/inscritos",
        status_code=303
    )

@app.post("/admin/cuadros")
def guardar_cuadro(
    torneo_id: int = Form(...),
    nombre: str = Form(...),
    tamano: int = Form(...),
    numero_jugadores: int = Form(...),
    observaciones: str = Form(""),
    ruta_excel: str = Form(""),
    admin: str = Depends(comprobar_admin)
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO cuadros (torneo_id, nombre, tamano, numero_jugadores, observaciones, ruta_excel)
    VALUES (%s, %s, %s, %s, %s, %s)
""", (torneo_id, nombre, tamano, numero_jugadores, observaciones, ruta_excel))

    conn.commit()
    cur.close()
    conn.close()

    return RedirectResponse(url="/admin/cuadros", status_code=303)

@app.get("/admin/cuadros/editar/{cuadro_id}", response_class=HTMLResponse)
def editar_cuadro_form(
    request: Request,
    cuadro_id: int,
    admin: str = Depends(comprobar_admin)
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, nombre, fecha_inicio, categoria, ubicacion
        FROM torneos
        ORDER BY fecha_inicio DESC, nombre
    """)
    torneos = cur.fetchall()

    cur.execute("""
        SELECT id, torneo_id, nombre, tamano, numero_jugadores, COALESCE(observaciones, ''), COALESCE(ruta_excel, '')
        FROM cuadros
        WHERE id = %s
    """, (cuadro_id,))

    cuadro = cur.fetchone()

    cur.close()
    conn.close()

    if not cuadro:
        return RedirectResponse(url="/admin/cuadros", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="editar_cuadro.html",
        context={
            "request": request,
            "cuadro": cuadro,
            "torneos": torneos
        }
    )

@app.post("/admin/cuadros/editar/{cuadro_id}")
def actualizar_cuadro(
    cuadro_id: int,
    torneo_id: int = Form(...),
    nombre: str = Form(...),
    tamano: int = Form(...),
    numero_jugadores: int = Form(...),
    observaciones: str = Form(""),
    ruta_excel: str = Form(""),
    admin: str = Depends(comprobar_admin)
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE cuadros
        SET torneo_id = %s,
            nombre = %s,
            tamano = %s,
            numero_jugadores = %s,
            observaciones = %s,
            ruta_excel = %s
        WHERE id = %s
    """, (torneo_id, nombre, tamano, numero_jugadores, observaciones, ruta_excel, cuadro_id))

    conn.commit()
    cur.close()
    conn.close()

    return RedirectResponse(url="/admin/cuadros", status_code=303)

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