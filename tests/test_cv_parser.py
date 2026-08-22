from services.cv_parser import (
    extract_email,
    extract_phone,
    extract_years_of_experience,
    pick_name,
    _NLP,
    extract_expertise,
    extract_certifications,
    extract_education,
    extract_companies_from_experience,
    _find_experience_section,
    parse_cv,
)


def test_extract_email_finds_valid_email():
    text = "Contact me at aziz.benamor@example.com for more info."
    assert extract_email(text) == "aziz.benamor@example.com"


def test_extract_email_returns_none_when_missing():
    assert extract_email("No email here.") is None


def test_extract_phone_finds_us_format():
    text = "Call me at (202) 867-5309 anytime."
    assert extract_phone(text) is not None


def test_extract_years_of_experience_picks_the_max():
    text = "I have 5 years experience, plus a prior 3 years internship."
    assert extract_years_of_experience(text) == 5


def test_pick_name_uses_first_line_for_western_name():
    text = "Aziz Benamor\nSoftware Engineer\naziz@example.com"
    doc = _NLP(text)
    assert pick_name(doc, text) == "Aziz Benamor"


def test_pick_name_uses_first_line_for_non_western_name():
    """Regression test: earlier version misfired on this, returning
    a GitHub handle ('posquit0') instead of the actual name because
    spaCy's PERSON NER under-detects non-Western names."""
    text = "Byungjin Park\nDevOps Engineer · Software Architect\nGitHub: @posquit0"
    doc = _NLP(text)
    assert pick_name(doc, text) == "Byungjin Park"

# ---------------------------------------------------------------------------
# extract_expertise: expertise domains derived from technical skills
# ---------------------------------------------------------------------------

def test_extract_expertise_derives_domains_from_skills():
    skills = ["Terraform", "Kubernetes", "Docker"]
    expertise = extract_expertise(skills)
    assert "Infrastructure as Code" in expertise
    assert "Container Orchestration" in expertise
    assert "DevOps" in expertise


def test_extract_expertise_is_empty_when_no_mapped_skills():
    assert extract_expertise(["some totally unmapped skill"]) == []


def test_extract_expertise_deduplicates_domains_triggered_by_multiple_skills():
    """Both Terraform and Kubernetes independently map to 'DevOps'; it
    should only be reported once, not once per triggering skill."""
    expertise = extract_expertise(["Terraform", "Kubernetes"])
    assert expertise.count("DevOps") == 1


def test_extract_expertise_preserves_first_appearance_order():
    # "DevOps" is first triggered by Terraform (first in the list);
    # "Service Mesh" only appears once we reach Istio.
    expertise = extract_expertise(["Terraform", "Istio"])
    assert expertise.index("DevOps") < expertise.index("Service Mesh")


# ---------------------------------------------------------------------------
# extract_certifications
# ---------------------------------------------------------------------------

CERT_SECTION_TEXT = """Certificates
2023
AWS Certified Solutions Architect - Professional, Amazon Web Services (AWS)
2021
Certified Kubernetes Application Developer (CKAD), The Linux Foundation

Education
State University
"""


def test_extract_certifications_merges_standalone_year_with_description():
    """Regression test: PDF layout extraction commonly puts a
    certification's year on its own line, separate from the description
    right after it. Without merging, a bare '2023' would be reported as
    its own fake certification entry."""
    certs = extract_certifications(CERT_SECTION_TEXT)
    assert certs == [
        "2023 AWS Certified Solutions Architect - Professional, Amazon Web Services (AWS)",
        "2021 Certified Kubernetes Application Developer (CKAD), The Linux Foundation",
    ]


def test_extract_certifications_returns_empty_list_when_no_section():
    assert extract_certifications("Just some CV text with no certificates section.") == []


# ---------------------------------------------------------------------------
# extract_companies_from_experience: layout regression tests
# ---------------------------------------------------------------------------

FOUR_LINE_LAYOUT_CV = """Work Experience

Acme Cloud Inc.
Seoul, S.Korea
Senior DevOps Engineer
Jan. 2020 - Mar. 2022

Bright Robotics Ltd. (BrightBot)
Austin, TX
Founding Engineer & Infrastructure Lead
Jun. 2017 - Dec. 2019

Education
State University
"""


