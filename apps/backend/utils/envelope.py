from fastapi.responses import JSONResponse


def ok(data=None, meta=None):
    return JSONResponse(
        content={
            "ok": True,
            "data": data,
            "meta": meta or {},
        }
    )


def error(message: str, code: str = "error", status: int = 400):
    return JSONResponse(
        status_code=status,
        content={
            "ok": False,
            "error": code,
            "message": message,
        },
    )
