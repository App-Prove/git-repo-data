import os
import logging
from openai import OpenAI
from typing import List


logger = logging.getLogger(__name__)


class ChatGPTApi:
    """Class that is used to call chatgpt, you need to have your openai API key as an environemnt variable named OPENAI_API_KEY"""

    def __init__(self) -> None:
        assert (
            os.getenv("OPENAI_API_KEY") is not None
        ), "No API key detected, please setup your API key as an environement variable under the name OPENAI_API_KEY"
        self.client = OpenAI()

    def call(self, *, message):
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            response_format={"type": "json_object"},
            messages=message,
        )
        logger.debug(response)
        return response.choices[0].message.content

    def identify_relevent_files(self, files: List[dict]):
        """Identify relevent files using GPT"""

        message = [
            {
                "role": "system",
                "content": (
                    f"You will be provided with a list of files paths"
                    "Your task is to identify which files are most likely to contain sensitive code, base your expectations on the path of the file."
                    "Output is formatted as JSON with key sensitive_files containing a list of objects with keys:"
                    "path, which is the path of the file containing sensitive code"
                    "programming_language, which is the programming language of the file"
                ),
            },
            {
                "role":"user",
                "content": "[{'path': 'cloned_repo/main.py', 'language': 'Python'}]",
            },
            {
                "role": "assistant",
                "content": """{ "sensitive_files": [ { "path": "cloned_repo/main.py", "programming_language": "Python" } ] }"""
            },
            {
                "role": "user",
                "content": str(files),
            },
        ]
        return self.call(message=message)

    def in_depth_analysis(self, code: str, language: str = "python"):
        """Analyse code in depth using GPT"""
        if code is None or code == "":
            return None
        message = [
            {
                "role": "system",
                "content": (
                    f"You will be provided with a piece of {language} code"
                    "Your task is to check code security."
                    "If you find a possible security issue, you should provide a comment and a code suggestion to fix the issue (it must be code replacing existing one). "
                    "Answer with a list of Json outputs with keys:"
                    "line_number, which is starting line where the issue occurs"
                    "comment, which is a short description of the issue"
                    "suggestion, which is a possible solution to the issue"
                    "each entry of the list corresponds to a different issue in the code."
                ),
            },
            {
                "role": "user",
                "content": code,
            },
        ]
        return self.call(message=message)
