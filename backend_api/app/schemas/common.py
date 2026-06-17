from pydantic import BaseModel


class Datasource(BaseModel):
    key: str
    label: str
    domain: str
    enabled: bool
    database: str


class HealthResponse(BaseModel):
    status: str
    datasource: str
    database: str
    user: str

