from pydantic import BaseModel


class LogoutSchema(BaseModel):
    token: str | None = None
    flag: str | None = "default"
    origin: int | None = 0
    data: str | None = None
