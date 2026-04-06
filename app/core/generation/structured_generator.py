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

    def generate(self, query: Optional[str] = None, docs: Optional[List[str]] = None, mode: str = "query", retries: int = 3) -> dict:
        if not self.api_key:
            raise ValueError("Missing GROQ_API_KEY. Set it in the environment before generating insights.")

        if docs is None:
            docs = []

        context = build_context(docs)
        
        # In 'document' mode, use a broad intelligence extraction query
        effective_query = query if mode == "query" else "Perform a high-depth commercial and legal analysis focusing on non-obvious contractual exposures, critical risks, and actionable negotiation recommendations."

        from app.core.generation.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

        full_prompt = (
            SYSTEM_PROMPT
            + "\n\n"
            + USER_PROMPT_TEMPLATE.format(
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
                
                # Parse and validate with Pydantic
                parsed = DecisionOutput.model_validate_json(cleaned)
                return parsed.model_dump()

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
