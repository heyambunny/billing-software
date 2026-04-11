from fastapi import FastAPI
from backend.routes.dashboard import router as dashboard_router
from backend.routes.auth import router as auth_router
from backend.routes.projection import router as projection_router
app = FastAPI()

app.include_router(dashboard_router, prefix="/api")

app.include_router(auth_router, prefix="/api")

app.include_router(projection_router, prefix="/api")

from backend.routes.billing import router as billing_router
app.include_router(billing_router, prefix="/api")

from backend.routes.reports import router as reports_router
app.include_router(reports_router, prefix="/api")

from backend.routes.billed import router as billed_router
app.include_router(billed_router, prefix="/api")

from backend.routes.edit_projection import router as projection_router
app.include_router(projection_router, prefix="/api")

from backend.routes.finance import router as finance_router
app.include_router(finance_router, prefix="/api")

from backend.routes.audit import router as audit_router
app.include_router(audit_router, prefix="/api")

from backend.routes.client_access import router as client_access_router
app.include_router(client_access_router, prefix="/api")

from backend.routes.bulk_upload import router as bulk_router
app.include_router(bulk_router, prefix="/api")