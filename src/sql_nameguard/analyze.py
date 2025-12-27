from .parse_sql import SQLParser
from .embed_sql import SQLEmbedder
import numpy as np
from logging import getLogger

class SQLAnalyzer:
    def __init__(self):
        self.parser = SQLParser()
        self.embedder = SQLEmbedder()
        self.logger = getLogger(__name__)

    def calculate_similarities(self, parsed_elements):
        embeddings = []
        for element in parsed_elements:
            code_embedding = self.embedder.embed(element['code'])
            alias_embedding = self.embedder.embed(element['alias'])
            embeddings.append({
                'alias': alias_embedding,
                'code': code_embedding,
                # calculate cosine similarity of code and alias embeddings
                'similarity': np.dot(code_embedding, alias_embedding) / (np.linalg.norm(code_embedding) * np.linalg.norm(alias_embedding))
            })
        return embeddings
    
    def analyze(self, sql: str, threshold: float = 0.7, log_warnings: bool = True):
        parsed_elements = self.parser.parse(sql)
        similarities = self.calculate_similarities(parsed_elements)
        
        analysis = []
        for element, sim in zip(parsed_elements, similarities):
            score = sim['similarity']
            if score < threshold and log_warnings:
                message = f"Alias '{element.get('alias')}' appears to be a poor name for the code (similarity={score:.3f})\n\ncode:\n{element.get('code')}\n"
                self.logger.warning(message)
            analysis.append({
                'alias': element.get('alias'),
                'code': element.get('code'),
                'type': element.get('type'),
                'similarity': score,
            })
        return analysis


