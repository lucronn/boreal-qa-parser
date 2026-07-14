import re

# Regex to match Boreal findings:
# Format: - [emoji] `[severity]` [`[rule]`] **[title]**
BOREAL_FINDING_PATTERN = re.compile(
    r'^[\s]*-\s*(?:❌|⚠️|ℹ️|✅)\s*`([^`]+)`\s*\[`([^`]+)`\]\s*\*\*(.*?)\*\*'
)

def parse_boreal_comment(body):
    """
    Parses a GitHub issue/PR comment body and extracts Boreal Env QA pre-flight findings.
    
    Returns a dictionary with:
        - has_boreal_section: bool
        - grader_qa_result: dict or None
        - findings: list of dicts (severity, rule, title, details)
    """
    res = {
        "has_boreal_section": False,
        "grader_qa_result": None,
        "findings": []
    }
    
    if "### Boreal Results" not in body:
        # Fallback check
        if "env qa pre-flight" not in body.lower():
            return res
            
    res["has_boreal_section"] = True
    
    # Try to extract grader QA result summary
    grade_match = re.search(r'-\s*(?:✅|⚠️|❌)\s*Grade:\s*`([^`]+)`', body)
    score_match = re.search(r'-\s*Score:\s*`([^`]+)`', body)
    min_axis_match = re.search(r'-\s*Minimum axis score:\s*`([^`]+)`', body)
    model_match = re.search(r'-\s*Model:\s*`([^`]+)`', body)
    summary_match = re.search(r'-\s*Summary:\s*([^\n]+)', body)
    
    if grade_match or score_match:
        res["grader_qa_result"] = {
            "grade": grade_match.group(1) if grade_match else "unknown",
            "score": score_match.group(1) if score_match else "N/A",
            "min_axis_score": min_axis_match.group(1) if min_axis_match else "N/A",
            "model": model_match.group(1) if model_match else "N/A",
            "summary": summary_match.group(1).strip() if summary_match else ""
        }
        
    # Extract findings
    lines = body.split('\n')
    current_finding = None
    
    for line in lines:
        match = BOREAL_FINDING_PATTERN.match(line)
        if match:
            if current_finding:
                res["findings"].append(current_finding)
            severity = match.group(1).strip()
            rule = match.group(2).strip()
            title = match.group(3).strip()
            current_finding = {
                "severity": severity,
                "rule": rule,
                "title": title,
                "details": []
            }
        elif current_finding:
            stripped = line.strip()
            if stripped.startswith('-'):
                # Detail item
                detail = stripped.lstrip('-').strip()
                current_finding["details"].append(detail)
            elif stripped.startswith('*') or stripped.startswith('+'):
                detail = stripped.lstrip('*+').strip()
                current_finding["details"].append(detail)
            elif stripped == "" or stripped.startswith('<') or stripped.startswith('###'):
                # Empty line or HTML tag or next section header - finish current finding
                res["findings"].append(current_finding)
                current_finding = None
            else:
                # Text continuation of detail
                if current_finding["details"]:
                    current_finding["details"][-1] += " " + stripped
                else:
                    current_finding["details"].append(stripped)
                    
    if current_finding:
        res["findings"].append(current_finding)
        
    return res

def parse_trusted_ci_metadata(body):
    """
    Parses general Trusted CI decision and details from the comment body.
    """
    res = {
        "decision": "unknown",
        "next_action": "",
        "required_fixes": []
    }
    
    decision_match = re.search(r'\*\*Decision:\*\*\s*(.*)', body)
    next_action_match = re.search(r'\*\*Next action:\*\*\s*(.*)', body)
    
    if decision_match:
        res["decision"] = decision_match.group(1).strip()
    if next_action_match:
        res["next_action"] = next_action_match.group(1).strip()
        
    # Extract fixes under "### Required Fixes"
    fixes_section = re.split(r'### Required Fixes', body)
    if len(fixes_section) > 1:
        fixes_body = fixes_section[1].split('###')[0].split('<details')[0]
        # Look for numbered list: 1. **Title**\n   Source: ...\n   Problem: ...\n   Suggested fix: ...
        fixes_matches = re.finditer(r'\d+\.\s+\*\*(.*?)\*\*(.*?)(?=(?:\d+\.\s+\*\*)|$)', fixes_body, re.DOTALL)
        for m in fixes_matches:
            title = m.group(1).strip()
            content = m.group(2).strip()
            
            source_m = re.search(r'Source:\s*`([^`]+)`', content)
            severity_m = re.search(r'Severity:\s*`([^`]+)`', content)
            problem_m = re.search(r'Problem:\s*(.*?)(?=Suggested fix:|$)', content, re.DOTALL)
            fix_m = re.search(r'Suggested fix:\s*(.*)', content, re.DOTALL)
            
            res["required_fixes"].append({
                "title": title,
                "source": source_m.group(1).strip() if source_m else "unknown",
                "severity": severity_m.group(1).strip() if severity_m else "error",
                "problem": problem_m.group(1).strip() if problem_m else "",
                "suggested_fix": fix_m.group(1).strip() if fix_m else ""
            })
            
    return res

def parse_auto_qa_assessment(body):
    """
    Parses Auto QA Assessment section from the comment.
    """
    res = {
        "has_auto_qa": False,
        "overall": "unknown",
        "confidence": "unknown",
        "summary": "",
        "issues": []
    }
    
    if "### Auto QA Assessment" not in body:
        return res
        
    res["has_auto_qa"] = True
    
    # Split to get Auto QA section
    section = body.split("### Auto QA Assessment")[1].split("###")[0].split("<details")[0]
    
    overall_m = re.search(r'-\s*Overall:\s*`([^`]+)`', section, re.IGNORECASE) or re.search(r'-\s*Overall:\s*([^\n]+)', section, re.IGNORECASE)
    confidence_m = re.search(r'-\s*Confidence:\s*`([^`]+)`', section, re.IGNORECASE) or re.search(r'-\s*Confidence:\s*([^\n]+)', section, re.IGNORECASE)
    
    if overall_m:
        res["overall"] = overall_m.group(1).strip().replace("`", "")
    if confidence_m:
        res["confidence"] = confidence_m.group(1).strip().replace("`", "")
        
    # The summary is usually the text right below the bullet points
    lines = [l.strip() for l in section.split('\n') if l.strip()]
    summary_lines = []
    issues = []
    
    recording_summary = False
    recording_issues = False
    
    for line in lines:
        if line.startswith("- Overall:") or line.startswith("- Confidence:"):
            recording_summary = True
            continue
        if "Issues Auto QA considers blocking:" in line or "Issues " in line:
            recording_summary = False
            recording_issues = True
            continue
        
        if recording_issues:
            if line.startswith("-"):
                issues.append(line.lstrip("-").strip())
            else:
                if issues:
                    issues[-1] += " " + line
        elif recording_summary:
            summary_lines.append(line)
            
    res["summary"] = " ".join(summary_lines)
    res["issues"] = issues
    return res
