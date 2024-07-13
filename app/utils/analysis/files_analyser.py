import json
import os
import logging
import pandas as pd
import chardet

from pathlib import Path
from typing import List, Tuple, Dict
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


def get_sensitive_files(list_files: List[dict[str,str]]) -> dict[str, List[dict[str, str]]]:
    """Identify sensitive files using GPT
    
    return list of files {sensitiveFiles:[{"path": str, "language": str},]}
    """
    logger.debug("Loading GPT Model")
    logger.debug("Model loaded")
    sensitive_files = model.identify_sensitive_files(list_files)
    try:
        # Try to format the data in json
        sensitive_files = json.loads(str(sensitive_files))
        logger.debug("All files analysed")
        return sensitive_files
    except Exception as error:
        logger.error(f"When identifying sensitive files an error has occured (likely GPT forgetting sensitive_files key) : {error}")
        return {"sensitiveFiles": []}


def get_in_depth_file_analysis(list_files: List[dict[str,str]]) -> List[dict[str, str]]:
    """Asynchronously analyse each file with GPT to locate sensitive code
    For each file it returns a list of issues which are dict with keys:
    - lineNumber
    - comment
    - suggestion

    We have to ensure we lead an analysis on relevent files (files that are likely to contain sensitive code)
    """
    in_depth_results = []
    # Limit the number of files to 5 for testing
    list_files = list_files[:5]
    for file_data in list_files:
        logger.error(file_data)
        file_path = str(file_data.get("path"))
        try:
            with open(file_path, "r") as file:
                logger.info(f"Reading file : {file_path}")
                # Put line numbers before each line so GPT can understand the context
                content = list(
                    map(
                        lambda line: f"{line[0]}. {line[1]}" if line[1] != "" else None,
                        enumerate(file.readlines(), 1),
                    )
                )
                code = "".join([line for line in content if line is not None])
                logger.info(f"Code to analyze : {code}")
                in_depth_result = model.in_depth_analysis(
                    code, str(file_data.get("language"))
                )
                try:
                    # Try to format the data in json
                    in_depth_result = json.loads(in_depth_result)
                    # We should get something like {"issues":[]}
                except Exception as error:
                    logger.error(f"When identifying in depth file analysis an error has occured (likely GPT forgetting issues key) : {error}")
                    continue # Goes to next file
                logger.warning(f"Sensitive code found in file : {file_path}")
                logger.warning(in_depth_result)
                in_depth_result["path"] = file_path
                in_depth_results.append(in_depth_result) # Add the analysis to the list
        except Exception as error:
            logger.error(f"An error has occured for file : {file_path} : {error}")
    return in_depth_results


def format_github_url(url: str) -> str:
    """Format the URL to be used with the Github API"""
    # Make sure there is github.com in the URL
    if "github.com" not in url:
        url = f"github.com/{url}"
    # Make sure there is https:// in the URL
    if "https://" not in url:
        url = f"https://{url}"
    return url

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
    clone_dir: Path,
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
