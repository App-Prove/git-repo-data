from pathlib import Path
from typing import List
from collections import Counter
import pandas as pd
from analysis.ML_analyser import ChatGPTApi

import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


config_path = "analysis/config/supported_extensions.csv"

def get_important_extensions(list_files : List[Path] , extensions = []) -> List[str]:

    if not extensions:
        suffix_counts = Counter(map(lambda x : x.suffix ,list_files))
        most_common_suffix_list = suffix_counts.most_common()
        idx = 0
        df = pd.read_csv(config_path)
        while df[df['extension'] == most_common_suffix_list[idx][0]].shape[0] <= 0 and idx < len(most_common_suffix_list):
            idx +=1
        if idx >= len(most_common_suffix_list):
            return []
        most_common_suffix, _ = most_common_suffix_list[idx]
        language = df[df['extension'] == most_common_suffix].iloc[0]['name']
        return df[df['name'] == language]['extension'].to_list(),language
    else:
        liste = []
        for suffix in extensions:
            language = df[df['extension'] == suffix].iloc[0]['name']
            liste += df[df['name'] == language]['extension'].to_list()
        return list(set(map(lambda x : Path(x),liste))),language

def get_file_analysis(list_files : List[Path]):
    model = ChatGPTApi()
    for file in list_files:
        try:
            with open(file,'r') as f:
                content = map(lambda x : f"{x[0]} " + x[1],enumerate(f.readlines()))
                code = "".join(content)
                yield model.call(code) , len(content)
        except:
            logger.error(f"An error has occured for file : {file}")
            yield None,None