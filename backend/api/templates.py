import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend.database import get_db
from backend.models import Setting
from backend.schemas import TemplateOut, TemplateCreate, TemplateUpdate
from backend.services.message_template import DEFAULT_TEMPLATES
from backend.auth import verify_bearer_token

router = APIRouter(prefix="/api/templates", tags=["Templates"])

TEMPLATES_SETTING_KEY = "custom_message_templates"

def _get_all_templates(db: Session) -> List[dict]:
    setting = db.query(Setting).filter(Setting.key == TEMPLATES_SETTING_KEY).first()
    if setting:
        try:
            return json.loads(setting.value)
        except Exception:
            pass
    return DEFAULT_TEMPLATES.copy()

def _save_templates(db: Session, templates: List[dict]):
    setting = db.query(Setting).filter(Setting.key == TEMPLATES_SETTING_KEY).first()
    json_val = json.dumps(templates)
    if setting:
        setting.value = json_val
    else:
        setting = Setting(key=TEMPLATES_SETTING_KEY, value=json_val)
        db.add(setting)
    db.commit()


@router.get("", response_model=List[TemplateOut])
def list_templates(db: Session = Depends(get_db)):
    return [TemplateOut(**t) for t in _get_all_templates(db)]


@router.post("", response_model=TemplateOut, dependencies=[Depends(verify_bearer_token)])
def create_template(payload: TemplateCreate, db: Session = Depends(get_db)):
    if not payload.name.strip() or not payload.content.strip():
        raise HTTPException(status_code=400, detail="Template name and content are required")

    templates = _get_all_templates(db)
    new_id = f"tpl_{len(templates) + 1}_{int(payload.name.__hash__() & 0xffff)}"
    new_template = {
        "id": new_id,
        "name": payload.name.strip(),
        "content": payload.content.strip()
    }
    templates.append(new_template)
    _save_templates(db, templates)
    return TemplateOut(**new_template)


@router.put("/{id}", response_model=TemplateOut, dependencies=[Depends(verify_bearer_token)])
def update_template(id: str, payload: TemplateUpdate, db: Session = Depends(get_db)):
    templates = _get_all_templates(db)
    found = None
    for t in templates:
        if t["id"] == id:
            found = t
            break

    if not found:
        raise HTTPException(status_code=404, detail="Template not found")

    if payload.name is not None and payload.name.strip():
        found["name"] = payload.name.strip()
    if payload.content is not None and payload.content.strip():
        found["content"] = payload.content.strip()

    _save_templates(db, templates)
    return TemplateOut(**found)


@router.delete("/{id}", dependencies=[Depends(verify_bearer_token)])
def delete_template(id: str, db: Session = Depends(get_db)):
    templates = _get_all_templates(db)
    filtered = [t for t in templates if t["id"] != id]
    if len(filtered) == len(templates):
        raise HTTPException(status_code=404, detail="Template not found")

    _save_templates(db, filtered)
    return {"message": f"Template {id} deleted"}
