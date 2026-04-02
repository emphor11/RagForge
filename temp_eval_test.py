from sentence_transformers import SentenceTransformer, util

# Load the exact same model
model = SentenceTransformer("all-MiniLM-L6-v2")

claim = "Changes in scope may impact cost and timeline."
source = "Changes in scope shall be documented via a Change Request and may impact cost and timeline."
context = """Deliver high-quality, bug-free code
Maintain communication and provide weekly updates
Fix critical bugs within agreed timelines...
Any changes in scope shall be documented via a Change Request and may impact cost and timeline....
The Client will provide timely approvals
No major scope changes during development
Third-party API costs (if any) will be borne by the Client..."""

# Scenario A: Claim vs Source (What it should realistically check)
emb_claim = model.encode(claim)
emb_source = model.encode(source)
sim_source = util.cos_sim(emb_claim, emb_source).item()

# Scenario B: Claim vs Window (What evaluator.py is actually doing)
emb_context = model.encode(context)
sim_context = util.cos_sim(emb_claim, emb_context).item()

print(f"Similarity (Claim vs Exact Source): {sim_source:.2f}")
print(f"Similarity (Claim vs Context Window): {sim_context:.2f}")
