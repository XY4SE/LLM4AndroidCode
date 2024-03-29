import os

import openai
import time
import sys
from contextlib import contextmanager

import GPT
from utils import *

def if_permission_is_text_or_code(id: str, initial_response: str, log_dir: str):
    print(f"Looking at Task {id}..")

    checker_gpt = GPT.GPT()

    log_dir = log_dir + f"/permission_in_text_or_code.txt"

    checker_gpt.manual_add_response(initial_response)

    print(initial_response)

    print("Waiting for Checker-GPT to response for permission information..")
    if_permission_provided_in_code_prompt = f"Is there AndroidManifest.xml or manifest file xml code containing permissions provided in the response?" \
                                            f"Answer in Yes or No only. No other text"
    response = checker_gpt.ask_checker(None, if_permission_provided_in_code_prompt)
    if response.lower().startswith("no."):
        print(f"Response: {response}")
        print("Permission not given in code..")
        with open(log_dir, "a+") as outfile:
            p_dict = {"id": id, "permission_provided": True, "in_code": False, "in_text": True}
            # Write the dictionary object to the file in JSON format
            json.dump(p_dict, outfile)
            outfile.write("\n")
    else:
        print(f"Response: {response}")
        print("Permission given in code..")
        with open(log_dir, "a+") as outfile:
            p_dict = {"id": id, "permission_provided": True, "in_code": True, "in_text": True}
            # Write the dictionary object to the file in JSON format
            json.dump(p_dict, outfile)
            outfile.write("\n")

    record_completed_task_id(os.getcwd() + "/permission_check_id_completed.txt", id)
    print("Responded. Logging conversation.")


