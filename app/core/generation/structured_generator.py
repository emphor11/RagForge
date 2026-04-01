from typing import List
from groq import Groq
from app.models.decision import DecisionOutput
from config.settings import settings

# =========================
# 🔒 CONTROL LAYER (STRICT)
# =========================
CONTROL_PROMPT = """CRITICAL INSTRUCTIONS:
- You MUST return ONLY valid JSON
- DO NOT include explanations, markdown, or extra text
- DO NOT wrap JSON in backticks
- Output must start with { and end with }
- Any deviation is failure
"""

# =========================
# 🧠 HIGH-FIDELITY PROMPT ENGINE
# =========================
SYSTEM_PROMPT = """You are a Decision Intelligence engine embedded inside an enterprise document analysis platform.

Your job is NOT to answer questions — your job is to transform raw document context into structured, actionable intelligence that helps professionals make faster, better decisions.

You operate with three core principles:
1. GROUNDED: Every insight, risk, and action must be directly traceable to the provided context. Every claim MUST include a verbatim source quote (max 25 words).
    - IMPORTANT: DO NOT use your internal training knowledge (memory). If a fact is NOT in the context, it doesn't exist for this analysis.
2. PRECISE: Be specific. If a number, date, formula, or section is mentioned, use it. Discard generic findings.
3. ACTIONABLE: Recommended actions must name exactly what to do, where in the document to find it, and why it matters.

QUALITY CONTROL RULES:
- Before finalizing each insight, ask: "Could someone write this without reading the document?" If yes, discard it and find a more specific one.
- A risk is only valid if it describes something that could go wrong or a conflict/gap within this specific document.
- If the document asks for a plan, provide a detailed numbered plan. If it asks for an explanation, provide depth.

CHAIN-OF-THOUGHT (MANDATORY):
Before generating the final JSON, identify the 10 most specific findings in the context. Evaluate which are non-obvious. Then select the best 3-5 for insights and risks.

CALIBRATION EXAMPLES:
- BAD INSIGHT: "Linear perceptrons are limited in what they can learn." (Generic, too broad)
- GOOD INSIGHT: "Section 2.3 introduces the XOR problem as proof that single-layer perceptrons cannot learn non-linear decision boundaries — this is the exact motivation for multilayer networks, though the document notes the mathematical proof is omitted." (Specific, grounded, non-obvious)

You always respond in valid JSON. Never add prose outside the JSON block."""

USER_PROMPT_TEMPLATE = """DOCUMENT CONTEXT:
\"\"\"
{context}
\"\"\"

USER QUERY:
\"\"\"
{query}
\"\"\"

TASK:
1. Reason through the context to find specific, non-obvious details.
2. Generate a structured intelligence report in valid JSON format sticking exactly to the schema.

{{
  "reasoning": "string — your internal thought process",
  "summary": "string — 3-4 sentences, specific to the query and document",
  "key_insights": [
    {{
      "insight": "string",
      "source": "verbatim quote from context",
      "confidence": 0.0-1.0
    }}
  ],
  "risks": [
    {{
      "finding": "string",
      "severity": "high|medium|low",
      "reason": "string",
      "source": "verbatim quote",
      "confidence": 0.0-1.0
    }}
  ],
  "opportunities": [
    {{
      "finding": "string",
      "source": "verbatim quote",
      "confidence": 0.0-1.0
    }}
  ],
  "recommended_actions": [
    {{
      "action": "string",
      "rationale": "string",
      "source": "verbatim quote",
      "confidence": 0.0-1.0
    }}
  ],
  "overall_confidence": 0.0-1.0,
  "context_quality": "full|partial|insufficient",
  "context_gap": "string — what is missing if quality is not full"
}}
"""


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

    def generate(self, query: str = None, docs: List[str] = None, mode: str = "query", retries: int = 3) -> dict:
        if not self.api_key:
            raise ValueError("Missing GROQ_API_KEY. Set it in the environment before generating insights.")

        context = build_context(docs)
        
        # In 'document' mode, use a broad intelligence extraction query
        effective_query = query if mode == "query" else "Perform a high-depth analysis focusing on non-obvious technical findings, specific risks, and document-grounded recommended actions."

        full_prompt = (
            CONTROL_PROMPT
            + "\n\n"
            + SYSTEM_PROMPT
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
