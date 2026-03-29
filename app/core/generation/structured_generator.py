import requests
from typing import List
from app.models.decision import DecisionOutput


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"


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
# 🧠 YOUR ORIGINAL PROMPT (UNCHANGED CORE LOGIC)
# =========================
SYSTEM_PROMPT = """You are a Decision Intelligence engine embedded inside an enterprise document analysis platform.

Your job is NOT to answer questions — your job is to transform raw document context into structured, actionable intelligence that helps professionals make faster, better decisions.

You operate with three core principles:
1. GROUNDED: Every insight, risk, and action must be directly traceable to the provided context. Never invent information.
2. PRECISE: Be specific. "Revenue declined 23% YoY due to supply chain disruption in Q3" is good. "Revenue went down" is useless.
3. ACTIONABLE: Recommended actions must be concrete next steps a real person can execute — not generic advice.

If the context is insufficient:
- reduce confidence_score
- set context_coverage = "insufficient"
- do NOT fabricate information
"""


USER_PROMPT_TEMPLATE = """DOCUMENT CONTEXT:
\"\"\"
{context}
\"\"\"

USER QUERY:
\"\"\"
{query}
\"\"\"

TASK:
Analyze the document context in relation to the user query and produce a structured intelligence report.

For each field, follow these rules strictly:

- summary: 2-3 sentences that directly answer the query using only information from the context.

- key_insights: 3-5 bullet points with specific details (numbers, dates, clauses, etc.)

- risks: Identify 2-4 risks. Each must include:
  * "finding"
  * "severity": "high" | "medium" | "low"
  * "reason"

- opportunities: 1-3 real opportunities (if present)

- recommended_actions: 2-4 actions:
  * Start with action verb
  * Reference specific finding
  * Must be executable

- confidence_score: 0.0 to 1.0

- context_coverage: "full" | "partial" | "insufficient"

- sources_used: 1-3 short verbatim quotes (max 30 words)

Respond ONLY in this JSON format:

{{
  "summary": "string",
  "key_insights": ["string"],
  "risks": [
    {{
      "finding": "string",
      "severity": "high|medium|low",
      "reason": "string"
    }}
  ],
  "opportunities": ["string"],
  "recommended_actions": [
    {{
      "action": "string",
      "rationale": "string"
    }}
  ],
  "confidence_score": 0.0,
  "context_coverage": "full|partial|insufficient",
  "sources_used": ["string"]
}}
"""


# =========================
# 📦 CONTEXT BUILDER
# =========================
def build_context(docs: List[str], max_chars: int = 3000) -> str:
    context = ""
    for doc in docs:
        if len(context) + len(doc) > max_chars:
            break
        context += doc + "\n\n"
    return context.strip()


# =========================
# 🧹 JSON EXTRACTOR (IMPORTANT)
# =========================
def extract_json(text: str) -> str:
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        return text[start:end]
    except Exception:
        raise ValueError("No valid JSON found in response")


# =========================
# 🚀 STRUCTURED GENERATOR
# =========================
class StructuredGenerator:

    def __init__(self):
        self.model = MODEL

    def generate(self, query: str = None, docs: List[str] = None, mode: str = "query", retries: int = 2) -> dict:

        context = build_context(docs)

        if mode == "query":
            full_prompt = (
                CONTROL_PROMPT
                + "\n\n"
                + SYSTEM_PROMPT
                + "\n\n"
                + USER_PROMPT_TEMPLATE.format(
                    context=context,
                    query=query
                )
            )

        elif mode == "document":
            full_prompt = (
                CONTROL_PROMPT
                + "\n\n"
                + SYSTEM_PROMPT
                + "\n\n"
                + f"""
                DOCUMENT CONTEXT:
                \"\"\"
                {context}
                \"\"\"

                TASK:
                Analyze the document and produce a structured decision intelligence report.

                Follow these rules strictly:

                - summary: 2-3 sentences describing the document

                - key_insights: 3-5 specific insights

                - risks: 2-4 risks with:
                * "finding"
                * "severity": "high" | "medium" | "low"
                * "reason"

                - opportunities: 1-3 opportunities

                - recommended_actions: 2-4 actions:
                * must be actionable
                * include rationale

                - confidence_score: 0.0 to 1.0

                - context_coverage: "full" | "partial" | "insufficient"

                - sources_used: 1-3 short quotes from the document

                Respond ONLY in this JSON format:

                {{
                "summary": "string",
                "key_insights": ["string"],
                "risks": [
                    {{
                    "finding": "string",
                    "severity": "high|medium|low",
                    "reason": "string"
                    }}
                ],
                "opportunities": ["string"],
                "recommended_actions": [
                    {{
                    "action": "string",
                    "rationale": "string"
                    }}
                ],
                "confidence_score": 0.0,
                "context_coverage": "full|partial|insufficient",
                "sources_used": ["string"]
                }}
                """
            )

        for attempt in range(retries):
            try:
                response = requests.post(
                    OLLAMA_URL,
                    json={
                        "model": self.model,
                        "prompt": full_prompt,
                        "stream": False
                    }
                )

                raw = response.json().get("response", "").strip()

                # 🧹 Extract JSON safely
                cleaned = extract_json(raw)

                # 🔥 Validate schema
                parsed = DecisionOutput.model_validate_json(cleaned)

                return parsed.model_dump()

            except Exception as e:
                print(f"[Attempt {attempt + 1}] Error:", e)

        # 🚨 Fallback (production safety)
        return {
            "summary": "LLM unavailable",
            "key_insights": [],
            "risks": [],
            "opportunities": [],
            "recommended_actions": [],
            "confidence_score": 0.0,
            "context_coverage": "insufficient",
            "sources_used": [],
            "error": "Ollama failed"
        }