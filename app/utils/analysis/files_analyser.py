import os
import logging
import pandas as pd
import chardet

from pathlib import Path
from typing import List, Tuple
from collections import Counter
from .ml import ChatGPTApi
from git import Repo


logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


config_path = "app/utils/analysis/config/supported_extensions.csv"

logger.debug("Loading GPT Model")
model = ChatGPTApi()
logger.debug("Model loaded")


def get_important_programming_language(list_files: List[Path]) -> pd.DataFrame:
    """Returns common extensions for the detected programming language"""
    logger.debug("No extensions detected")
    suffix_counts = Counter(map(lambda x: x.suffix, list_files))
    most_common_suffix_list = suffix_counts.most_common()
    logger.debug(f"Most common suffixes : {most_common_suffix_list}")
    df = pd.read_csv(config_path)
    # Find extensions which are in the list of supported extensions
    # Count number of file for each extension
    df["count"] = df["extension"].apply(
        lambda x: suffix_counts[x] if x in suffix_counts else 0
    )
    df = df.sort_values(by="count", ascending=False)
    # Remove extensions that are not in the list of supported extensions
    df = df[df["count"] > 0]
    logger.debug(df)
    return df


def get_relevent_files(list_files: List[dict]):
    """Identify relevent files using GPT"""
    logger.debug("Loading GPT Model")
    logger.debug("Model loaded")
    relevent_files = model.identify_relevent_files(list_files)
    logger.debug("All files analysed")
    return relevent_files


def get_in_depth_file_analysis(list_files: List[dict]):
    """Asynchronously analyse each file with GPT to locate sensitive code

    We have to ensure we lead an analysis on relevent files (files that are likely to contain sensitive code)
    """
    in_depth_results = []
    for file_data in list_files:
        logger.error(file_data)
        file_path = file_data.get("path")
        try:
            check = input(f"Type Y to analyse file else N : {file_path}")
            if check.lower() == "n":
                raise Exception("User skipped file")
            with open(file_path, "r") as file:
                logger.info(f"Reading file : {file_path}")
                # Put line numbers before each line so GPT can understand the context
                content = list(
                    map(
                        lambda line: f"{line[0]}. {line[1]}" if line[1] != "" else None,
                        enumerate(file.readlines(), 1),
                    )
                )
                logger.info(f"Content : {content}")
                code = "".join(content)
                in_depth_result = model.in_depth_analysis(
                    code, file_data.get("language")
                )
                logger.warning(f"Sensitive code found in file : {file_path}")
                logger.warning(in_depth_result)
                in_depth_results.append(in_depth_result)
        except Exception as error:
            logger.error(f"An error has occured for file : {file_path} : {error}")
    return in_depth_results


def clone_repo(repo_url, clone_dir):
    if not os.path.exists(clone_dir):
        os.makedirs(clone_dir)
    # Remove all files in the directory
    for root, dirs, files in os.walk(clone_dir, topdown=False, followlinks=True):
        for file in files:
            logger.debug(f"Removing file {file}")
            os.remove(os.path.join(root, file))
        for dir in dirs:
            logger.debug(f"Removing dir {dir}")
            os.rmdir(os.path.join(root, dir))
    # Clone the repository
    Repo.clone_from(repo_url, clone_dir)


# Function to count lines in a file
def count_lines(file_path):
    try:
        with open(file_path, "rb") as file:
            # TODO: Call GPT to identify not handled errors
            raw_data = file.read()
            result = chardet.detect(raw_data)
            encoding = result["encoding"]
            text = raw_data.decode(str(encoding))
            lines = text.splitlines()
            return len(lines)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return 0


def get_simple_repository_analysis(
    clone_dir: str | Path,
) -> Tuple[int, int, List[str], List[dict]]:
    """Analyse the repository

    - Get the list of files
    - Count number of files
    - Count number of lines
    - Identify most common extensions
    - Filter files with selected extensions

    returns number_of_files, total_line_count, most_common_programming_languages, code_which_may_throw_error
    """
    if type(clone_dir) == str:
        clone_dir = Path(clone_dir)
    list_files_paths = list(clone_dir.rglob("*.*"))
    number_of_files = len(list_files_paths)
    total_line_count = 0
    for file_path in list_files_paths:
        total_line_count += count_lines(file_path)
    important_programming_language = get_important_programming_language(
        list_files_paths
    )
    list_of_important_extensions = important_programming_language["extension"].to_list()
    # List of programming languages are going to be used for keywords
    list_of_programming_languages = important_programming_language["name"].to_list()
    logger.debug(f"Selected extensions : {list_of_important_extensions}")
    # Filter files with selected extensions
    selected_files = list(
        filter(lambda x: x.suffix in list_of_important_extensions, list_files_paths)
    )
    logger.debug(f"Selected files : {selected_files}")
    # Change list to dict with filepath and programming language as keys
    ready_for_analysis = [
        {
            "path": str(file),
            "language": important_programming_language[
                important_programming_language["extension"] == file.suffix
            ]["name"].values[0],
        }
        for file in selected_files
    ]

    return (
        number_of_files,
        total_line_count,
        list_of_programming_languages,
        ready_for_analysis,
    )
