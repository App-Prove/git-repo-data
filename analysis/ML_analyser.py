import os
import logging
from openai import OpenAI
from typing import List

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ChatGPTApi:
    """Class that is used to call chatgpt, you need to have your openai API key as an environemnt variable named OPENAI_API_KEY"""

    def __init__(self) -> None:
        assert (
            os.getenv("OPENAI_API_KEY") is not None
        ), "No API key detected, please setup your API key as an environement variable under the name OPENAI_API_KEY"
        self.client = OpenAI()

    def call(self, code=None, language="python"):
        if code is None or code == "":
            return None
        message = [
            {
                "role": "system",
                "content": "You are a helpful assistant that is an expert at detecting mistakes in code. You give result with json format as follow [{line_number:XX,comment:XX},] ",
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
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            response_format={"type": "json_object"},
            messages=message,
        )
        logger.debug(response)
        return response
        # return response.choices[0].message.content

    def call_on_list(self, code_list: List[str]):
        for code in code_list:
            yield self.call(code)

    def identify_relevent_files(self, files: List[str]):

        return self.call_on_list(files)