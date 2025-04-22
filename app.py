import streamlit as st
import json
from utils.srs_parser import extract_text_from_file, extract_rules_from_text
from utils.llm_api import get_gpt_response, get_deepseek_response, get_gemini_response
from utils.prompt_builder import build_prompt
from utils.validation import extract_code, validate_code
from zipfile import ZipFile
from datetime import date
from io import BytesIO

# Initialize persistent storage for all outputs if not already done
if "all_outputs" not in st.session_state:
    st.session_state.all_outputs = {}

st.set_page_config(page_title="LLM Test Case Generator", layout="centered")
st.title("🧠 LLM-Based Test Case Generator")
st.subheader("Step 1: Upload your SRS document")

# SRS Upload and Advanced Parsing
uploaded_file = st.file_uploader(
    "Choose an SRS file (.txt, .pdf, .docx)",
    type=["txt", "pdf", "docx"]
)
if uploaded_file:
    # 1) Extract plain text
    srs_text = extract_text_from_file(uploaded_file)

    # 2) Show a preview of the raw SRS
    st.text_area("📄 SRS Preview", srs_text, height=300)
    st.success("SRS loaded successfully!")

    # 3) Run the NLP pipeline to get structured rules + test outcomes
    structured_rules = extract_rules_from_text(srs_text)
    st.session_state.structured_rules = structured_rules

    # 4) Render each rule's details
    st.subheader("🔍 Extracted Rules & Testable Outcomes")
    for idx, item in enumerate(structured_rules, start=1):
        rule = item["rule"]
        tests = item.get("tests", [])
        st.markdown(f"**{idx}.** {rule['description']}")
        st.markdown(f"- Actor: {rule['actor']}  ")
        st.markdown(f"- Action: {rule['action']}")
        if rule["condition"]:
            st.markdown(f"- Condition: {rule['condition']}")
        if tests:
            bt = tests[0]["boundary_tests"]
            eq = [p["value"] for p in tests[0]["equivalence_partitions"]]
            st.markdown(f"- Boundary Tests: {bt}")
            st.markdown(f"- Equivalence: {eq}")
else:
    st.info("Please upload a `.txt`, `.pdf`, or `.docx` file containing your SRS.")

# Strategy and Framework Selection
st.subheader("🧪 Prompt Builder + LLM Comparison")
strategy = st.selectbox("Choose a Test Strategy", ["boundary", "equivalence", "default"])
framework = st.selectbox("Choose Test Framework", ["pytest", "mocha", "junit"])

# Process each structured rule for generation & display
if "all_outputs" in st.session_state and st.session_state.all_outputs and not uploaded_file:
    rule_keys = list(st.session_state.all_outputs.keys())
else:
    rule_keys = [f"Rule {i+1}" for i in range(len(st.session_state.get("structured_rules", [])))]

