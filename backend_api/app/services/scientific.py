from __future__ import annotations

from fastapi import Request
from sqlalchemy.exc import IntegrityError

from app.audit import mutation_connection, record_event
from app.db import get_primary_engine
from app.repositories.scientific import ScientificRepository
from app.security import Principal


class ScientificError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


PARENT = {
    "case": ("subject", "subject_id"),
    "sample": ("case", "case_id"),
    "slide": ("sample", "sample_id"),
    "image": ("slide", "slide_id"),
}
EVENT_NOUN = {
    "subject": "subject", "case": "case", "sample": "sample",
    "slide": "slide", "image": "image",
}
TRANSITIONS = {
    "subject": {"active": {"active"}},
    "case": {"draft": {"draft", "registered"}, "registered": {"registered", "ready"}, "ready": {"ready", "registered"}},
    "sample": {"registered": {"registered", "received"}, "received": {"received", "prepared"}, "prepared": {"prepared"}},
    "slide": {"registered": {"registered", "prepared"}, "prepared": {"prepared", "ready_for_capture"}, "ready_for_capture": {"ready_for_capture", "prepared"}},
    "image": {
        "registered": {"registered", "available", "unavailable", "rejected"},
        "available": {"available", "unavailable", "rejected"},
        "unavailable": {"unavailable", "available", "rejected"},
        "rejected": {"rejected"},
    },
}


def _actor_id(principal: Principal) -> str:
    if principal.insecure_local:
        raise ScientificError(403, "Las mutaciones científicas requieren un usuario persistido.")
    return principal.user_id


def _audit_state(kind: str, row: dict) -> dict:
    code_key = {
        "subject": "subject_code", "case": "case_code", "sample": "sample_code",
        "slide": "slide_code", "image": "image_code",
    }[kind]
    state = {"id": str(row["id"]), code_key: row[code_key], "status": row["status"]}
    for key in ("subject_id", "case_id", "sample_id", "slide_id"):
        if row.get(key):
            state[key] = str(row[key])
    return state


