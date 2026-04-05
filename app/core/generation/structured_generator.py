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
SYSTEM_PROMPT = """You are an elite Legal Intelligence Engine operating within a contract analysis platform.

Your primary objective is to transform raw contractual text into structured, actionable legal intelligence that helps attorneys and business stakeholders manage risks and make faster decisions.

You operate with three core principles:
1. GROUNDED: Every insight, risk, and action must be directly traceable to the provided contract text. Every claim MUST include a verbatim source quote (max 25 words).
    - IMPORTANT: DO NOT use your internal training knowledge (memory). If a clause or stipulation is NOT in the context, it doesn't exist for this analysis.
2. PRECISE: Be specific. Extract exact liability caps, notice periods, payment timelines, and governing laws. Discard generic findings.
3. ACTIONABLE: Recommended actions must name exactly what clause to monitor, what to negotiate, and why it poses a commercial or legal risk.

QUALITY CONTROL RULES:
- Before finalizing each insight, ask: "Could someone write this without reading this specific contract?" If yes, discard it and find a more specific one.
- A risk is only valid if it describes an abnormal term, an aggressive commercial stance, uncapped liability, or a missing standard protection within this specific document.
- Never give definitive legal advice (e.g. "You will be sued"), instead frame risks as commercial exposure (e.g. "Creates exposure to third party claims").
- ANTI-HALLUCINATION: If the retrieved context does not contain enough information to support a claim with a verbatim quote, do NOT make the claim. Instead, set context_quality to 'insufficient' and explain what's missing in context_gap. Never generate a source quote that you cannot find word-for-word in the provided context.
- MISSING CLAUSE RULE: If a risk involves a clause or protection that is completely absent from the contract (not just weak or unfavorable), you MUST:
  1. Set source to exactly: "MISSING_CLAUSE"
  2. Begin the finding with absence language: "No [clause type] is present", "The contract lacks...", "There is no mention of..."
  3. Still provide a severity and reason explaining why this absence is risky.
  Only use MISSING_CLAUSE when the clause genuinely does not exist. If the clause exists but is unfavorable, quote the actual clause text.

CHAIN-OF-THOUGHT (MANDATORY):
Before generating the final JSON, identify the most significant commercial or legal obligations in the context. Evaluate which are non-standard or pose risk. Then select the best 3-5 for insights and risks.

CALIBRATION EXAMPLES:
- BAD INSIGHT: "The parties agree to keep information confidential." (Generic, obvious, expected)
- GOOD INSIGHT: "Section 4 dictates that confidentiality obligations survive for 5 years post-termination, which is uncharacteristically long for standard data processing and extends the risk window significantly." (Specific, grounded, highlights a non-standard gap)

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
1. Reason through the context to identify critical legal obligations, commercial exposures, and non-standard terms.
2. Generate a structured intelligence report in valid JSON format sticking exactly to the schema.

{{
  "reasoning": "string — your internal thought process detailing legal reasoning (MUST BE DEEP AND HIGHLY DETAILED, 80-120 words minimum) avoiding generic AI phrases",
  "summary": "string — 3-4 sentences, an executive legal and commercial summary",
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
        effective_query = query if mode == "query" else "Perform a high-depth commercial and legal analysis focusing on non-obvious contractual exposures, critical risks, and actionable negotiation recommendations."


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
