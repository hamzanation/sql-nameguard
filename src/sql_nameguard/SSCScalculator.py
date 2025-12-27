import sqlglot
from sqlglot import exp
from .analyze import SQLAnalyzer
from logging import getLogger


class SSCSCalculator:
    def __init__(self):
        # Configuration for weights
        self.weights = {
            exp.Join: 1,
            exp.Where: 1,
            exp.Group: 1,
            exp.Having: 1,
            exp.Order: 1,
            exp.Case: 2,           # Branching logic = higher load
            exp.Window: 2,         # Window functions are complex
            exp.Connector: 1,      # AND / OR
            exp.Subquery: 1        # Base penalty for existence of subquery
        }
        
        # Configuration for Semantic Penalty
        self.semantic_weight = 0.5  # Alpha in the formula
        self.min_alias_length = 3
        self.generic_aliases = {'temp', 'data', 't', 'x', 'val', 'obj', 'row'}
        self.analyzer = SQLAnalyzer()
        self.logger = getLogger(__name__)

    def calculate(self, sql: str, complexity_threshold: float = 15.0, similarity_threshold: float = 0.7, log_warnings: bool = True):
        """
        Parses SQL and returns the SSCS score along with a detailed breakdown.
        """
        try:
            parsed = sqlglot.parse_one(sql)
        except Exception as e:
            return {"error": f"Parse Error: {e}"}

        # 1. Isolate CTEs and Main Query
        ctes = []
        main_query = parsed

        # If there is a WITH clause, extract CTEs
        if parsed.find(exp.CTE):
            # We treat CTEs as independent "functions" for complexity
            # Note: sqlglot stores CTEs in the 'with' arg of the main expression
            ctes = parsed.find_all(exp.CTE)
                # We analyze the main query as if the CTEs are just tables
                # (The complexity of defining the CTE is handled separately)


        
        
        # 2. Calculate Structural Complexity (C_struct)
        # Sum of CTE complexities + Main Query complexity
        struct_score = 0
        component_scores = []
        sscs_scores = {}

        # Analyze CTEs (Depth starts at 0 for each, promoting modularity)
        for cte in ctes:
            cte_score = self._compute_structural_score(cte.this, depth=0)
            struct_score += cte_score
            component_scores.append(f"CTE '{cte.alias}': {cte_score}")
            cte_penalty, _ = self._compute_semantic_penalty(cte.this, similarity_threshold, log_warnings)
            cte_sscs = cte_score * (1 + cte_penalty)
            sscs_scores[cte.alias] = {
                "SSCS": round(cte_sscs, 2),
                "Structural Score": round(cte_score, 2),
                "Semantic Penalty": round(cte_penalty, 2)
            }
            if cte_sscs > complexity_threshold and log_warnings:
                self.logger.warning(f"CTE '{cte.alias}' has high SSCS score: {cte_sscs} (Threshold: {complexity_threshold})")

        # Analyze Main Query (Depth starts at 0)
        # We explicitly exclude the WITH clause from traversal to avoid double counting
        main_score = self._compute_structural_score(main_query, depth=0, exclude_node=exp.With)
        struct_score += main_score
        component_scores.append(f"Main Query: {main_score}")
        main_penalty, _ = self._compute_semantic_penalty(main_query, similarity_threshold, log_warnings)
        main_sscs = main_score * (1 + main_penalty)

        if main_sscs > complexity_threshold and log_warnings:
            self.logger.warning(f"Final SELECT has high SSCS score: {main_sscs} (Threshold: {complexity_threshold})")

        # 3. Calculate Semantic Penalty (P_sem)
        # We look at all aliases across the entire parsed tree globally
        semantic_penalty, alias_stats = self._compute_semantic_penalty(parsed, similarity_threshold, log_warnings)

        main_sscs = main_score * (1 + semantic_penalty)

        # 4. Final Formula: SSCS = C_struct * (1 + P_sem)
        final_sscs = struct_score * (1 + semantic_penalty)

        sscs_scores["final SELECT"] = {
            "SSCS": round(main_sscs, 2),
            "Structural Score": round(main_score, 2),
            "Semantic Penalty": round(semantic_penalty, 2)
        }

        sscs_scores["overall"] = {
            "SSCS": round(final_sscs, 2),
            "Structural Score": round(struct_score, 2),
            "Semantic Penalty": round(semantic_penalty, 2)
        }

        return {
            "sscs_scores": sscs_scores,
            "breakdown": component_scores,
            "alias_analysis": alias_stats
        }
    
    def _compute_structural_score(self, node, depth, exclude_node=None):
        """
        Recursive visitor to calculate complexity weights based on AST nodes.
        Increases depth penalty for nested subqueries.
        """
        score = 0
        
        # If this node is the one we want to exclude (e.g. the CTE definitions block), stop recursion
        if exclude_node and isinstance(node, exclude_node):
            return 0

        # Apply Weight if node type is in our config
        if type(node) in self.weights:
            base_weight = self.weights[type(node)]
            # Formula: Weight + Depth Penalty
            # We add depth to the weight. Deeper logic is heavier.
            score += base_weight + (0.5 * depth)

        # Check for nesting triggers
        # If we enter a Subquery (SELECT inside FROM/WHERE), increment depth
        next_depth = depth
        if isinstance(node, exp.Subquery):
            next_depth += 1
        
        # Recursively visit children
        # sqlglot's args.values() gives us lists of children or single children
        for child_list in node.args.values():
            if isinstance(child_list, list):
                for child in child_list:
                    if isinstance(child, exp.Expression):
                        score += self._compute_structural_score(child, next_depth, exclude_node)
            elif isinstance(child_list, exp.Expression):
                score += self._compute_structural_score(child_list, next_depth, exclude_node)
                
        return score
    
    def _compute_semantic_penalty(self, root_node, threshold=0.7, log_warnings: bool = True):
        """
        Uses semantic similarity analysis to compute penalty for poorly named aliases.
        
        Converts the parsed AST back to SQL, analyzes it with the SQLAnalyzer,
        and penalizes aliases with low similarity scores between the alias name
        and the code they represent.
        """
        # Convert parsed node back to SQL string for analyzer
        sql_str = root_node.sql()
        
        # Get semantic analysis from the analyzer
        analysis = self.analyzer.analyze(sql_str, threshold=threshold, log_warnings=log_warnings)
        
        if not analysis:
            return 0.0, {"total": 0, "low_similarity": [], "average_similarity": 0.0}
        
        # Calculate penalty based on similarity scores
        # Lower similarity = higher penalty
        similarities = [item['similarity'] for item in analysis]
        low_similarity_items = [item for item in analysis if item['similarity'] < threshold]
        
        # Penalty formula: average the "badness" (1 - similarity) for items below threshold
        if low_similarity_items:
            avg_badness = sum(1.0 - item['similarity'] for item in low_similarity_items) / len(analysis)
            penalty = self.semantic_weight * avg_badness
        else:
            penalty = 0.0
        
        avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0
        
        return penalty, {
            "total": len(analysis), 
            "low_similarity_count": len(low_similarity_items),
            "low_similarity_examples": [
                {
                    "alias": item['alias'], 
                    "similarity": round(item['similarity'], 3),
                    "type": item['type']
                } 
                for item in low_similarity_items[:5]
            ],
            "average_similarity": round(avg_similarity, 3)
        }