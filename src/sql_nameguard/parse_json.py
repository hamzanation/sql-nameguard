import json
import re


class JSONParser:
    @staticmethod
    def extract_json(text: str) -> dict:
        """Extract JSON object from a given text string."""
        json_str = re.search(r'\{.*\}', text, re.DOTALL)
        if json_str:
            try:
                return json.loads(json_str.group().replace("'", '"'))
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON format")
        else:
            return {}
