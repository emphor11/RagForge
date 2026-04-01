from pydantic import BaseModel
from typing import List


class ClauseIndexEntry(BaseModel):
    title: str
    type: str
    chunk_id: int
    page_number: int


class ContractProfile(BaseModel):
    document_id: str
    document_type: str
    classification_confidence: float
    parties: List[str]
    effective_date: str = ""
    governing_law: str = ""
    term_length: str = ""
    renewal_mechanics: str = ""
    payment_structure: str = ""
    clause_index: List[ClauseIndexEntry]
