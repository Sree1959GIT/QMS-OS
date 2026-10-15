"""Original evidence (MVP-1 slice 5; R-50 to R-53): read-only routes. There is no upload route in this pull request
(objects are stored by ``python -m qms_os.evidence put`` and by tests), and no delete or overwrite route at all.
A malformed, unknown or not-readable hash gets the same 404; a stored object that no longer matches its hash is never
served."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from ..evidence import service as EV
from ..models import User
from .deps import current_user, get_session

router = APIRouter(prefix="/api/v1/evidence")


@router.get("/{sha256}")
def evidence(sha256: str, request: Request, u: User = Depends(current_user), s: Session = Depends(get_session)):
    if request.app.state.evidence_store is None:
        raise EV.NotFound(EV.NOT_FOUND)
    return EV.object_row(EV.readable_object(s, u, sha256))


@router.get("/{sha256}/content")
def evidence_content(sha256: str, request: Request, u: User = Depends(current_user),
                     s: Session = Depends(get_session)):
    row, data = EV.read_content(s, request.app.state.evidence_store, u, sha256)
    return Response(content=data, media_type=row.mime,
                    headers={"X-Content-Type-Options": "nosniff", "Content-Disposition": "attachment",
                             "Cache-Control": "no-store"})
