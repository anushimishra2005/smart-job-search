import re


# Canonical skill names.
# Variations are mapped to one consistent name.
SKILL_PATTERNS = {
    "Python": [r"\bpython\b"],
    "Java": [r"\bjava\b"],
    "C++": [r"\bc\+\+\b"],
    "JavaScript": [r"\bjavascript\b", r"\bjs\b"],
    "TypeScript": [r"\btypescript\b", r"\bts\b"],
    "React": [r"\breact\.?js\b", r"\breact\b"],
    "React Native": [r"\breact native\b"],
    "Node.js": [r"\bnode\.?js\b"],
    "Express": [r"\bexpress\.?js\b", r"\bexpress\b"],
    "Flask": [r"\bflask\b"],
    "Django": [r"\bdjango\b"],
    "REST APIs": [r"\brestful?\s+apis?\b", r"\brest\s+apis?\b"],
    "SOAP": [r"\bsoap\b"],
    "SQL": [r"\bsql\b"],
    "MySQL": [r"\bmysql\b"],
    "MongoDB": [r"\bmongodb\b"],
    "PostgreSQL": [r"\bpostgresql\b", r"\bpostgres\b"],
    "AWS": [r"\baws\b", r"\bamazon web services\b"],
    "Azure": [r"\bazure\b"],
    "Docker": [r"\bdocker\b"],
    "Kubernetes": [r"\bkubernetes\b", r"\bk8s\b"],
    "Git": [r"\bgit\b"],
    "GitHub": [r"\bgithub\b"],
    "Machine Learning": [r"\bmachine learning\b"],
    "Deep Learning": [r"\bdeep learning\b"],
    "NLP": [r"\bnlp\b", r"\bnatural language processing\b"],
    "Scikit-learn": [r"\bscikit[- ]learn\b", r"\bsklearn\b"],
    "TensorFlow": [r"\btensorflow\b"],
    "PyTorch": [r"\bpytorch\b"],
    "Pandas": [r"\bpandas\b"],
    "NumPy": [r"\bnumpy\b"],
    "Streamlit": [r"\bstreamlit\b"],
    "HTML": [r"\bhtml5?\b"],
    "CSS": [r"\bcss3?\b", r"\bcascading style sheets\b"],
    "Redux": [r"\bredux\b"],
    "Redux Toolkit": [r"\bredux toolkit\b"],
    "JWT": [r"\bjwt\b", r"\bjson web token\b"],
    "bcrypt": [r"\bbcrypt\b"],
    "Jest": [r"\bjest\b"],
    "Blockchain": [r"\bblockchain\b"],
    "SDLC": [r"\bsdlc\b"],
    "CI/CD": [r"\bci\s*/\s*cd\b", r"\bcontinuous integration\b"],
}


def extract_skills(text):
    """Extract normalized technical skills from text."""

    if not text:
        return []

    found = []

    for skill, patterns in SKILL_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                found.append(skill)
                break

    return found


def extract_skill_set(text):
    """Return skills as a set for fast comparison."""

    return set(extract_skills(text))


if __name__ == "__main__":
    sample = """
    We need a Software Developer with Python, JavaScript, React,
    REST APIs, MongoDB, Docker and AWS experience.
    Knowledge of CI/CD and GitHub is preferred.
    """

    skills = extract_skills(sample)

    print("Detected skills:")
    for skill in skills:
        print(f"  ✓ {skill}")

    print(f"\nTotal: {len(skills)}")