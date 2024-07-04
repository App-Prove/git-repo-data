from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

response = client.chat.completions.create(
    model="gpt-3.5-turbo-0125",
    response_format={ "type": "json_object" },
    messages=[
        {"role": "system", "content": "You are a helpful assistant that is an expert at detecting mistakes in code. You give result with json format as follow {wrong_code:XX,comment:XX} "},
        {"role": "user", "content": "In this code, tell me which lines are susceptible to throw an error.\n print('Hello World')"}
    ]
)

print(response)