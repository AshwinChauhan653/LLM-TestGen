# utils/validation.py
import re

def extract_code(response: str) -> str:
    """
    Extracts the code block from an LLM response.
    Searches for text enclosed within triple backticks.
    If no code block is found, returns the entire response.
    """
    code_blocks = re.findall(r"```(?:\w+)?\n(.*?)\n```", response, re.DOTALL)
    if code_blocks:
        return code_blocks[0].strip()
    return response.strip()

def validate_code(code: str, framework: str) -> tuple:
    """
    Performs a basic validation of the extracted code based on the chosen test framework.
    Returns a tuple of (is_valid, message).
    """
    if framework == "pytest":
        if "def test_" in code and "assert" in code:
            return True, "Code appears to be a valid pytest test case."
        else:
            return False, "Code does not appear to be a valid pytest test case."
    elif framework == "mocha":
        if "describe(" in code and "it(" in code:
            return True, "Code appears to be a valid Mocha test case."
        else:
            return False, "Code does not appear to be a valid Mocha test case."
    elif framework == "junit":
        if "@Test" in code:
            return True, "Code appears to be a valid JUnit test case."
        else:
            return False, "Code does not appear to be a valid JUnit test case."
    else:
        return False, "Unknown framework for validation."
