from .parse_json import JSONParser
from logging import getLogger
from .llm_call import call_llm
from .llm_request import LLMRequest, Message

class LLMSuggester:
    def __init__(self, provider="openai", model: str = "gpt-5.1-mini", api_key: str = None):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.json_parser = JSONParser()
        self.logger = getLogger(__name__)

    def suggest_aliases(self,  alias_type, code) -> str:
        prompt = f"""
        You are reveiwing SQL code for proper semantics.

        Given the follwing {alias_type}, suggest a couple alias names that accurately reflects its purpose from a semantic standpoint. 
        Order them by appropriateness.
        code:
        ```
        {code}
        ```

        Return a response in JSON format like the following:
        {{
            'suggested_alias1': 'first_appropriate_alias_name',
            'suggested_alias2': 'second_appropriate_alias_name',
            'suggested_alias3': 'third_appropriate_alias_name'
        }}
        """


        request = LLMRequest(
            provider=self.provider,
            model=self.model,
            messages=[
                Message.text("user", prompt)
            ],
            max_tokens=1000,
            temperature=1
        )

        initial_message = {
            "role": "user",
            "content": prompt
        }


        response = call_llm(self.provider, request, self.api_key)

        response_text = response.strip()
        response_json = self.json_parser.extract_json(response_text)
        aliases = []
        for key, value in response_json.items():
            aliases.append(value)

        self.logger.info(f"suggested aliases: {', '.join(map(str, aliases))}")



        return_object = {
            'response_object': response_json,
            'raw_response': response_text
        }
        return return_object