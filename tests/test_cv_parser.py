from services.cv_parser import extract_email, extract_phone, extract_years_of_experience, pick_name, _NLP


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