for idx, rule_key in enumerate(rule_keys):
    # Fetch structured rule dict
    if rule_key in st.session_state.all_outputs:
        record = st.session_state.all_outputs[rule_key]
        structured = record["rule"]
    else:
        structured = st.session_state.structured_rules[idx]["rule"]

    desc = structured["description"]
    with st.expander(f"{rule_key}: {desc}"):
        # Build prompt off the description
        prompt = build_prompt(desc, strategy, framework)
        st.code(prompt, language="markdown")

        # Model selection
        selected_models = st.multiselect(
            f"Select LLMs for {rule_key}",
            ["gpt-3.5-turbo", "gpt-4", "deepseek", "gemini"],
            default=["gemini"],
            key=f"model_select_{idx}"
        )

        # Generate and auto-validate
        if st.button(f"🔁 Generate & Validate for {rule_key}", key=f"gen_validate_{idx}"):
            with st.spinner("Generating and validating test cases..."):
                outputs = {}
                validations = {}
                for model_name in selected_models:
                    # Query each model
                    if model_name.startswith("gpt"):
                        resp = get_gpt_response(prompt, model=model_name)
                    elif model_name == "deepseek":
                        resp = get_deepseek_response(prompt)
                    else:
                        resp = get_gemini_response(prompt)
                    outputs[model_name] = resp

                    # Extract and validate code
                    code = extract_code(resp)
                    valid, message = validate_code(code, framework)
                    validations[model_name] = {"extracted_code": code, "valid": valid, "message": message}

                # Persist in session state
                st.session_state.all_outputs[rule_key] = {
                    "rule": structured,
                    "prompt": prompt,
                    "responses": outputs,
                    "validation": validations
                }

        # Display generated and validated test cases
        if rule_key in st.session_state.all_outputs:
            data = st.session_state.all_outputs[rule_key]
            st.markdown("#### Generated & Validated Test Cases")
            tabs = st.tabs(list(data["responses"].keys()))
            for tab, model_name in zip(tabs, data["responses"].keys()):
                val = data["validation"][model_name]
                with tab:
                    st.markdown(f"##### 🧠 {model_name}")
                    st.code(data["responses"][model_name], language="python")
                    st.markdown("**Extracted Code:**")
                    st.code(val["extracted_code"], language="python")
                    # Show validation status
                    if val["valid"]:
                        st.success(val["message"])
                    else:
                        st.error(val["message"])
                        # Repair logic
                        if st.button(f"🛠️ Repair {model_name}", key=f"repair_{idx}_{model_name}"):
                            with st.spinner("Repairing test case..."):
                                repair_prompt = (
                                    f"The following test case for the rule '{desc}' is invalid because: {val['message']}\n"
                                    f"Please regenerate a correct {framework} test case using the {strategy} strategy."
                                    " Provide only the code block ready to plug in."
                                )
                                if model_name.startswith("gpt"):
                                    rep = get_gpt_response(repair_prompt, model=model_name)
                                elif model_name == "deepseek":
                                    rep = get_deepseek_response(repair_prompt)
                                else:
                                    rep = get_gemini_response(repair_prompt)
                                rep_code = extract_code(rep)
                                rep_valid, rep_msg = validate_code(rep_code, framework)
                                # Update session state
                                st.session_state.all_outputs[rule_key]["responses"][model_name] = rep
                                st.session_state.all_outputs[rule_key]["validation"][model_name] = {
                                    "extracted_code": rep_code,
                                    "valid": rep_valid,
                                    "message": rep_msg
                                }
                                st.experimental_rerun()

# Day 8: Exporter & Formatter
st.subheader("📦 Export Test Cases")
json_data = json.dumps(st.session_state.all_outputs, indent=2)
st.download_button(
    label="Download Raw JSON",
    data=json_data,
    file_name="test_cases.json",
    mime="application/json"
)
frameworks = st.multiselect("Frameworks to Export", ["pytest", "mocha", "junit"])
if st.button("📥 Export Selected"):
    if not frameworks:
        st.warning("Select at least one framework to export.")
    else:
        today = date.today().isoformat()
        files = {}
        # Generate framework files
        if "pytest" in frameworks:
            header = f"# Generated on {today} by LLM Test Case Generator\n\n"
            tests = []
            for data in st.session_state.all_outputs.values():
                for val in data["validation"].values():
                    if val["valid"]:
                        tests.append(val["extracted_code"])
            content = header + "\n\n".join(tests)
            files[f"llm_tests_pytest.py"] = content
        if "mocha" in frameworks:
            header = f"// Generated on {today} by LLM Test Case Generator\n\n"
            body_tests = []
            for data in st.session_state.all_outputs.values():
                for val in data["validation"].values():
                    if val["valid"]:
                        body_tests.append(val["extracted_code"])
            wrapped = "describe('LLM Test Suite', () => {\n" + "\n\n".join(["    " + line for code in body_tests for line in code.splitlines()]) + "\n});\n"
            files[f"llm_tests_mocha.js"] = header + wrapped
        if "junit" in frameworks:
            header = f"// Generated on {today} by LLM Test Case Generator\n\nimport org.junit.jupiter.api.Test;\nimport static org.junit.jupiter.api.Assertions.*;\n\npublic class LLMTestSuite \n"
            methods = []
            for data in st.session_state.all_outputs.values():
                for val in data["validation"].values():
                    if val["valid"]:
                        methods.append(val["extracted_code"])
            indented = "\n\n".join(["    " + line for code in methods for line in code.splitlines()])
            closing = "\n}\n"
            files[f"llm_tests_junit.java"] = header + indented + closing
        # Package
        if len(files) > 1:
            files["test_cases.json"] = json_data
            buffer = BytesIO()
            with ZipFile(buffer, "w") as zipf:
                for fname, data in files.items():
                    zipf.writestr(fname, data)
            st.download_button(
                label="Download ZIP",
                data=buffer.getvalue(),
                file_name=f"llm_test_suite_{today}.zip",
                mime="application/x-zip-compressed"
            )
        else:
            fname, data = next(iter(files.items()))
            st.download_button(
                label=f"Download {fname}",
                data=data,
                file_name=fname,
                mime="application/octet-stream"
            )
