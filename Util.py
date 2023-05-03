import itertools
import os
import random
import re
import json
from typing import Any, Union, Tuple, List


def search_KG(fqn_of_target_method: str, kg: [dict]) -> dict:
    """
    Search through Knowledge Graph by matching FQN and return its exceptions to be handled
    :param fqn_of_target_method: the fully qualified name of our target API
    :param kg: knowledge graph
    :return: a list of exceptions that the target API needs to handle, None if unable to find target API
    """

    fqn_of_target_method = fqn_of_target_method.replace(" ", "")

    # first round check
    for api_dict in kg:
        fqn_of_method_in_kg = api_dict["API_name"]
        fqn_of_method_in_kg = fqn_of_method_in_kg.replace(" ", "")
        if fqn_of_target_method == fqn_of_method_in_kg:
            return api_dict

    # second round check if method is inherited from parent classes
    for api_dict in kg:
        fqn_of_method_in_kg = api_dict["API_name"]
        fqn_of_method_in_kg = fqn_of_method_in_kg.replace(" ", "")
        if check_similarity(fqn_of_target_method, fqn_of_method_in_kg) is True:
            simple_name_of_method_in_kg = api_dict["API_simple_name"]
            simple_name_of_method_in_kg = simple_name_of_method_in_kg.replace(" ", "")
            subclass_list = api_dict["inheritance"]
            if fqn_of_target_method in [f"{subclass}.{simple_name_of_method_in_kg}"for subclass in subclass_list]:
                return api_dict

    return None

def check_similarity(method_1: str, method_2: str) -> bool:
    """
    Check if the substrings from the start to the last index of '.' before '(' in the input methods are similar.

    :param method_1: The first input method name to compare.
    :param method_2: The second input method name to compare.
    :return: True if the substrings are similar, otherwise False.
    """
    # Find the last index of '.' before '(' in the input strings
    idx1 = method_1.rfind('.', 0, method_1.find('('))
    idx2 = method_2.rfind('.', 0, method_2.find('('))

    # Check if the substrings after the found index are similar
    return method_1[idx1:] == method_2[idx2:]

def get_FQNs(text: str) -> [str]:
    """
    Obtain a list of Fully Qualified Names from the response by checker
    :param text: checker-gpt's response
    :return: a list of FQNs
    """
    split_text = text.split("\n")
    fqn_list = []
    for fqn in split_text:
        m = re.search("`(.+?)`", fqn)
        if m:
            found = m.group(1)
            found = found.replace(" ", "")
            fqn_list.append(found)

    return fqn_list

# log each question/prompt with its response into a log file
def log_QnA(file: str, prompt: str, response: str):
    with open(file, "a+") as f:
        f.write(f"{prompt}\n")
        f.write(f"{response}\n")
        f.write("------------------------------------------------------\n")

def log_stats(file: str, invalid_mtd_list: [str], deprecated_list: [str], loop_count: int):
    stat_dict = {"loop_count": loop_count, "invalid_mtd_list": invalid_mtd_list, "num_of_invalid": len(invalid_mtd_list), "deprecated_list": deprecated_list, "num_of_deprecated": len(deprecated_list)}
    # Open a file in write mode
    with open(file, "a+") as outfile:
        # Write the dictionary object to the file in JSON format
        json.dump(stat_dict, outfile)
        outfile.write("\n")

def log_permission_stats(file: str, task_id: str, permission_declared: [str], permission_missing: [str]):
    stat_dict = {"task_id": task_id, "permission_declared": permission_declared, "permission_missing": permission_missing}
    # Open file in append mode
    with open(file, "a+") as outfile:
        # Write dictionary object to file with a new line
        json.dump(stat_dict, outfile)
        outfile.write("\n")

