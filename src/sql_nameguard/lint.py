from .analyze import SQLAnalyzer
from .SSCScalculator import SSCSCalculator

class SQLLinter:
    @staticmethod
    def lint_aliases(sql: str, semantic_threshold: float = 0.7):
        analyzer = SQLAnalyzer()
        alias_similarities = analyzer.analyze(sql, threshold=semantic_threshold)
        return alias_similarities

    @staticmethod
    def lint_complexity(sql: str, complexity_threshold: float = 15.0, similarity_threshold: float = 0.7):
        sscs_calculator = SSCSCalculator()
        sscs_object = sscs_calculator.calculate(sql, complexity_threshold, similarity_threshold)
        return sscs_object
    
    @staticmethod
    def lint(sql: str, complexity_threshold: float = 15.0, similarity_threshold: float = 0.7):
        
        return SQLLinter.lint_complexity(sql, complexity_threshold, similarity_threshold)