class ScientificService:
    def create(
        self, kind: str, values: dict, principal: Principal, request: Request,
        *, parent_id: str | None = None,
    ) -> dict:
        actor = _actor_id(principal)
        with mutation_connection(get_primary_engine()) as connection:
            repository = ScientificRepository(connection)
            if kind in PARENT:
                parent_kind, parent_column = PARENT[kind]
                effective_parent = parent_id or values.get(parent_column)
                if kind == "case" and effective_parent is None:
                    parent = None
                else:
                    parent = repository.get(parent_kind, str(effective_parent), for_update=True) if effective_parent else None
                if kind != "case" and not parent:
                    raise ScientificError(404, "Recurso padre no encontrado.")
                if effective_parent is not None and not parent:
                    raise ScientificError(404, "Recurso padre no encontrado.")
                if parent and parent["status"] == "archived":
                    raise ScientificError(409, "No se puede agregar contenido a un recurso archivado.")
                if effective_parent is not None:
                    values[parent_column] = effective_parent
            try:
                row = repository.create(kind, values, actor)
            except IntegrityError as exc:
                raise ScientificError(409, "Código, checksum o relación duplicada/inválida.") from exc
            action = "registered" if kind == "image" else "created"
            record_event(
                event_type=f"SCIENTIFIC_{kind.upper()}_{action.upper()}",
                action=f"scientific.{EVENT_NOUN[kind]}.{action}",
                principal=principal, request=request, success=True,
                after_state=_audit_state(kind, row), connection=connection,
                resource_type=f"scientific_{kind}", resource_id=str(row["id"]),
            )
            return row

    def get(self, kind: str, entity_id: str) -> dict:
        with get_primary_engine().connect() as connection:
            row = ScientificRepository(connection).get(kind, entity_id)
        if not row:
            raise ScientificError(404, "Recurso científico no encontrado.")
        return row

    def list(self, kind: str, **filters) -> dict:
        with get_primary_engine().connect() as connection:
            return ScientificRepository(connection).list(kind, **filters)

    def update(
        self, kind: str, entity_id: str, values: dict, principal: Principal, request: Request,
    ) -> dict:
        actor = _actor_id(principal)
        with mutation_connection(get_primary_engine()) as connection:
            repository = ScientificRepository(connection)
            before = repository.get(kind, entity_id, for_update=True)
            if not before:
                raise ScientificError(404, "Recurso científico no encontrado.")
            if before["status"] == "archived":
                raise ScientificError(409, "Un recurso archivado es inmutable.")
            next_status = values.get("status")
            if next_status and next_status not in TRANSITIONS[kind][before["status"]]:
                raise ScientificError(409, "Transición de estado inválida.")
            if kind == "case" and values.get("subject_id"):
                subject = repository.get("subject", str(values["subject_id"]))
                if not subject or subject["status"] == "archived":
                    raise ScientificError(409, "Sujeto inexistente o archivado.")
            try:
                after = repository.update(kind, entity_id, values, actor)
            except IntegrityError as exc:
                raise ScientificError(409, "Actualización rechazada por integridad.") from exc
            record_event(
                event_type=f"SCIENTIFIC_{kind.upper()}_UPDATED",
                action=f"scientific.{EVENT_NOUN[kind]}.updated",
                principal=principal, request=request, success=True,
                before_state=_audit_state(kind, before), after_state=_audit_state(kind, after),
                connection=connection, resource_type=f"scientific_{kind}", resource_id=entity_id,
            )
            return after

    def archive(
        self, kind: str, entity_id: str, principal: Principal, request: Request, reason: str | None,
    ) -> dict:
        actor = _actor_id(principal)
        with mutation_connection(get_primary_engine()) as connection:
            repository = ScientificRepository(connection)
            before = repository.get(kind, entity_id, for_update=True)
            if not before:
                raise ScientificError(404, "Recurso científico no encontrado.")
            if before["status"] == "archived":
                raise ScientificError(409, "El recurso ya está archivado.")
            if kind != "image" and repository.active_child_count(kind, entity_id):
                raise ScientificError(409, "Existen dependencias activas; no se aplicó archivado.")
            after = repository.archive(kind, entity_id, actor)
            record_event(
                event_type=f"SCIENTIFIC_{kind.upper()}_ARCHIVED",
                action=f"scientific.{EVENT_NOUN[kind]}.archived",
                principal=principal, request=request, success=True,
                metadata={"reason": reason} if reason else {},
                before_state=_audit_state(kind, before), after_state=_audit_state(kind, after),
                connection=connection, resource_type=f"scientific_{kind}", resource_id=entity_id,
            )
            return after

    def traceability(self, case_id: str) -> dict:
        with get_primary_engine().connect() as connection:
            rows = ScientificRepository(connection).traceability(case_id)
        if not rows:
            raise ScientificError(404, "Caso científico no encontrado.")
        first = rows[0]
        result = {
            "case": {"id": str(first["case_id"]), "case_code": first["case_code"], "status": first["case_status"]},
            "subject": (
                {"id": str(first["subject_id"]), "subject_code": first["subject_code"], "status": first["subject_status"]}
                if first["subject_id"] else None
            ),
            "samples": [],
        }
        samples: dict[str, dict] = {}
        slides: dict[str, dict] = {}
        for row in rows:
            if not row["sample_id"]:
                continue
            sample_key = str(row["sample_id"])
            sample = samples.setdefault(sample_key, {
                "id": sample_key, "sample_code": row["sample_code"],
                "status": row["sample_status"], "slides": [],
            })
            if not row["slide_id"]:
                continue
            slide_key = str(row["slide_id"])
            slide = slides.setdefault(slide_key, {
                "id": slide_key, "slide_code": row["slide_code"], "smear_type": row["smear_type"],
                "status": row["slide_status"], "images": [],
            })
            if slide not in sample["slides"]:
                sample["slides"].append(slide)
            if row["image_id"]:
                slide["images"].append({
                    "id": str(row["image_id"]), "image_code": row["image_code"],
                    "status": row["image_status"], "sha256": row["sha256"],
                    "width_px": row["width_px"], "height_px": row["height_px"],
                    "mime_type": row["mime_type"],
                })
        result["samples"] = list(samples.values())
        return result
