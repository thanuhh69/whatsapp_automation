import re
from typing import Dict, Any, Tuple, List

DEFAULT_TEMPLATES = [
    {
        "id": "tpl_reg_confirm",
        "name": "Registration Confirmation",
        "content": "Hello {{name}}, thank you for registering with Q9X! We have confirmed your registration details."
    },
    {
        "id": "tpl_webinar_rem",
        "name": "Webinar Reminder",
        "content": "Hi {{name}}, friendly reminder that our upcoming Q9X session is tomorrow! Link sent to {{email}}."
    },
    {
        "id": "tpl_webinar_soon",
        "name": "Webinar Starting Soon",
        "content": "Hey {{name}}, we are starting live right now! Join the Q9X session."
    },
    {
        "id": "tpl_course_ann",
        "name": "Course Announcement",
        "content": "Dear {{name}}, applications for the Q9X specialized training cohort are now open."
    },
    {
        "id": "tpl_q9x_update",
        "name": "General Q9X Update",
        "content": "Hello {{name}}, here is an important community update from Q9X."
    }
]

def render_template(template_str: str, context: Dict[str, Any], skip_on_missing: bool = False) -> Tuple[str, bool, str]:
    """
    Renders template string replacing {{variable}} placeholders with context values.
    Returns (rendered_text, is_success, error_message).
    If skip_on_missing is True and a required variable is missing/empty, marks as failed/skipped.
    """
    if not template_str:
        return "", False, "Empty template"

    rendered = template_str
    matches = re.findall(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", template_str)

    missing_vars = []
    for var in set(matches):
        val = context.get(var)
        pattern = r"\{\{\s*" + re.escape(var) + r"\s*\}\}"
        if val is None or str(val).strip() == "":
            missing_vars.append(var)
            rendered = re.sub(pattern, f"[Missing {var}]", rendered)
        else:
            rendered = re.sub(pattern, str(val), rendered)

    if missing_vars and skip_on_missing:
        return rendered, False, f"Missing placeholder value(s): {', '.join(missing_vars)}"

    return rendered, True, ""
