# SQL NameGuard

A sophisticated tool for evaluating and improving SQL aliases for Common Table Expressions (CTEs), tables, and columns using semantic analysis and LLM-powered suggestions.

## Overview

SQL NameGuard analyzes SQL queries to identify poorly named aliases and provides intelligent suggestions for better names. It combines:

- **Semantic Analysis**: Uses sentence transformers to embed SQL code and aliases, calculating similarity scores
- **LLM Integration**: Leverages large language models (via LiteLLM) to generate context-aware alias suggestions
- **Multi-element Support**: Handles CTEs, table aliases, and column aliases

## Features

- 🔍 **Alias Quality Analysis**: Detects aliases that don't semantically match their SQL code
- 🤖 **LLM-Powered Suggestions**: Generates multiple ranked alias recommendations
- 📊 **Similarity Scoring**: Quantifies the semantic relationship between aliases and code
- 🎯 **Flexible Threshold Configuration**: Customize sensitivity for alias evaluation
- 🧪 **Comprehensive Testing**: Full unit and integration test coverage

## Project Structure

```
sql-cte-suggestion-human/
├── src/
│   └── sql_nameguard/
│       ├── __init__.py
│       ├── analyze.py           # Core analyzer for alias quality
│       ├── embed_sql.py         # SQL embedding functionality
│       ├── llm_suggest.py       # LLM integration for suggestions
│       ├── parse_json.py        # JSON response parsing
│       └── parse_sql.py         # SQL parsing utilities
├── pyproject.toml               # Poetry project configuration
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables (API keys)
└── README.md                    # This file
```

## Installation

### Using Poetry (Recommended)

```bash
# Install poetry if you don't have it
curl -sSL https://install.python-poetry.org | python3 -

# Install project and dependencies
poetry install
```

### Using pip

```bash
pip install -r requirements.txt
```

### Development Setup

```bash
# Install with dev dependencies
poetry install --with dev

# Or with pip
pip install -r requirements.txt
```

## Configuration

### Environment Variables

Create a `.env` file in the project root with your API keys:

```env
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
ANTHROPIC_API_KEY=sk-ant-...
```

The project supports multiple LLM providers through LiteLLM. Configure the model and API key when initializing `LLMSuggester`.

## Usage

### Basic Analysis

```python
from sql_nameguard.analyze import SQLAnalyzer

# Initialize analyzer
analyzer = SQLAnalyzer()

# Analyze SQL query
sql_query = """
WITH user_activity AS (
    SELECT user_id, COUNT(*) as cnt
    FROM events
    GROUP BY user_id
)
SELECT * FROM user_activity
"""

# Get analysis results
results = analyzer.analyze(sql_query, threshold=0.7)

for issue in results:
    print(f"Alias: {issue['alias']}")
    print(f"Code: {issue['code']}")
    print(f"Similarity Score: {issue['similarity']:.3f}")
    print(f"Message: {issue['message']}")
```

### Getting Suggestions from LLM

```python
from sql_nameguard.llm_suggest import LLMSuggester
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize suggester with API key from .env
suggester = LLMSuggester(
    model="openai/gpt-3.5-turbo",
    api_key=os.getenv('OPENAI_API_KEY')
)

# Get alias suggestions
code = "SELECT COUNT(*) as cnt, status FROM orders GROUP BY status"
suggestions = suggester.suggest_cte(
    alias_type="CTE",
    code=code
)

print(suggestions['response_object'])
# Output: {'suggested_alias1': '...', 'suggested_alias2': '...', ...}
```

### Parsing SQL

```python
from sql_nameguard.parse_sql import SQLParser

parser = SQLParser()
sql = "WITH data AS (SELECT * FROM users) SELECT * FROM data"

parsed_elements = parser.parse(sql)
# Returns: [
#   {'alias': 'data', 'type': 'CTE', 'code': 'SELECT * FROM users'},
#   ...
# ]
```

### Embedding SQL

```python
from sql_nameguard.embed_sql import SQLEmbedder

embedder = SQLEmbedder(model_name="sentence-transformers/all-MiniLM-L6-v2")

embedding = embedder.embed("SELECT * FROM users")
# Returns: numpy array of embeddings
```

## API Reference

### SQLAnalyzer

```python
class SQLAnalyzer:
    def __init__(self):
        """Initialize with SQLParser and SQLEmbedder"""
        
    def calculate_similarities(self, parsed_elements: list) -> list:
        """Calculate similarity scores between aliases and code"""
        
    def analyze(self, sql: str, threshold: float = 0.7) -> list:
        """Analyze SQL and return poorly-named aliases"""
```

### LLMSuggester

```python
class LLMSuggester:
    def __init__(self, model: str = "openai/gpt-5.1-mini", api_key: str = None):
        """Initialize with model name and API key"""
        
    def suggest_cte(self, alias_type: str, code: str) -> dict:
        """Generate alias suggestions for given code"""
```

### SQLParser

```python
class SQLParser:
    @staticmethod
    def parse(sql: str) -> list:
        """Parse SQL and extract CTEs, columns, and table aliases"""
```

