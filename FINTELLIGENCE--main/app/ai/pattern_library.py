import json
from app.ai.groq_client import call_groq
from app.models.detection_result import DetectionResult
from app.detectors.evidence_confidence import calculate_evidence_confidence

def identify_patterns(case_id: str) -> list:
    # Get all detection results
    results = DetectionResult.query.filter_by(case_id=case_id, triggered=True).all()
    
    # Also fetch the M3 new detectors which might not be stored in DB if run on the fly, 
    # but the architecture usually saves them to DetectionResult.
    # To be safe and capture M3 detectors dynamically if they aren't saved yet:
    evidence = calculate_evidence_confidence(case_id)
    raw_m3 = evidence.get('raw_results', {})
    
    patterns = []
    
    # Merge DB results and on-the-fly M3 results
    triggered_detectors = set([r.detector_name for r in results])
    for k, v in raw_m3.items():
        if v and any(d.get('triggered') for d in v):
            triggered_detectors.add(k)
            
    if not triggered_detectors:
        return []

    # Map detectors to broader pattern categories
    detected_patterns = []
    if "LayeringChain" in triggered_detectors or "LayeringSeverity" in triggered_detectors:
        detected_patterns.append("LAYERING")
    if "CircularFlow" in triggered_detectors:
        detected_patterns.append("CIRCULAR_FLOW")
    if "Structuring" in triggered_detectors:
        detected_patterns.append("STRUCTURING")
    if "DormantRevival" in triggered_detectors:
        detected_patterns.append("DORMANT_REVIVAL")
    if "BeneficiaryBurst" in triggered_detectors:
        detected_patterns.append("BENEFICIARY_BURST")
    if "LargeTransaction" in triggered_detectors:
        detected_patterns.append("VELOCITY_ABUSE") # simplified mapping

    for pattern_name in detected_patterns:
        # Ask Groq to describe the pattern and recommend actions
        system_prompt = (
            "You are a forensic analyst. Describe the given financial crime pattern concisely, "
            "and provide a single recommended investigation action. Respond in JSON: "
            "{'description': 'string', 'recommended_action': 'string'}"
        )
        
        user_prompt = f"Pattern: {pattern_name}. Describe it in the context of Indian AML, and recommend an action."
        
        response_text = call_groq(system_prompt, user_prompt, max_tokens=500)
        
        desc = "Suspicious money movement pattern."
        action = "Investigate source and destination of funds."
        
        try:
            clean_json = response_text.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)
            desc = data.get('description', desc)
            action = data.get('recommended_action', action)
        except Exception:
            if "[MOCK RESPONSE]" in response_text:
                desc = f"[MOCK] Description for {pattern_name}."
                action = f"[MOCK] Recommended action for {pattern_name}."
        
        patterns.append({
            "pattern_name": pattern_name,
            "confidence_score": 85, # Simplification: you could use sentence transformers against a known definition DB
            "description": desc,
            "recommended_investigation_action": action
        })

    return patterns
