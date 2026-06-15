from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

load_dotenv()

from app.routers import cuadros, home, importaciones, jugadores, partidos, sets, torneos

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/Static"), name="static")

app.include_router(home.router)
app.include_router(jugadores.router)
app.include_router(importaciones.router)
app.include_router(torneos.router)
app.include_router(cuadros.router)
app.include_router(partidos.router)
app.include_router(sets.router)
