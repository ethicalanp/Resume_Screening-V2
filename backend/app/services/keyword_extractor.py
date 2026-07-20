"""
General-purpose keyword extractor for resumes and job descriptions.
Supports dynamic HR-driven matching and non-technical roles by using a broad, flexible taxonomy.
"""

import re
from typing import Set, Iterable

# ── General Keyword Taxonomy ───────────────────────────────────────────────────
# This includes technical skills, business domains, non-tech roles, soft skills, and certifications.
GENERAL_KEYWORD_TAXONOMY: Set[str] = {
    # Technical skills
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "golang",
    "rust", "ruby", "php", "swift", "kotlin", "scala", "r", "matlab", "perl",
    "bash", "shell", "powershell", "dart", "elixir", "haskell", "lua", "groovy",
    "react", "reactjs", "react.js", "angular", "angularjs", "vue", "vuejs",
    "next.js", "nextjs", "nuxt", "nuxtjs", "gatsby", "svelte", "flutter", "android",
    "ios", "xcode", "swiftui", "django", "flask", "fastapi", "spring", "spring boot",
    "express", "node.js", "nodejs", "laravel", "rails", "ruby on rails", "asp.net",
    "dotnet", ".net", "grpc", "rest api", "soap", "websocket", "graphql", "docker",
    "kubernetes", "terraform", "ansible", "helm", "aws", "azure", "gcp", "google cloud",
    "s3", "rds", "ec2", "lambda", "postgresql", "mysql", "mongodb", "redis",
    "sql", "nosql", "tableau", "power bi", "pandas", "numpy", "scikit-learn", "tensorflow",
    "pytorch", "machine learning", "data science", "nlp", "ai", "cloud", "devops",

    # Business and operations
    "sales", "marketing", "digital marketing", "product management", "business analyst",
    "data analyst", "customer success", "customer service", "account management",
    "operations", "logistics", "supply chain", "finance", "accounting", "human resources",
    "recruiter", "talent acquisition", "training", "employee engagement", "learning and development",
    "administration", "office management", "executive assistant", "event planning",
    "project coordination", "vendor management", "procurement", "compliance", "quality assurance",
    "legal", "regulatory", "healthcare", "nursing", "education", "training and development",
    "customer experience", "risk management", "business development",

    # Soft skills and leadership
    "leadership", "communication", "teamwork", "collaboration", "problem solving",
    "critical thinking", "time management", "organization", "attention to detail",
    "stakeholder management", "presentation", "negotiation", "project management",
    "strategic planning", "decision making", "adaptability", "customer focus",

    # Certifications, methodologies, and tools
    "agile", "scrum", "kanban", "lean", "waterfall", "jira", "confluence",
    "notion", "salesforce", "hubspot", "quickbooks", "sap", "oracle",
    "microsoft office", "excel", "powerpoint", "sql server",
}


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def extract_keywords(text: str, taxonomy: Iterable[str] | None = None) -> Set[str]:
    """
    Extract keywords from text using a broad taxonomy.
    Defaults to the general taxonomy, but can use a custom set.
    """
    if not text:
        return set()

    text_lower = _normalize_text(text)
    taxonomy = taxonomy or GENERAL_KEYWORD_TAXONOMY
    matched: Set[str] = set()

    for keyword in taxonomy:
        keyword_lower = keyword.lower()
        pattern = r"(?<!\w)" + re.escape(keyword_lower) + r"(?!\w)"
        if re.search(pattern, text_lower):
            matched.add(keyword)

    return matched


# Backwards-compatible alias
extract_skills = extract_keywords


def get_skill_categories(skills: Set[str]) -> dict:
    """Group matched keywords into categories for display."""
    CATEGORIES = {
        "Technical Skills": {
            "python", "java", "javascript", "react", "aws", "azure", "docker", "kubernetes",
            "sql", "postgresql", "mysql", "mongodb", "flask", "fastapi",
            "tensorflow", "pytorch", "machine learning", "data science",
        },
        "Business Roles": {
            "sales", "marketing", "product management", "business analyst",
            "customer success", "operations", "finance", "accounting", "human resources",
            "recruiter", "project management", "compliance",
        },
        "Soft Skills": {
            "leadership", "communication", "teamwork", "problem solving",
            "critical thinking", "time management", "organization", "attention to detail",
            "presentation", "negotiation", "customer focus",
        },
    }

    result = {}
    for category, cat_keywords in CATEGORIES.items():
        matched_in_cat = skills & cat_keywords
        if matched_in_cat:
            result[category] = sorted(matched_in_cat)

    return result