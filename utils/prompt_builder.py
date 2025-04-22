def build_prompt(rule, strategy="boundary", framework="pytest"):
    """
    Builds a structured prompt for LLMs based on selected strategy and framework.
    """
    strategy_text = {
        "boundary": "Use boundary value analysis.",
        "equivalence": "Use equivalence partitioning.",
        "default": ""
    }

    framework_text = {
        "pytest": "Format the output using the Pytest framework.",
        "mocha": "Format the output using the Mocha testing framework.",
        "junit": "Format the output using the JUnit framework."
    }

    prompt = f"""
    This is an api call for test case generator you have to give only the required code redy to plug in for testing nothing else should be written
Generate a test case for the following rule:

\"{rule}\"

{strategy_text.get(strategy, '')}
{framework_text.get(framework, '')}
"""

    return prompt.strip()
