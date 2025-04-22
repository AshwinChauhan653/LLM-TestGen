### Updated utils/srs_parser.py

import re
from io import BytesIO
from PyPDF2 import PdfReader
import docx
import spacy
from spacy.matcher import Matcher

# Load spaCy model (ensure 'en_core_web_sm' is installed)
nlp = spacy.load("en_core_web_sm")

# Initialize matcher for condition words
matcher = Matcher(nlp.vocab)
pattern = [{"LOWER": {"IN": ["if", "when", "shall", "must"]}}]
matcher.add("REQUIREMENT_KEY", [pattern])


def extract_text_from_file(uploaded_file) -> str:
    """
    Detect file type by extension and extract plain text from .txt, .pdf, .docx.
    """
    name = uploaded_file.name.lower()
    if name.endswith('.txt'):
        return uploaded_file.read().decode('utf-8')
    elif name.endswith('.pdf'):
        reader = PdfReader(BytesIO(uploaded_file.read()))
        text = []
        for page in reader.pages:
            text.append(page.extract_text() or '')
        return '\n'.join(text)
    elif name.endswith('.docx'):
        doc = docx.Document(BytesIO(uploaded_file.read()))
        return '\n'.join([para.text for para in doc.paragraphs])
    else:
        raise ValueError(f"Unsupported file type: {name}")


def segment_requirements(text: str) -> list[str]:
    """
    Use spaCy to segment text into sentences and filter those matching requirement patterns.
    """
    doc = nlp(text)
    requirements = []
    for sent in doc.sents:
        # check for modal or conditional keywords via matcher
        if matcher(nlp(sent.text)):
            requirements.append(sent.text.strip())
    return requirements


def parse_structured_rule(sentence: str) -> dict:
    """
    Extract actor, action, condition, expected outcome from a requirement sentence.
    """
    doc = nlp(sentence)
    actor = ''
    action = ''
    condition = ''
    outcome = ''
    # Simple heuristic: first noun chunk is actor, main verb is action
    noun_chunks = list(doc.noun_chunks)
    if noun_chunks:
     actor = noun_chunks[0].text
    for token in doc:
        if token.pos_ == 'VERB':
            action = token.lemma_
            break
    # Condition: text before comma or 'if'
    m = re.search(r'(?:if|when)\s+([^,]+)', sentence, re.IGNORECASE)
    if m:
        condition = m.group(1).strip()
    # Expected outcome: phrase after 'then' or clause following comma
    parts = re.split(r'then|,', sentence, flags=re.IGNORECASE)
    if len(parts) > 1:
        outcome = parts[-1].strip()
    return {
        'description': sentence.strip(),
        'actor': actor,
        'action': action,
        'condition': condition,
        'expected_outcome': outcome
    }


def derive_testable_outcomes(rule: dict) -> list[dict]:
    """
    From a structured rule, identify variables and numeric constraints, derive boundary and equivalence tests.
    """
    desc = rule['description']
    outcomes = []
    # find numeric ranges like 1 to 10 or <= 5 etc
    ranges = re.findall(r'(\d+)\s*(?:to|-|–)\s*(\d+)', desc)
    for low, high in ranges:
        low, high = int(low), int(high)
        # boundary values
        tests = [low, low+1, high-1, high]
        outcomes.append({
            'variable_range': (low, high),
            'boundary_tests': tests,
            'equivalence_partitions': [
                {'type': 'below', 'value': low-1},
                {'type': 'within', 'value': (low+high)//2},
                {'type': 'above', 'value': high+1}
            ]
        })
    return outcomes


def extract_rules_from_text(text: str) -> list[dict]:
    """
    Full pipeline: text -> sentences -> structured rules -> testable outcomes
    Returns list of {'rule': structured_rule, 'tests': [...]} dicts.
    """
    raw_reqs = segment_requirements(text)
    structured = []
    for sent in raw_reqs:
        sr = parse_structured_rule(sent)
        tests = derive_testable_outcomes(sr)
        structured.append({'rule': sr, 'tests': tests})
    return structured

