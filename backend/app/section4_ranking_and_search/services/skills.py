"""
Canonical Skill Alias Dictionary, Normalization, and Overlap Calculation.
"""
import re
from typing import Dict, List, Set, Tuple

# Comprehensive canonical skill aliases dictionary
CANONICAL_SKILL_MAP: Dict[str, str] = {
    # Languages
    "js": "JavaScript",
    "javascript": "JavaScript",
    "ts": "TypeScript",
    "typescript": "TypeScript",
    "py": "Python",
    "python": "Python",
    "golang": "Go",
    "go": "Go",
    "c++": "C++",
    "cpp": "C++",
    "c#": "C#",
    "csharp": "C#",
    "rb": "Ruby",
    "ruby": "Ruby",
    "rust": "Rust",
    "java": "Java",
    "kotlin": "Kotlin",
    "swift": "Swift",
    "php": "PHP",
    
    # Frontend & UI
    "react": "React",
    "react.js": "React",
    "reactjs": "React",
    "next": "Next.js",
    "next.js": "Next.js",
    "nextjs": "Next.js",
    "vue": "Vue.js",
    "vue.js": "Vue.js",
    "vuejs": "Vue.js",
    "angular": "Angular",
    "svelte": "Svelte",
    "tailwind": "Tailwind CSS",
    "tailwindcss": "Tailwind CSS",
    "css": "CSS",
    "html": "HTML",
    "redux": "Redux",
    
    # Backend & Runtimes
    "node": "Node.js",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "express": "Express",
    "express.js": "Express",
    "fastapi": "FastAPI",
    "django": "Django",
    "flask": "Flask",
    "spring": "Spring Boot",
    "spring boot": "Spring Boot",
    "rails": "Ruby on Rails",
    "ruby on rails": "Ruby on Rails",
    "graphql": "GraphQL",
    "rest": "REST APIs",
    "restful": "REST APIs",
    "grpc": "gRPC",

    # Cloud & DevOps
    "aws": "AWS",
    "amazon web services": "AWS",
    "gcp": "GCP",
    "google cloud": "GCP",
    "google cloud platform": "GCP",
    "azure": "Azure",
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    "docker": "Docker",
    "terraform": "Terraform",
    "ci/cd": "CI/CD",
    "cicd": "CI/CD",
    "linux": "Linux",

    # Databases
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "mysql": "MySQL",
    "mongo": "MongoDB",
    "mongodb": "MongoDB",
    "redis": "Redis",
    "sqlite": "SQLite",
    "dynamodb": "DynamoDB",

    # Data & AI
    "ml": "Machine Learning",
    "machine learning": "Machine Learning",
    "ai": "Artificial Intelligence",
    "artificial intelligence": "Artificial Intelligence",
    "llm": "LLMs",
    "llms": "LLMs",
    "pytorch": "PyTorch",
    "tf": "TensorFlow",
    "tensorflow": "TensorFlow",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "spark": "Apache Spark",
}


def normalize_skill(skill: str) -> str:
    """Returns canonical form of skill name, or title-cased string if unmapped."""
    if not skill or not isinstance(skill, str):
        return ""
    cleaned = skill.strip().lower()
    return CANONICAL_SKILL_MAP.get(cleaned, skill.strip())


def calculate_skill_overlap(
    candidate_skills: List[str],
    job_text: str,
    job_title: str = "",
) -> Tuple[float, List[str], List[str]]:
    """
    Computes overlap between candidate skills and job posting text/title.
    Uses word-boundary regex for precision.
    Returns: (overlap_percentage (0-100), matched_skills, missing_skills).
    """
    if not candidate_skills:
        return 50.0, [], []

    search_corpus = f"{job_title}\n\n{job_text}".lower()
    matched: Set[str] = set()
    missing: Set[str] = set()

    for raw_skill in candidate_skills:
        canonical = normalize_skill(raw_skill)
        skill_lower = canonical.lower()

        # Find all known alias terms for this canonical skill
        alias_terms = {skill_lower}
        for alias, canon in CANONICAL_SKILL_MAP.items():
            if canon.lower() == skill_lower:
                alias_terms.add(alias.lower())

        # Check if any alias occurs in the corpus with word boundaries
        found = False
        for term in alias_terms:
            # Escape regex special chars (like c++, c#, .js)
            escaped = re.escape(term)
            # Match boundary or symbol edge
            pattern = rf"(?:\b|(?<=[^a-zA-Z0-9])){escaped}(?:\b|(?=[^a-zA-Z0-9]))"
            if re.search(pattern, search_corpus, re.IGNORECASE):
                found = True
                break

        if found:
            matched.add(canonical)
        else:
            missing.add(canonical)

    total_candidate = len(candidate_skills)
    overlap_score = (len(matched) / total_candidate) * 100.0 if total_candidate > 0 else 50.0

    return round(overlap_score, 2), sorted(list(matched)), sorted(list(missing))
