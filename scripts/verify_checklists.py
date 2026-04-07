import sys
import os
import json

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.generation.contract_analyzer import LLMContractAnalyzer

def verify():
    analyzer = LLMContractAnalyzer()
    
    # Load the existing NDA data
    json_path = "insights/Untitled document (2).pdf.json"
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found.")
        return

    with open(json_path, "r") as f:
        data = json.load(f)
    
    profile = data.get("contract_profile", {})
    clauses = data.get("clauses", [])
    
    print(f"--- Verifying spot_issues for Document Type: {profile.get('document_type')} ---")
    
    # Run spot_issues
    findings = analyzer.spot_issues(profile, clauses)
    
    print("\nFindings generated:")
    for i, f in enumerate(findings):
        print(f"{i+1}. [{f['finding_type'].upper()}] {f['title']} (Severity: {f['severity']})")
        # print(f"   Explanation: {f['explanation']}")

    # Verification: For an NDA, we expect NO "Warranty" or "Payment" missing protections
    unexpected_keywords = ["warranty", "payment", "milestone"]
    false_positives = [f for f in findings if any(kw in f['title'].lower() or kw in f['explanation'].lower() for kw in unexpected_keywords) and f['finding_type'] == 'missing_protection']
    
    if false_positives:
        print("\n❌ FAILED: Found false positive missing protections for an NDA:")
        for fp in false_positives:
            print(f"   - {fp['title']}")
    else:
        print("\n✅ PASSED: No false positive missing protections (Warranty/Payment) found for the NDA.")

if __name__ == "__main__":
    verify()
