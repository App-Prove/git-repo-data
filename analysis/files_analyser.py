from pathlib import Path
from typing import List
from collections import Counter
import pandas as pd
from analysis.ML_analyser import ChatGPTApi

import logging

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


config_path = "analysis/config/supported_extensions.csv"


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


def get_file_analysis(list_files: List[dict]):
    """Asynchronously analyse each file with GPT to locate sensitive code
    
    We have to ensure we lead an analysis on relevent files (files that are likely to contain sensitive code)
    """
    logger.debug("Loading GPT Model")
    model = ChatGPTApi()
    logger.debug("Model loaded")
    for file_data in list_files:
        file_path = file_data.get("path")
        try:
            check = input(f"Type Y to analyse file else N : {file_path}")
            if check.lower() != "n":
                raise Exception("User skipped file")
            with open(file_path, "r") as file:
                logger.debug(f"Reading file : {file_path}")
                # Put line numbers before each line
                content = list(
                    map(
                        lambda line: f"{line[0]}. {line[1]}" if line[1] != "" else None,
                        enumerate(file.readlines(), 1),
                    )
                )
                logger.debug(f"Content : {content}")
                code = "".join(content)
                logger.debug(f"Code : {code}")
                yield model.call(code, file_data.get("language")), len(content)
        except Exception as error:
            logger.error(f"An error has occured for file : {file_path} : {error}")
            yield None, None
    logger.debug("All files analysed")