def read_permission_log_from_file(filename):
    # Open file in read mode
    with open(filename, "r") as infile:
        # Read file contents into a list
        contents = infile.readlines()

    # Initialize an empty list to store dictionary objects
    permission_log_list = []

    # Iterate over the list of file contents
    for line in contents:
        # Load the JSON string into a dictionary object and append to the list
        permission_log_list.append(json.loads(line))

    # Return the list of dictionary objects
    return permission_log_list

def record_completed_task_id(file: str, task_id: str):
    with open(file, "a+") as f:
        f.write(task_id + "\n")

def record_error_task_id(file: str, task_id: str):
    with open(file, "a+") as f:
        f.write(task_id + "\n")

def get_completed_task_id(file: str) -> [str]:
    with open(file, "r") as file:
        lines = file.readlines()
    # Remove newline characters at the end of each line, if needed
    completed_task_id = [line.strip() for line in lines]
    return completed_task_id

def get_error_task_id(file: str) -> [str]:
    with open(file, "r") as file:
        lines = file.readlines()
    # Remove newline characters at the end of each line, if needed
    error_task_id = [line.strip() for line in lines]
    error_task_id = list(set(error_task_id))
    return error_task_id

# read previous generated response from log txt
# response is appropriately cleaned and preprocessed, ready to manually add into GPT's conversation
# def read_previous_response_from_txt(filename: str) -> str:
#     with open(filename, "r") as file:
#         previous_response = file.readlines()[1:]
#         previous_response = " ".join(str(x) for x in previous_response)
#         previous_response = previous_response.replace("------------------------------------------------------\n", "")
#     return previous_response
def read_previous_response_from_txt(filename: str) -> str:
    with open(filename, "r") as file:
        lines = file.readlines()
        end_index = lines.index("------------------------------------------------------\n")
        previous_response = " ".join(str(x) for x in lines[1:end_index])
    return previous_response

def read_KG(kg_json: str) -> [dict]:
    """
    Read the json file containing Knowledge Graph
    :param kg_json: json file
    :return: a list of dictionary of API knowledge
    """
    with open(kg_json, "r") as j:
        kg = json.loads(j.read())
    return kg

def combine_all_exceptions_to_add_in_one_big_prompt(excpt_to_add_list: [str]) -> str:
    """
    Aggregate all individual exceptions checking/adding prompt into one single large prompt
    :param excpt_to_add_list: list containing the exceptions to handle
    :return: a large string that contains all the exceptions prompt
    """
    all_exceptions_to_add_in_one_prompt = ""
    for excpt_to_add in excpt_to_add_list:
        all_exceptions_to_add_in_one_prompt = all_exceptions_to_add_in_one_prompt + excpt_to_add + "\n"
    all_exceptions_to_add_in_one_prompt = all_exceptions_to_add_in_one_prompt.rstrip()
    return all_exceptions_to_add_in_one_prompt

def combine_all_invalid_deprecated_to_change_in_one_big_prompt(invalid_mtd_list: [str], deprecated_mtd_list: [(str, str)]) -> str:
    """
    Combine a list of invalid methods and a list of deprecated methods, along with their alternative options,
    into one big prompt.
    :param invalid_mtd_list: A list of invalid method names as strings.
    :param deprecated_mtd_list: A list of tuples where the first element is the deprecated method name as a string,
    and the second element is a list of alternative method names as strings.
    :return: A string containing a prompt that summarizes all the invalid and deprecated methods along with their
    alternative options.
    """
    all_invalid_deprecated_prompt = ""
    for invalid_mtd in invalid_mtd_list:
        prompt = f"{invalid_mtd} is not a valid API in Android."
        all_invalid_deprecated_prompt = all_invalid_deprecated_prompt + prompt + "\n"
    for deprecated_mtd, alternative_list in deprecated_mtd_list:
        alternative_options = ""
        for alternative in alternative_list:
            alternative_options = alternative_options + f"{alternative} or "
        alternative_options = alternative_options.rstrip()
        alternative_options = alternative_options[:-2]
        prompt = f"{deprecated_mtd} is deprecated. Try use {alternative_options}"
        all_invalid_deprecated_prompt = all_invalid_deprecated_prompt + prompt + "\n"
    all_invalid_deprecated_prompt = all_invalid_deprecated_prompt + "Rewrite the code you provided."
    all_invalid_deprecated_prompt = all_invalid_deprecated_prompt.rstrip()
    return all_invalid_deprecated_prompt

