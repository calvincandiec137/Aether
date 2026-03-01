import json
from llm_client import call_llm
import config

def extract_factors(report_text):
    """
    Extract debatable factors from the input report.
    Returns a list of factor strings (limited by MAX_FACTORS config).
    """
    system_prompt = """You are a critical analyst. Your task is to break down reports into independent, debatable factors.

Rules:
- Each factor must be arguable from both sides
- Factors must be non-overlapping
- Prefer analytical dimensions over topics
- Examples: Feasibility, Scalability, Risk profile, Ethical implications, Market fit

CRITICAL: Return ONLY a valid JSON array of strings. NO explanations, NO markdown, NO extra text.
Format: ["Factor 1", "Factor 2"]"""

    # Truncate report if too long (prevent context window overflow)
    max_report_length = 4000  # Characters - safe for most models
    truncated_report = report_text
    if len(report_text) > max_report_length:
        truncated_report = report_text[:max_report_length] + "\n\n[Report truncated for factor extraction...]"
    
    prompt = f"""Analyze this report and extract exactly {config.MAX_FACTORS} debatable factors.

{truncated_report}

Output ONLY the JSON array, nothing else:"""

    response = call_llm(config.JUDGE_MODEL, prompt, system_prompt)
    
    # Parse JSON response - extract from markdown code blocks if needed
    try:
        # Try to find JSON array in response (may be wrapped in ```json``` or have explanatory text)
        response_clean = response.strip()
        
        # Remove markdown code blocks
        if "```json" in response_clean:
            response_clean = response_clean.split("```json")[1].split("```")[0]
        elif "```" in response_clean:
            response_clean = response_clean.split("```")[1].split("```")[0]
        
        # Find JSON array pattern
        import re
        json_match = re.search(r'\[[\s\S]*?\]', response_clean)
        if json_match:
            json_str = json_match.group(0)
            factors = json.loads(json_str)
            if isinstance(factors, list) and all(isinstance(f, str) for f in factors):
                return factors[:config.MAX_FACTORS]
        
        # Direct parse attempt
        factors = json.loads(response_clean.strip())
        if isinstance(factors, list) and all(isinstance(f, str) for f in factors):
            return factors[:config.MAX_FACTORS]
        else:
            raise ValueError("Invalid factor format")
    except Exception as e:
        # Fallback: try to extract quoted strings
        import re
        quotes = re.findall(r'"([^"]+)"', response)
        valid_factors = [q for q in quotes if len(q) > 10 and not q.startswith('Factor')]
        if valid_factors:
            return valid_factors[:config.MAX_FACTORS]
        
        # Last resort: split by lines and filter
        lines = [line.strip(' "-,[]') for line in response.strip().split('\n') if line.strip()]
        clean_lines = [line for line in lines if line and len(line) > 10 and not line.startswith('{') and not line.startswith('```')]
        return clean_lines[:config.MAX_FACTORS] if clean_lines else ["Default Factor 1", "Default Factor 2"]
