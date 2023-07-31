import os
import openai
from CodeChecker import *

def parse_code(js_file):
    with open(js_file, "r") as file:
        js_code = file.read()
    return js_code

def get_few_shots(few_shot_file):
    with open(few_shot_file, "r") as file:
        few_shots = file.read()
    return few_shots

fqn_prompts_file = os.getcwd() + "/prompts_templates/fqn_prompts.txt"
code_generate_prompts_file = os.getcwd() + "/prompts_templates/code_generate_prompts.txt"

# js_file = "../data/Random Roll Call Page/app.js"

# TODO: Refactor the code optimization modules into a unified and streamlined process.
# TODO: Implement consistent formatting and structure for console output. :)
def main(code_file_path: str):
    fqn_prompts = get_few_shots(fqn_prompts_file)
    code_generate_prompts = get_few_shots(code_generate_prompts_file)

    code_snippet = parse_code(js_file=code_file_path)

    # proxies = {'http': "http://127.0.0.1:10792",
    #            'https': "http://127.0.0.1:10792"}
    # openai.proxy = proxies

    # OPENAI API key configuration
    # TODO: update API key
    openai.api_key = "API_KEY"

    kg = load_KB(os.getcwd() + "/knowledge_base/android_kb_6.json")

    print("Code checking...\n")
    codeChecker = CodeChecker(kg, fqn_prompts, code_generate_prompts)
    refined_code = codeChecker.code_check(code_snippet, max_loop=5)
    print("Code checking analysis completed. Rectified code:")
    print(refined_code)
    print()

if __name__ == "__main__":
    code_file_path = input("Please provide a JavaScript file:\n")
    main(code_file_path=code_file_path)
    # TODO: examples are added and are located in the examples folder :)