def combine_all_permissions_to_add_in_one_big_prompt(method_with_permission_to_declare: [dict], permission_declared_list: [str]) -> tuple[str, list[Any]]:
    all_permissions_to_add_prompt = ""
    permission_to_add_list = []

    permission_names = [permission.split(".")[-1] for permission in permission_declared_list]

    for mtd in method_with_permission_to_declare:
        mtd_fqn = mtd["API_name"]
        permission_list = mtd["API_permission"]
        if permission_list is not None and permission_list:
            for permission in permission_list:
                permission_name = permission.rsplit(".", 1)[-1]
                if permission_name in permission_names:
                    continue
                prompt = f"Check and add {permission} for {mtd_fqn} in the AndroidManifest.xml\n"
                all_permissions_to_add_prompt = all_permissions_to_add_prompt + prompt
                permission_to_add_list.append(permission)

    all_permissions_to_add_prompt = all_permissions_to_add_prompt.rstrip()
    return all_permissions_to_add_prompt, permission_to_add_list

def random_sample_to_txt(task_list: [str], n: int):
    """
    Randomly sample n tasks from task list
    :param task_list: list containing all the tasks
    :param n: sample size
    :return: randomly sampled tasks in a txt
    """
    sampled_tasks = random.sample(task_list, n)

    with open(os.getcwd() + f"/android_{n}_random_tasks.txt", "w+") as f:
        for line in sampled_tasks:
            f.write(f"{line}\n")

def read_tasks_from_txt(filename: str) -> [str]:
    with open(filename) as file:
        tasks = [line.rstrip() for line in file]
    return tasks

def get_task(task: str) -> tuple[Union[str, Any], Union[str, Any], Union[str, Any]]:
    task_information = re.split(r'\t+', task)
    id = task_information[0]
    task = task_information[1]
    method = task_information[2]

    return id, task, method

def extract_permission_strings(text: str) -> [str]:
    """
    Extracts permission strings from a given text that match the formats 'Manifest.permission.[permission_name]'
    and '[package_name].permission.[permission_name]'.

    Args:
        text (str): The text to extract permission strings from.

    Returns:
        list: A list of permission strings that match the regular expression pattern in the input text.
    """
    regex = r"(([a-zA-Z_]+\.)?permission\.[a-zA-Z_]+)"
    permission_strings = [m.group(0) for m in re.finditer(regex, text)]
    return permission_strings

def extract_method_names(text):
    """
    Extracts fully qualified method names from a given text that match the format '[package_name].[class_name].[method_name]([argument_types])'.

    Args:
        text (str): The text to extract method names from.

    Returns:
        list: A list of fully qualified method names that match the regular expression pattern in the input text.
    """
    pattern = r'\b[a-z]+(\.[a-zA-Z]+)+\([a-zA-Z\.\[\]\?\s,<>]*\)'
    # methods = re.findall(pattern, text)
    methods = re.finditer(pattern, text)
    methods = [m.group() for m in methods]
    return methods

def extract_parameters(s: str):
    # Find the index of the first occurrence of '(' and ')'
    start_idx = s.find("(")
    end_idx = s.find(")")

    # Extract the string between '(' and ')'
    params_str = s[start_idx + 1:end_idx]

    # Split the extracted string by ','
    params = params_str.split(",")

    return params

def compare_parameters(params1, params2):
    if len(params1) != len(params2):
        return False

    for p1, p2 in zip(params1, params2):
        # Get the substring after the last index of '.'
        p1_substring = p1.strip().split(".")[-1]
        p2_substring = p2.strip().split(".")[-1]

        if p1_substring != p2_substring:
            return False

    return True