def generate_code_desc_with_KG(id: str, task: str, KG: [dict], log_dir: str, sleep_time: int = 10):
    print(f"Looking at Task {id}..")

    main_gpt = GPT.GPT()
    checker_gpt = GPT.GPT()
    fqn_extractor = GPT.GPT()
    permission_extractor = GPT.GPT

    # log file configuration
    main_log_dir = log_dir + f"/task_{id}_main.txt"
    checker_log_dir = log_dir + f"/task_{id}_checker.txt"
    final_log_dir = log_dir + f"/task_{id}_final.txt"
    stats_log_dir = log_dir + f"/task_{id}_stats.txt"

    # ask task first, use main gpt
    print(f"Waiting for gpt to response for \"{task}\"")
    task = task + " API level is set to be 33."
    response = main_gpt.ask_gpt(task)
    log_QnA(main_log_dir, task, response) # log to corresponding file - main
    print("Responded. Logging conversation.")
    time.sleep(sleep_time)

    # code with description, generated by main gpt
    code_and_desc_generated = response
    code_has_regenerated = False

    # permission declared list
    permission_list = []

    mtd_permission_to_check_list = []

    # add the inital response to checker gpt
    # checker_gpt.manual_add_response(code_and_desc_generated)
    fqn_extractor.manual_add_response(code_and_desc_generated)
    permission_extractor.manual_add_response(code_and_desc_generated)

    # ask if permission information were provided - use checker
    print("Waiting for Checker-GPT to response for permission information..")
    if_permission_provided_prompt = f"Does your response contains permission information? If Yes, give a list of the permissions, permissions listed should start with \"Manifest.permission\". If No, answer No only. No other text"
    # response = checker_gpt.ask_checker(None, if_permission_provided_prompt)
    response = permission_extractor.ask_checker(None, if_permission_provided_prompt)

    if response.lower().startswith("yes."):
        permission_list = extract_permission_strings(response)

    log_QnA(checker_log_dir, if_permission_provided_prompt, f"{response}\n\n + From response, we get: {permission_list}")
    print("Responded. Logging conversation.")
    time.sleep(sleep_time)  # 为了避免OpenAI API调用过于频繁而被限制，建议加入一个时间间隔

    n_attempt = 0
    max_attempt = 5

    while n_attempt < max_attempt:
        # list FQNs from code - use checker
        if code_has_regenerated:
            # checker_gpt.manual_add_response(code_and_desc_generated)
            fqn_extractor.manual_add_response(code_and_desc_generated)
            permission_extractor.manual_add_response(code_and_desc_generated)
            code_has_regenerated = False

        print("Waiting for Checker-GPT to response for FQNs..")
        FQN_prompt = "List the fully qualified name of the Java JDK and Android methods used in the code above, exclude Constructor methods. Fully qualified name contains package.class.method(parameters), starts with \"android.\" or \"java.\". Parameters must be fully qualified, starts with \"android.\" or \"java.\". Provide no other text."
        # response = checker_gpt.ask_checker(None, FQN_prompt)
        response = fqn_extractor.ask_checker(None, FQN_prompt)

        fqn_list = extract_method_names(response)

        log_QnA(checker_log_dir, FQN_prompt, f"{response}\n\n + From response, we get: {fqn_list}")
        print("Responded. Logging conversation.")
        time.sleep(sleep_time)

        # clear
        # checker_gpt.clear_context_conversion()
        fqn_extractor.clear_context_conversion()
        permission_extractor.clear_context_conversion()

        # do aa API valid check - by me use KG, a max round should be set to prevent infinite loop
        # check deprecated API - by me use KG
        print("Checking invalid and deprecated APIs..")
        invalid_methods = []
        deprecated_methods = []
        for fully_qualified_method in fqn_list:
            result = search_KB(fully_qualified_method, KG)
            if result is None:
                invalid_methods.append(fully_qualified_method)
                continue

            if result["API_level_deprecated"] is not None:
                alternative_methods = result["API_alternative"]
                if alternative_methods is not None and alternative_methods:
                    deprecated_methods.append((fully_qualified_method, alternative_methods))

            mtd_permission_to_check_list.append(result)

        log_stats(stats_log_dir, invalid_mtd_list=invalid_methods, deprecated_list=deprecated_methods, loop_count=n_attempt)
        print("Check completed. Logging stats.")

        if (len(invalid_methods) > 0 or len(deprecated_methods) > 0) and n_attempt < max_attempt:
            print(f"Number of invalid methods: {len(invalid_methods)}, Number of deprecated methods: {len(deprecated_methods)}")
            if n_attempt < max_attempt:
                print(f"Loop {n_attempt + 1} / {max_attempt}. Expects next loop.")
            else:
                print(f"Last loop {n_attempt + 1} / {max_attempt} reached. Loop expects to terminate.")
        else:
            print(f"Number of invalid methods: {len(invalid_methods)}, Number of deprecated methods: {len(deprecated_methods)}")
            print(f"Attempt {n_attempt + 1}/{max_attempt}. Loop expects to terminate.")

        if not invalid_methods and not deprecated_methods:
            print("Loop is terminated. OK")
            break

        all_invalid_deprecated_in_one_prompt = combine_all_invalid_deprecated_to_change_in_one_big_prompt(invalid_methods, deprecated_methods)

        print(f"Waiting for Main-GPT to response for invalid and deprecated API(s)..")
        response = main_gpt.ask_gpt(all_invalid_deprecated_in_one_prompt)
        log_QnA(main_log_dir, all_invalid_deprecated_in_one_prompt, response)
        print("Responded. Logging conversation.")
        time.sleep(sleep_time)

        code_and_desc_generated = response
        code_has_regenerated = True
        n_attempt += 1

    # ask if permission information were provided - use checker
    print("Waiting for Checker-GPT to response for permission information..")
    if_permission_provided_prompt = f"Does your response contains permission information? If Yes, give a list of the permissions, permissions listed should start with \"Manifest.permission\". If No, answer No only. No other text"
    # response = checker_gpt.ask_checker(None, if_permission_provided_prompt)
    response = permission_extractor.ask_checker(None, if_permission_provided_prompt)

    if response.lower().startswith("yes."):
        permission_list = extract_permission_strings(response)

    log_QnA(checker_log_dir, if_permission_provided_prompt,
            f"{response}\n\n + From response, we get: {permission_list}")
    print("Responded. Logging conversation.")
    time.sleep(sleep_time)

    # check permission - use KG
    all_permissions_to_add_prompt, permission_missing_list = combine_all_permissions_to_add_in_one_big_prompt(mtd_permission_to_check_list, permission_list)

    if permission_missing_list:
        print(f"Waiting for Main-GPT to response for adding {len(permission_missing_list)} missing permission(s) declaration..")
        response = main_gpt.ask_gpt(all_permissions_to_add_prompt)
        log_QnA(main_log_dir, all_permissions_to_add_prompt, response)
        print("Responded. Logging conversation.")
        time.sleep(sleep_time)
    else:
        print("No missing permission declaration..")

    print(f"Logging permissions stat..")
    log_permission_stats(log_dir+"/permission_stat.txt", id, permission_list, permission_missing_list)

    # TODO: summarize and output the new code + description. record this in task_XXX_final.txt
    print(f"Waiting for Main-GPT to summarize and generate new output..")
    response = main_gpt.ask_gpt("Review and summarize the responses and feedback provided. Provide a new updated version of code snippet and permission declaration.")
    log_QnA(final_log_dir, "", response)
    print("Responded. Logging conversation.")
    time.sleep(sleep_time)  # 为了避免OpenAI API调用过于频繁而被限制，建议加入一个时间间隔

    record_completed_task_id(os.getcwd() + "/tasks_completed.txt", id)
    print(f"Task {id} completed!\n")
    return

