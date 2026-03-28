from pydantic import BaseModel


class DocumentInput(BaseModel):
    text: str
    metadata: dict = {}