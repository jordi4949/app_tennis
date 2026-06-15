from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
import os
import secrets


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