### SQLEmbedder

```python
class SQLEmbedder:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """Initialize with sentence transformer model"""
        
    def embed(self, text: str) -> np.ndarray:
        """Generate embeddings for text"""
```

## Testing

### Run All Tests

```bash
# Using poetry
poetry run pytest

# Using pip
pytest
```

### Run Specific Test Suite

```bash
# Test analyzer module
pytest tests/test_analyze.py -v

# Test LLM suggester
pytest tests/test_llm_suggest.py -v
```

### Run Integration Tests

Integration tests that call the actual LLM API are marked with `@pytest.mark.integration`:

```bash
# Run only integration tests
pytest tests/test_llm_suggest.py::TestLLMSuggester::test_suggest_cte_live_api_call -v

# Run all tests except integration tests
pytest -m "not integration"
```

### Test Coverage

View test coverage report:

```bash
pytest --cov=src/sql_nameguard tests/
```

## Dependencies

### Core Dependencies

- **numpy** (^1.24.0): Numerical computing
- **sqlglot** (^19.0.0): SQL parsing and manipulation
- **sentence-transformers** (^2.2.0): Semantic embeddings
- **litellm** (^1.0.0): LLM API abstraction layer
- **transformers** (^4.30.0): Hugging Face transformers library
- **python-dotenv** (^1.0.0): Environment variable management

### Development Dependencies

- **pytest** (^7.4.0): Testing framework
- **pytest-dotenv** (^0.5.2): Pytest plugin for .env file support

## How It Works

### Analysis Pipeline

1. **SQL Parsing**: Input SQL is parsed using SQLGlot to extract CTEs, columns, and table aliases
2. **Embedding**: Both the alias and its corresponding code are embedded using sentence transformers
3. **Similarity Calculation**: Cosine similarity is computed between embeddings
4. **Filtering**: Aliases with similarity below the threshold are flagged as potential issues
5. **Suggestion**: For problematic aliases, the LLM generates better alternatives

### Similarity Scoring

The similarity score ranges from 0 to 1:
- **High (>0.7)**: Alias is semantically appropriate for the code
- **Medium (0.4-0.7)**: Alias may need review
- **Low (<0.4)**: Alias is likely a poor fit and needs renaming

## Examples

### Example 1: Detecting Poor CTE Names

```python
analyzer = SQLAnalyzer()
sql = """
WITH xyz AS (
    SELECT user_id, COUNT(*) as total_orders
    FROM orders
    WHERE status = 'completed'
    GROUP BY user_id
)
SELECT * FROM xyz
"""

results = analyzer.analyze(sql, threshold=0.8)
# Detects that 'xyz' is a poor name for order statistics CTE
```

### Example 2: Getting Multiple Suggestions

```python
suggester = LLMSuggester(api_key=os.getenv('OPENAI_API_KEY'))

code = """
SELECT 
    customer_id,
    order_count,
    total_spent,
    ROW_NUMBER() OVER (ORDER BY total_spent DESC) as rank
FROM customer_metrics
"""

suggestions = suggester.suggest_cte('column', code)
# Returns multiple ranked suggestions for better column names
```

## Troubleshooting

### API Key Issues

If you encounter API key errors:
1. Verify `.env` file exists in project root
2. Check that `OPENAI_API_KEY` is set correctly
3. Ensure API key has appropriate permissions
4. Check rate limits on your API account

### Import Errors

If you get import errors:
```bash
# Reinstall package in development mode
pip install -e .
# Or with poetry
poetry install
```

### Model Download Issues

The first time you run the embedder, it downloads the sentence-transformer model (~100MB):
```python
# This will automatically download the model
embedder = SQLEmbedder()
```

## Contributing

To contribute to this project:

1. Install development dependencies: `poetry install --with dev`
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Write tests for new functionality
4. Ensure all tests pass: `pytest`
5. Submit a pull request

## Performance Notes

- **Embedding**: Initial model load is slow; subsequent embeddings are faster
- **LLM Calls**: API calls depend on model and network speed
- **Large Queries**: SQL parsing handles complex queries but may be slow for very large files

## Future Enhancements

- [ ] Support for additional SQL dialects beyond SQLGlot defaults
- [ ] Caching layer for embeddings
- [ ] Batch processing for multiple SQL files
- [ ] Custom embedding models
- [ ] Configuration profiles for different use cases
- [ ] IDE plugins for real-time alias checking
- [ ] Web interface for analysis

## License

[Specify your license here]

## Citation

If you use SQL NameGuard in your research, please cite:

```bibtex
@software{sql_nameguard,
  title={SQL NameGuard: SQL Alias Evaluation and Suggestion Tool},
  author={Hamza, Rayan},
  year={2025},
  url={https://github.com/yourusername/sql-cte-suggestion-human}
}
```

## Acknowledgments

- SQLGlot for robust SQL parsing
- Hugging Face for sentence-transformers
- OpenAI for language model API
- LiteLLM for unified LLM interface
