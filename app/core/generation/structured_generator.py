import json
from typing import List, Optional
from groq import Groq
from app.models.decision import DecisionOutput
from config.settings import settings


# =========================
# 📦 CONTEXT BUILDER
# =========================
def build_context(docs: List[str], max_chars: int = 15000) -> str:
    content = ""
    for doc in docs:
        if len(content) + len(doc) > max_chars:
            break
        content += doc + "\n\n"
    return content.strip()


# =========================
# 🧹 JSON EXTRACTOR
# =========================
def extract_json(text: str) -> str:
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        return text[start:end]
    except Exception:
        raise ValueError(f"No valid JSON found in LLM response: {text[:500]}...")


# =========================
# 🚀 STRUCTURED GENERATOR
# =========================
class StructuredGenerator:
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.standard_clauses = self._load_standard_clauses()
        self.checklists = self._load_checklists()

    def _load_standard_clauses(self) -> dict:
        import os
        path = "app/resources/standard_clauses.json"
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
        return {}

    def _load_checklists(self) -> dict:
        import os
        path = "app/resources/checklists.json"
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
        return {}

    def _post_process_mitigation(self, data: dict) -> dict:
        """
        Injects vetted legal templates into findings based on keywords.
        """
        if not self.standard_clauses:
            return data

        # Keywords mapping for mitigation suggestion
        mapping = {
            "liability": "limitation_of_liability",
            "arbitration": "arbitration_india",
            "force majeure": "force_majeure",
            "governing law": "governing_law_india",
            "solicitation": "non_solicitation",
            "compete": "non_compete" # We can add more to standard_clauses.json later
        }

        # Process Risks
        for risk in data.get("risks", []):
            finding_text = risk.get("finding", "").lower()
            for kw, template_key in mapping.items():
                if kw in finding_text:
                    risk["mitigation_fix"] = self.standard_clauses.get(template_key)
                    break

        # Process Recommended Actions
        for action in data.get("recommended_actions", []):
            action_text = action.get("action", "").lower()
            for kw, template_key in mapping.items():
                if kw in action_text:
                    action["mitigation_fix"] = self.standard_clauses.get(template_key)
                    break

        return data

    def generate(self, query: Optional[str] = None, docs: Optional[List[str]] = None, mode: str = "query", document_type: Optional[str] = None, retries: int = 3) -> dict:
        if not self.api_key:
            raise ValueError("Missing GROQ_API_KEY. Set it in the environment before generating insights.")

        if docs is None:
            docs = []

        context = build_context(docs)
        
        # In 'document' mode, use a broad intelligence extraction query
        effective_query = query if mode == "query" else "Perform a high-depth commercial and legal analysis focusing on non-obvious contractual exposures, critical risks, and actionable negotiation recommendations."

        from app.core.generation.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE, CHAT_PROMPT_TEMPLATE

        # Prepare document-type specific instructions
        type_instruction = ""
        if mode == "document" and document_type:
            checklist = self.checklists.get(document_type) or self.checklists.get("General") or []
            checklist_items = "\n".join([f"- {item}" for item in checklist])
            type_instruction = f"""
### {document_type} SPECIFIC GUIDELINES:
This document is classified as a {document_type}. 
Focus your analysis strictly on the following core requirements:
{checklist_items}

Note: If a global mandate (like Indian Data Protection) is NOT in the list above, do not mark the context as 'partial' or 'insufficient' just because it is missing. Only evaluate what is required for a {document_type}.
"""

        selected_user_template = CHAT_PROMPT_TEMPLATE if mode == "query" else USER_PROMPT_TEMPLATE

        full_prompt = (
            SYSTEM_PROMPT
            + "\n\n"
            + type_instruction
            + "\n\n"
            + selected_user_template.format(
                context=context,
                query=effective_query
            )
        )

        for attempt in range(retries):
            try:
                client = Groq(api_key=self.api_key)

                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "user", "content": full_prompt}
                    ],
                    temperature=0.1
                )

                raw = str(response.choices[0].message.content or "")
                cleaned = extract_json(raw)
                
                # Parse and validate with correct Pydantic model
                from app.models.decision import DecisionOutput, ChatResponse
                
                model = ChatResponse if mode == "query" else DecisionOutput
                parsed = model.model_validate_json(cleaned)
                output_dict = parsed.model_dump()
                
                # Phase 3: Inject Mitigation Suggestions
                return self._post_process_mitigation(output_dict)


            except Exception as e:
                print(f"[Attempt {attempt + 1}] Intelligence generation failed: {e}")

        # 🚨 Schema-compliant fallback
        return {
            "reasoning": "Fallback triggered. LLM failed to produce valid JSON after retries.",
            "summary": "The intelligence engine encountered an error while processing the document.",
            "key_insights": [],
            "risks": [],
            "opportunities": [],
            "recommended_actions": [],
            "overall_confidence": 0.0,
            "context_quality": "insufficient",
            "context_gap": "Generation failure occurred. Please try again or refine your query."
        }
