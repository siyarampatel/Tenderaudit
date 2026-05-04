"""
modules/llm_engine.py
Handles all LLM interactions via Groq API (Llama 3.3).
"""

import json
import re
from groq import Groq


def get_groq_client(api_key: str) -> Groq:
    return Groq(api_key=api_key)


CRITERIA_EXTRACTION_PROMPT = """You are a government procurement analyst.

Extract eligibility criteria from this tender document.

RULES:
- Return ONLY a JSON array
- No explanation, no markdown, no code blocks
- Start your response with [ and end with ]
- Each item must have exactly these keys: criterion_name, type, required_value, unit, description
- type must be one of: Financial, Technical, Compliance

    Example of exact format to return:
    [{{"criterion_name":"Annual Turnover","type":"Financial","required_value":"500","unit":"Lakhs INR","description":"Minimum average annual turnover of Rs 500 Lakhs"}},{{"criterion_name":"Experience","type":"Technical","required_value":"5","unit":"Years","description":"Minimum 5 years experience"}}]

Tender text:
{tender_text}

Remember: Start with [ and end with ] only. No other text."""


BIDDER_EVALUATION_PROMPT = """You are a government procurement evaluation officer.

Evaluate this bidder against each criterion.

CRITERIA:
{criteria_json}

BIDDER NAME: {bidder_name}

BIDDER DOCUMENTS:
{bidder_text}

RULES:
- Return ONLY a JSON array
- No explanation, no markdown, no code blocks
- Start your response with [ and end with ]
- Each item must have exactly these keys: criterion_name, extracted_value, source_page, status, confidence, reasoning
- status must be one of: Pass, Fail, Needs Review
- confidence must be a number 0-100
- source_page must be a number

Example of exact format:
[{{"criterion_name":"Annual Turnover","extracted_value":"620 Lakhs","source_page":4,"status":"Pass","confidence":88,"reasoning":"Turnover of 620 Lakhs exceeds required 500 Lakhs"}}]

Remember: Start with [ and end with ] only. No other text."""


def extract_criteria_from_tender(client: Groq, tender_text: str) -> list:
    prompt = CRITERIA_EXTRACTION_PROMPT.format(tender_text=tender_text)

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You are a JSON API. You only return valid JSON arrays. Never return explanations or markdown."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.0,
        max_tokens=2048,
    )

    raw = response.choices[0].message.content.strip()
    if not raw.startswith("["):
        raise ValueError(f"RAW RESPONSE WAS: {raw[:500]}")
    return _parse_json_safe(raw, default=[])


def evaluate_bidder(client: Groq, bidder_name: str, bidder_text: str, criteria: list) -> list:
    criteria_json = json.dumps(criteria, indent=2)
    prompt = BIDDER_EVALUATION_PROMPT.format(
        criteria_json=criteria_json,
        bidder_text=bidder_text,
        bidder_name=bidder_name
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You are a JSON API. You only return valid JSON arrays. Never return explanations or markdown."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.0,
        max_tokens=2048,
    )

    raw = response.choices[0].message.content.strip()
    results = _parse_json_safe(raw, default=[])
    results = _align_results_to_criteria(results, criteria)
    return results


def _parse_json_safe(raw: str, default):
    """Very robust JSON parser."""
    # Remove markdown fences
    raw = re.sub(r'```json', '', raw)
    raw = re.sub(r'```', '', raw)
    raw = raw.strip()

    # Try direct parse first
    try:
        return json.loads(raw)
    except Exception:
        pass

    # Find array boundaries
    start = raw.find('[')
    end = raw.rfind(']')

    if start != -1 and end != -1 and end > start:
        chunk = raw[start:end+1]
        # Fix trailing commas
        chunk = re.sub(r',\s*}', '}', chunk)
        chunk = re.sub(r',\s*]', ']', chunk)
        try:
            return json.loads(chunk)
        except Exception:
            pass

    # Last resort: try to build array from objects
    objects = []
    for match in re.finditer(r'\{[^{}]+\}', raw, re.DOTALL):
        try:
            obj = json.loads(match.group())
            objects.append(obj)
        except Exception:
            pass

    if objects:
        return objects

    return default


def _align_results_to_criteria(results: list, criteria: list) -> list:
    result_names = {r.get("criterion_name", "").lower() for r in results}
    aligned = list(results)

    for criterion in criteria:
        name = criterion.get("criterion_name", "")
        if name.lower() not in result_names:
            aligned.append({
                "criterion_name": name,
                "extracted_value": "Not Found",
                "source_page": 0,
                "status": "Needs Review",
                "confidence": 0,
                "reasoning": "Could not locate relevant information in submitted documents."
            })

    return aligned


def compute_overall_status(results: list) -> str:
    statuses = [r.get("status", "Needs Review") for r in results]
    if "Fail" in statuses:
        return "Not Eligible"
    if "Needs Review" in statuses:
        return "Needs Review"
    return "Eligible"


def compute_average_confidence(results: list) -> float:
    confidences = [r.get("confidence", 0) for r in results]
    if not confidences:
        return 0.0
    return round(sum(confidences) / len(confidences), 1)