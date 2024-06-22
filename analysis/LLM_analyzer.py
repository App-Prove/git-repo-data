import requests
from abc import ABC, abstractmethod
import yaml
import json
import os
import logging
from openai import OpenAI

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)




    


class ChatGPTApi:
    """Class that is used to call chatgpt, you need to have your openai API key as an environemnt variable named OPENAI_API_KEY"""
    def __init__(self) -> None:
        assert os.getenv("OPENAI_API_KEY") is not None , "No API key detected, please setup your API key as an environement variable under the name OPENAI_API_KEY"
        self.client = OpenAI()
        self.message = [
            {"role": "system", "content": "You are a helpful assistant that is an expert at detecting mistakes in code."}
            ]


    def call(self, model="gpt-3.5", code=None, max_tokens=100, temperature=0.7, n=1, stop=None):
        if code is None or code == "":
            return None
        message = self.message
        message.append({"role": "user", "content": f"In this code, tell me which lines are susceptible to throw an error.\n {code} Give only :  the line number, a short comment about why it is not good"})

        response = self.client.chat.completions.create(
        model="gpt-3.5-turbo-0125",
        response_format={ "type": "json_object" },
        messages=message
        )
        return response
        # return response.choices[0].message.content
