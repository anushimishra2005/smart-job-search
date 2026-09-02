import re


# Common technical skills we want to detect.
SKILL_LIST = [
    "Python",
    "Java",
    "C++",
    "C",
    "JavaScript",
    "TypeScript",
    "React",
    "React Native",
    "Node.js",
    "Express",
    "Flask",
    "Django",
    "REST API",
    "REST APIs",
    "SQL",
    "MySQL",
    "MongoDB",
    "PostgreSQL",
    "AWS",
    "Azure",
    "Docker",
    "Kubernetes",
    "Git",
    "GitHub",
    "Machine Learning",
    "Deep Learning",
    "NLP",
    "Scikit-learn",
    "TensorFlow",
    "PyTorch",
    "Pandas",
    "NumPy",
    "Streamlit",
    "HTML",
    "CSS",
    "Redux",
    "Redux Toolkit",
    "JWT",
    "bcrypt",
    "Jest",
    "Blockchain",
]


def extract_skills(text):
    """Detect technical skills mentioned in resume text."""
    found_skills = []

    text_lower = text.lower()

    for skill in SKILL_LIST:
        pattern = r"(?<![a-z0-9])" + re.escape(skill.lower()) + r"(?![a-z0-9])"

        if re.search(pattern, text_lower):
            found_skills.append(skill)

    return found_skills


def extract_email(text):
    """Extract the first email address from resume text."""
    match = re.search(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        text
    )

    return match.group(0) if match else None


def extract_phone(text):
    """Extract a likely Indian phone number."""
    match = re.search(
        r"(?:\+91[\s-]?)?[6-9]\d{9}",
        text
    )

    return match.group(0) if match else None


def extract_name(text):
    """Extract a likely candidate name from the beginning of the resume."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    if lines:
        return lines[0]

    return None


def analyze_resume(text):
    """Convert raw resume text into a structured candidate profile."""
    return {
        "name": extract_name(text),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "skills": extract_skills(text),
    }


if __name__ == "__main__":
    from resume_parser import extract_resume_text

    resume_text = extract_resume_text("resume.pdf")
    profile = analyze_resume(resume_text)

    print("\n📄 Resume Profile")
    print("=" * 40)

    print(f"Name: {profile['name']}")
    print(f"Email: {profile['email']}")
    print(f"Phone: {profile['phone']}")

    print("\n🛠 Skills:")
    for skill in profile["skills"]:
        print(f"  ✓ {skill}")

    print(f"\nTotal skills detected: {len(profile['skills'])}")