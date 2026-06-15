from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core import comprobar_admin, templates
from app.database import get_connection

router = APIRouter()

@router.get("/admin/jugadores", response_class=HTMLResponse)
def jugadores(
    request: Request,
    buscar: str = "",
    ordenar: str = "apellido",
    genero_id: int = 0,
    ano_nacimiento: str = "",
    admin: str = Depends(comprobar_admin)
):
    texto_busqueda = f"%{buscar.strip()}%"

    if ordenar == "club":
        order_by = "club, apellido1, apellido2, nombre"
    elif ordenar == "licencia":
        order_by = "NULLIF(numero_licencia, '') NULLS LAST, apellido1, apellido2, nombre"
    elif ordenar == "genero_ano_apellido":
        order_by = "genero_id, ano_nacimiento, apellido1, apellido2, nombre"
    elif ordenar == "ano_genero_apellido":
        order_by = "ano_nacimiento, genero_id, apellido1, apellido2, nombre"
    elif ordenar == "club_genero_ano":
        order_by = "club, genero_id, ano_nacimiento, apellido1, apellido2, nombre"
    elif ordenar == "genero_club_apellido":
        order_by = "genero_id, club, apellido1, apellido2, nombre"
    else:
        order_by = "apellido1, apellido2, nombre"

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, nombre
        FROM generos
        ORDER BY id
    """)
    generos = cur.fetchall()

    condiciones = []
    parametros = []

    if buscar:
        texto_busqueda = f"%{buscar.strip()}%"
        condiciones.append("""
            (
                nombre ILIKE %s
                OR apellido1 ILIKE %s
                OR COALESCE(apellido2,'') ILIKE %s
                OR club ILIKE %s
                OR COALESCE(numero_licencia,'') ILIKE %s
            )
        """)
        parametros.extend([
            texto_busqueda,
            texto_busqueda,
            texto_busqueda,
            texto_busqueda,
            texto_busqueda
        ])

    if genero_id != 0:
        condiciones.append("genero_id = %s")
        parametros.append(genero_id)

    if ano_nacimiento.strip() != "":
        condiciones.append("ano_nacimiento = %s")
        parametros.append(int(ano_nacimiento))

    where_sql = ""

    if condiciones:
        where_sql = "WHERE " + " AND ".join(condiciones)

    cur.execute(f"""
        SELECT
            id,
            nombre,
            apellido1,
            apellido2,
            club,
            ano_nacimiento,
            numero_licencia,
            genero_id
        FROM jugadores
        {where_sql}
        ORDER BY {order_by}
    """, parametros)

    jugadores = cur.fetchall()

    return templates.TemplateResponse(
        request=request,
        name="jugadores.html",
        context={
            "request": request,
            "jugadores": jugadores,
            "buscar": buscar,
            "ordenar": ordenar,
            "generos": generos,
            "genero_id": genero_id,
            "ano_nacimiento": ano_nacimiento
        }
    )

@router.post("/admin/jugadores")
def guardar_jugador(
    nombre: str = Form(...),
    apellido1: str = Form(...),
    apellido2: str = Form(""),
    club: str = Form(""),
    ano_nacimiento: int = Form(...),
    numero_licencia: str = Form(""),
    genero_id: int = Form(...),
    admin: str = Depends(comprobar_admin)
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO jugadores (nombre, apellido1, apellido2, club, ano_nacimiento, numero_licencia, genero_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (nombre, apellido1, apellido2, club, ano_nacimiento, numero_licencia, genero_id))

    conn.commit()

    cur.close()
    conn.close()

    return RedirectResponse(url="/admin/jugadores", status_code=303)

@router.get("/admin/jugadores/editar/{jugador_id}", response_class=HTMLResponse)
def editar_jugador_form(request: Request, jugador_id: int,
admin: str = Depends(comprobar_admin) 
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, nombre, apellido1, apellido2, club, ano_nacimiento, numero_licencia, genero_id
        FROM jugadores
        WHERE id = %s
    """, (jugador_id,))
    jugador = cur.fetchone()

    cur.execute("""
        SELECT id, nombre
        FROM generos
        ORDER BY id
    """)
    generos = cur.fetchall()

    cur.close()
    conn.close()

    if not jugador:
        return RedirectResponse(url="/admin/jugadores", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="editar_jugador.html",
        context={
            "request": request,
            "jugador": jugador,
            "generos": generos
        }
    )


@router.post("/admin/jugadores/editar/{jugador_id}")
def actualizar_jugador(
    jugador_id: int,
    nombre: str = Form(...),
    apellido1: str = Form(...),
    apellido2: str = Form(""),
    club: str = Form(""),
    ano_nacimiento: int = Form(...),
    numero_licencia: str = Form(""),
    genero_id: int = Form(...),
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
            numero_licencia = %s,
            genero_id = %s
            
        WHERE id = %s
    """, (nombre, apellido1, apellido2, club, ano_nacimiento, numero_licencia, genero_id, jugador_id))

    conn.commit()
    cur.close()
    conn.close()

    return RedirectResponse(url="/admin/jugadores", status_code=303)


@router.post("/admin/jugadores/borrar/{jugador_id}")
def borrar_jugador(jugador_id: int,
      admin: str = Depends(comprobar_admin)            
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*)
        FROM partidos
        WHERE jugador1_id = %s
           OR jugador2_id = %s
           OR ganador_id = %s
    """, (jugador_id, jugador_id, jugador_id))
    partidos_relacionados = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM cuadro_inscritos
        WHERE jugador_id = %s
    """, (jugador_id,))
    inscritos_relacionados = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM rondas_cuadro
        WHERE jugador1_id = %s
           OR jugador2_id = %s
           OR ganador_id = %s
    """, (jugador_id, jugador_id, jugador_id))
    rondas_relacionadas = cur.fetchone()[0]

    if partidos_relacionados or inscritos_relacionados or rondas_relacionadas:
        cur.close()
        conn.close()
        return RedirectResponse(url="/admin/jugadores", status_code=303)

    cur.execute("DELETE FROM jugadores WHERE id = %s", (jugador_id,))

    conn.commit()
    cur.close()
    conn.close()

    return RedirectResponse(url="/admin/jugadores", status_code=303)