def test_extract_companies_handles_company_location_role_date_on_separate_lines():
    """Regression test: résumés (e.g. this app's original test CV, an
    Awesome-CV LaTeX template) commonly lay out each work-experience entry
    across four separate lines -- Company / Location / Role / Date --
    rather than the 2-line layout (Company+Location, Role+Date) the
    original heuristic assumed. Before the fix, the line immediately above
    the date line was always the Role line, so the employer name was
    silently dropped."""
    doc = _NLP(FOUR_LINE_LAYOUT_CV)
    span = _find_experience_section(FOUR_LINE_LAYOUT_CV)
    companies = extract_companies_from_experience(doc, FOUR_LINE_LAYOUT_CV, span)

    assert "Acme Cloud Inc." in companies
    assert "Bright Robotics Ltd. (BrightBot)" in companies


def test_extract_companies_does_not_split_a_parenthetical_alias():
    """Regression test: a company written as 'Name Inc. (Alias)' should
    stay one entry. Before the layout-walk fix, this CV's companies list
    was populated entirely by the generic ORG-NER fallback, which
    sometimes split a parenthetical alias into its own separate 'company'."""
    doc = _NLP(FOUR_LINE_LAYOUT_CV)
    span = _find_experience_section(FOUR_LINE_LAYOUT_CV)
    companies = extract_companies_from_experience(doc, FOUR_LINE_LAYOUT_CV, span)

    assert "BrightBot" not in companies
    assert "Bright Robotics Ltd." not in companies  # only the full, unsplit form


# ---------------------------------------------------------------------------
# parse_cv: new top-level keys
# ---------------------------------------------------------------------------

SIMPLE_CV_FOR_PARSE = """Alex Rivera
Backend Engineer
alex.rivera@example.com

Work Experience

Backend Engineer, Northwind Systems
Built REST APIs with Python and FastAPI. Deployed on AWS. Used Docker and Kubernetes.

Skills
Python, FastAPI, Docker, Kubernetes, AWS

Education
Bachelor of Science, State University
"""


def test_parse_cv_includes_expertise_and_certifications_keys():
    result = parse_cv(SIMPLE_CV_FOR_PARSE)
    assert "expertise" in result
    assert "certifications" in result
    assert isinstance(result["expertise"], list)
    assert isinstance(result["certifications"], list)
    # Docker/Kubernetes should derive at least a DevOps-flavored expertise
    assert "DevOps" in result["expertise"]


# ---------------------------------------------------------------------------
# Section-entry grouping: education/certifications spanning multiple lines
# ---------------------------------------------------------------------------

# Mirrors a real CV where the institution name doesn't contain any of our
# English school keywords (falls into extract_education's fallback path),
# AND the date/location line is a visually distinct PDF block styled
# separately from the institution/degree block above it.
WRAPPED_EDUCATION_CV = """Education

Communication and MultiMedia
Institut Superieur des Arts Multimedia de la
Manouba(ISAMM)

09/2022 - Present,
Manouba

Skills
Python
"""


def test_extract_education_fallback_merges_wrapped_institution_and_trailing_date():
    """Regression test: a CV whose institution name wraps across several
    PDF-extracted lines, with the date/location styled as its own block,
    should come back as ONE education entry -- not one bullet per line."""
    result = extract_education(_NLP(WRAPPED_EDUCATION_CV), WRAPPED_EDUCATION_CV)
    assert len(result) == 1
    assert "Communication and MultiMedia" in result[0]
    assert "Manouba(ISAMM)" in result[0]
    assert "09/2022 - Present" in result[0]


# Mirrors a real CV where each certification's title and description wrap
# across two lines, with a blank line separating one certification from
# the next (as block-mode PDF extraction produces -- see cv_extraction.py).
WRAPPED_CERTIFICATIONS_TEXT = """Certificates

PROJET(PAQ-DGSE) (2024)
Attestation a la participation a la formation en "DESIGN THINKING"

Company Program les entrepreneurs de demain avec
INJAZ Tunisia a l'ISAMM ! (05/2024)

Education
State University
"""


def test_extract_certifications_groups_blank_line_separated_multiline_entries():
    """Regression test: two certifications, each wrapping across two
    lines, separated by a blank line, should come back as exactly two
    entries -- not four fragments (one per raw line)."""
    result = extract_certifications(WRAPPED_CERTIFICATIONS_TEXT)
    assert len(result) == 2
    assert "PROJET(PAQ-DGSE)" in result[0]
    assert "Attestation" in result[0]
    assert "Company Program" in result[1]
    assert "INJAZ Tunisia" in result[1]