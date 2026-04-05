import json
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from groq import Groq
from config.settings import settings

class ProfileExtractionModel(BaseModel):
    document_type: str = Field(description="The type of contract (e.g., MSA, SOW, NDA, Lease, etc.)")
    parties: List[str] = Field(description="All legal entities or individuals involved in the agreement.")
    effective_date: str = Field(default="", description="The start or effective date of the agreement.")
    governing_law: str = Field(default="", description="The governing law and/or jurisdiction (e.g., 'California', 'Laws of England').")
    term_length: str = Field(default="", description="The duration or term of the contract (e.g., '12 Months', '3 Years', '8 Weeks').")
    renewal_mechanics: str = Field(default="", description="How the contract renews (e.g., 'Automatic 1 year', 'Mutual written agreement').")
    payment_structure: str = Field(default="", description="Summary of fees or payment milestones (e.g., 'Milestone based', '$5,000 monthly', 'Not Disclosed').")
    classification_confidence: float = Field(description="Confidence score between 0.0 and 1.0 representing how certain you are of the document type and extraction.")

class ClauseExtractionModel(BaseModel):
    class Clause(BaseModel):
        title: str = Field(description="The section heading or implied title of the clause.")
        type: str = Field(description="A snake_case standardized category for this clause (e.g., 'termination', 'payment', 'confidentiality', 'liability_cap')")
        clause_text: str = Field(description="The full extracted text of the clause.")
        chunk_id: int
        page_number: int

    clauses: List[Clause]

class ReviewFindingModel(BaseModel):
    class Finding(BaseModel):
        finding_type: str = Field(description="Must be one of: 'risk', 'missing_protection', 'negotiation_point'.")
        clause_type: str = Field(description="The associated clause type (e.g., 'termination', 'payment', 'liability_cap').")
        severity: str = Field(description="'high', 'medium', or 'low'.")
        title: str = Field(description="A short, descriptive title of the finding.")
        explanation: str = Field(description="Detailed legal reasoning for why this is a risk or missing protection.")
        clause_refs: List[str] = Field(description="Titles of the clauses relevant to this finding.")
        source_quotes: List[str] = Field(description="Extracted sentences from the clauses that trigger this finding. If 'missing_protection', this can be blank.")
        confidence: float = Field(description="Confidence score representing certainty of this issue (0.0 to 1.0).")
    
    findings: List[Finding]

CONTROL_PROMPT = """CRITICAL INSTRUCTIONS:
- You MUST return ONLY valid JSON matching the exact provided schema.
- DO NOT include explanations, markdown, or extra text.
- DO NOT wrap JSON in backticks format like ```json.
- Any deviation is a failure.
"""

def extract_json(text: str) -> str:
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        return text[start:end]
    except Exception:
        raise ValueError(f"No valid JSON found in LLM response: {text[:500]}...")

class LLMContractAnalyzer:
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        if not self.api_key:
            raise ValueError("Missing GROQ_API_KEY.")

    def _call_llm(self, prompt: str, schema_model: type[BaseModel]) -> dict:
        client = Groq(api_key=self.api_key)
        
        system_prompt = f"{CONTROL_PROMPT}\n\nYou must strictly adhere to the following JSON schema:\n{schema_model.model_json_schema()}"
        
        for attempt in range(3):
            try:
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1
                )
                raw = str(response.choices[0].message.content or "")
                cleaned = extract_json(raw)
                
                # Validate and parse
                parsed = schema_model.model_validate_json(cleaned)
                return parsed.model_dump()
            except Exception as e:
                print(f"[LLMContractAnalyzer] Error on attempt {attempt+1}: {e}")
        
        # Fallback if extremely fails
        return {}

    def extract_profile(self, document_id: str, context: str) -> dict:
        prompt = f"""
Analyze the following document preamble and introductory text to extract the core contract profile metadata.
Find the legal entities (parties) involved, the document type, the effective date, any mention of term/duration, governing law, and payment terms. 
If a field is not present, use an empty string.

DOCUMENT TEXT:
{context}
"""
        result = self._call_llm(prompt, ProfileExtractionModel)
        if result:
            result['document_id'] = document_id
            result['clause_index'] = []  # Will be populated later 
        return result

    def extract_clauses(self, chunks: List[dict]) -> List[dict]:
        all_clauses = []
        batch_size = 20
        
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            chunk_text = ""
            for chunk in batch:
                chunk_id = chunk["metadata"]["chunk_id"]
                page = chunk["metadata"].get("page_number", 1)
                chunk_text += f"\n--- [Chunk {chunk_id} | Page {page}] ---\n{chunk['content']}\n"

            prompt = f"""
Identify ALL distinct legal sections and clauses within the provided text.
For each clause, determine its 'title' as it appears in the text, assign a standardized snake_case 'type', and carefully extract the relevant 'clause_text'.
Make sure to include the chunk_id and page_number corresponding to where you found the text. 

DOCUMENT CHUNKS:
{chunk_text}
"""
            result = self._call_llm(prompt, ClauseExtractionModel)
            batch_clauses = result.get("clauses", [])
            all_clauses.extend(batch_clauses)
            
        return all_clauses

    def spot_issues(self, profile: dict, clauses: List[dict]) -> List[dict]:
        # Serialize the context for the LLM
        profile_str = json.dumps(profile, indent=2)
        clauses_str = json.dumps([{"title": c["title"], "type": c["type"], "text": c["clause_text"][:300] + "..."} for c in clauses], indent=2)
        
        # Deterministic check for presence to prevent hallucinations
        # We explicitly tell the LLM which categories already exist.
        clause_types_present = set(c["type"].lower() for c in clauses)
        existing_hints = ", ".join(clause_types_present)

        prompt = f"""
You are an expert corporate lawyer conducting a contract review audit for an Indian-market commercial agreement.

### CRITICAL ADVISORY:
The following clause types were DETERMINISTICALLY FOUND in this document:
[{existing_hints}]

- IF A TYPE IS LISTED ABOVE, DO NOT FLAG IT AS 'missing_protection'.
- Analyze the text of these clauses for 'risk' or 'negotiation_point'.
- If a core protection (like 'liability_cap' or 'indemnification') is NOT listed above, flag as 'missing_protection'.

### LEGAL CHECKLIST (Benchmark: Standard Indian MSA/SOW):
1. **Liability**: Is there a 'liability_cap'? Is it uncapped? Is it mutual?
2. **Indemnity**: Is indemnification present? Does it cover IP infringement?
3. **Payments**: Are interest rates excessive (e.g. >18% annually)? Are there 15-day payment terms?
4. **IP Context**: Are there carve-outs for 'pre-existing rights' or 'background IP'?
5. **Force Majeure**: Is it defined? Does it include standard exclusions?
6. **Termination**: Is there a clear 'cure period' for breach (typically 30 days)?

Look for:
1. 'missing_protection' (Absent clauses).
2. 'risk' (Uncapped liability, high interest, non-mutual terms).
3. 'negotiation_point' (Notice periods, 1-year non-solicit (if above norm), restrictive clauses).

CONTRACT PROFILE:
{profile_str}

IDENTIFIED CLAUSES:
{clauses_str}
"""
        result = self._call_llm(prompt, ReviewFindingModel)
        raw_findings = result.get("findings", [])
        
        # Hydrate default metadata expected by UI
        for finding in raw_findings:
            finding["status"] = "open"
            finding["reviewer_note"] = ""
            
        return raw_findings
