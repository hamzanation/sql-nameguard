from transformers import AutoModel


class SQLEmbedder:
    def __init__(self, model_name: str = "jinaai/jina-embeddings-v2-base-code"):
        self.model = AutoModel.from_pretrained(model_name, trust_remote_code=True)

    def embed(self, text: str):
        return self.model.encode([text])[0]