"""Script de inicialização da API do Instagram."""

import os
import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    reload_enabled = os.getenv("UVICORN_RELOAD", "false").lower() == "true"
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=port,
        reload=reload_enabled,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