def main():

    ################################################################################################################
    ######################################### Configuration Setting ################################################
    ################################################################################################################

    # set current working directory
    cwd = os.getcwd()

    # OPENAI API key configuration
    # TODO: Check key before run
    openai.api_key = os.getenv("OPENAI_API_KEY")

    # read KG
    android_kg = read_KG(cwd + "/android_kb_6.json")

    # set the name of the file to which the console output will be written
    output_file_name = cwd + "/console_output_permission.txt"

    # txt file containing all the tasks
    android_task_txt = cwd + "/android_task_all.txt"

    fqn_prompts_file = os.getcwd() + "/prompts/fqn_prompts.txt"
    code_generate_prompts_file = os.getcwd() + "/prompts/code_generate_prompts.txt"

    tasks_list = read_tasks_from_txt(android_task_txt)

    log_dir = cwd + "/error_tasks_log"

    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # get the previously completed task ids, so that we can skip them
    if os.path.exists(os.getcwd() + "/error_tasks_completed.txt"):
        completed_task_id_list = get_completed_task_id(os.getcwd() + "/error_tasks_completed.txt")
    else:
        completed_task_id_list = []


    tasks_id_to_check = get_error_task_id(cwd + "/tasks_id_to_check.txt")
    print(f"Task IDs to check are: {tasks_id_to_check}")

    tasks_completed = get_completed_task_id(cwd + "/permission_check_id_completed.txt")
    #
    print(f"Completed task IDs are: {completed_task_id_list}")

    ################################################################################################################
    ######################################### Start GPT with KG ####################################################
    ################################################################################################################

    with open(output_file_name, "a+") as output_file, redirect_stdout_tee(output_file, sys.stdout):

        for task in tasks_list:
            id, task, api = get_task(task)

            # if task_id has run before, we skip it
            if id in completed_task_id_list:
                continue

            try:
                generate_code_desc_with_KG(id=id, task=task, KG=android_kg, log_dir=log_dir, sleep_time=10)
            except openai.error.InvalidRequestError or openai.error.RateLimitError or openai.error.Timeout or openai.error.APIError :
                print(f"Task {id} encountered error. Log to error.log\n")
                record_error_task_id(os.getcwd() + "/new_error_tasks.txt", id)
                record_completed_task_id(os.getcwd() + "/error_tasks_completed.txt", id)


@contextmanager
def redirect_stdout_tee(file1, file2):
    """
    Redirects standard output to two file objects simultaneously.
    """
    class Tee(object):
        def __init__(self, file1, file2):
            self.file1 = file1
            self.file2 = file2

        def write(self, data):
            self.file1.write(data)
            self.file2.write(data)

        def flush(self):
            self.file1.flush()
            self.file2.flush()

    original_stdout = sys.stdout
    sys.stdout = Tee(file1, file2)
    try:
        yield
    finally:
        sys.stdout = original_stdout

if __name__ == "__main__":
    main()




