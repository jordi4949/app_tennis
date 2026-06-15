from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.core import comprobar_admin, templates

router = APIRouter()

@router.get("/admin", response_class=HTMLResponse)
def inicio(request: Request, admin: str = Depends(comprobar_admin)):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request}
    )
