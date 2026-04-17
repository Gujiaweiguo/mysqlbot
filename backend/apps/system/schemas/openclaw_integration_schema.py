from pydantic import BaseModel


class OpenClawMcpConfigResponse(BaseModel):
    status: str
    service: str
    ready: bool
    setup_enabled: bool
    server_name: str
    bind_host: str
    port: int
    path: str
    base_url: str
    endpoint: str
    health_url: str
    auth_header: str
    auth_scheme: str
    operations: list[str]
    tool_names: list[str]
    issues: list[str]
