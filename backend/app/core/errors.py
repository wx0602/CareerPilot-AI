from fastapi import HTTPException, status


def api_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


def unauthorized(message: str = "登录状态无效或已过期") -> HTTPException:
    return api_error(status.HTTP_401_UNAUTHORIZED, "unauthorized", message)


def forbidden(message: str = "无权访问该资源") -> HTTPException:
    return api_error(status.HTTP_403_FORBIDDEN, "forbidden", message)


def not_found(resource: str) -> HTTPException:
    return api_error(status.HTTP_404_NOT_FOUND, "not_found", f"{resource}不存在")


def conflict(code: str, message: str) -> HTTPException:
    return api_error(status.HTTP_409_CONFLICT, code, message)
