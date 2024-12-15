import logging
from typing import List, Sequence
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
import json

logger = logging.getLogger(__name__)

class OllamaApi:
    """Class that is used to call Ollama LLM through LangChain"""

    def __init__(self) -> None:
        # Initialize Ollama chat model with llama2 (you can change the model as needed)
        self.llm = ChatOllama(model="llama2", temperature=0)

    def call(self, *, messages: Sequence[BaseMessage]) -> str:
        """Call Ollama with the given messages"""
        response = self.llm.invoke(messages)
        logger.debug(response)
        # Handle both string and list responses
        if isinstance(response.content, str):
            return response.content
        elif isinstance(response.content, list):
            # Join list elements with newlines if it's a list
            return '\n'.join(str(item) for item in response.content)
        # Convert any other type to string
        return str(response.content)

    def identify_sensitive_files(self, files: List[dict]) -> str:
        """Identify sensitive files using Ollama"""
        messages = [
            SystemMessage(content=(
                "You will be provided with a list of files paths. "
                "Your task is to identify which files are most likely to contain sensitive code, "
                "base your expectations on the path of the file. "
                "understand that a main file is a file that is likely to contain the main logic of the application "
                "those types of files are usually the most sensitive ones. "
                "remove all files which are irrelevent to the analysis "
                "sort paths from most sensitive to least sensitive "
                "Output is formatted as JSON with key sensitiveFiles containing a list of objects with keys: "
                "path, which is the path of the file containing sensitive code "
                "language, which is the programming language of the file"
            )),
            HumanMessage(content=str(files))
        ]
        return self.call(messages=messages)

    def in_depth_analysis(
        self, code: str, language: str = "python", audit_type: str = "security"
    ) -> str:
        """Analyse code in depth using Ollama"""
        if code is None or code == "":
            return ""

        if audit_type == "security":
            system_content = (
                f"You will be provided with a piece of {language} code. "
                "Your task is to check code security. "
                "If you find a possible security issue, you should provide a comment and a code suggestion to fix the issue (it must be code replacing existing one). "
                "Output is formatted as JSON with key 'issues' containing a list "
                "each entry of the list corresponds to a different issue in the code "
                "formatted as JSON objects with keys: "
                f"language, which is always {language} "
                "lineNumber, which is starting line where the issue occurs "
                "initialCode, which is the code that is causing the issue ensure to include previous and next lines which are relevant "
                "solvingCode, which is a possible solution to the issue in code "
                "comment, which is a short description of the issue "
                "suggestion, which is a description of a possible solution to the issue"
            )
        else:
            system_content = (
                f"You will be provided with a piece of {language} code. "
                "Your task is to check code reliability. "
                "If you find an unhandeled error/exception, "
                "you should provide a comment and a code suggestion to fix the issue "
                "Output is formatted as JSON with key 'issues' containing a list "
                "each entry of the list corresponds to a different issue in the code "
                "formatted as JSON objects with keys: "
                "lineNumber, which is starting line where the issue occurs "
                "initialCode, which is the code that is causing the issue ensure to include previous and next lines which are relevant "
                "solvingCode, which is a possible solution to the issue in code "
                "comment, which is a short description of the issue "
                "suggestion, which is a description of a possible solution to the issue"
            )

        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=code)
        ]
        return self.call(messages=messages)

    def identify_programming_language(self, code_sample: str) -> str:
        """Identify the programming language of a code sample"""
        messages = [
            SystemMessage(content=(
                "You will be provided with a code sample. "
                "Your task is to identify the programming language. "
                "Respond with a JSON object containing a single key 'language' "
                "with the language name in lowercase as the value. "
                "If uncertain, use empty string as the value."
            )),
            HumanMessage(content=code_sample)
        ]
        
        try:
            response = self.call(messages=messages)
            # Parse JSON response and extract language
            result = json.loads(response)
            return result.get('language', '').strip().lower()
        except Exception as error:
            logger.error(f"Error identifying programming language: {error}")
            return ""
