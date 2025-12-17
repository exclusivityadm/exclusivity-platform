# FULL FILE — new
INIT_QS = [
    "Describe your brand in one sentence.",
    "Who is your ideal customer?",
    "Top 3 brand colors?",
    "Typical order value & margin range?",
    "Any words we should avoid in copy?"
]

def init_questions():
    return INIT_QS

def save_init_answers(supa, merchant_id: str, answers: dict):
    tone_tags = [k for k in answers.keys()]
    supa.table("brand_profile").update({"tone_tags": tone_tags}).eq("merchant_id", merchant_id).execute()
