from crewai.tools import BaseTool
import ast
import operator
import re

class CalculatorTool(BaseTool):
    name: str = "Calculator tool"
    description: str = (
        "Useful to perform any mathematical calculations. The input to this tool should be a mathematical expression, e.g., `200*7`."
    )

    def _run(self, operation: str) -> float:
        try:
            allowed_operators = {
                ast.Add: operator.add, ast.Sub: operator.sub,
                ast.Mult: operator.mul, ast.Div: operator.truediv,
                ast.Pow: operator.pow, ast.Mod: operator.mod,
                ast.USub: operator.neg, ast.UAdd: operator.pos,
            }
            if not re.match(r'^[0-9+\-*/().% ]+$', operation):
                raise ValueError("Invalid characters")
            tree = ast.parse(operation, mode='eval')
            def _eval_node(node):
                if isinstance(node, ast.Expression): return _eval_node(node.body)
                elif isinstance(node, ast.Constant): return node.value
                elif isinstance(node, ast.BinOp):
                    return allowed_operators[type(node.op)](_eval_node(node.left), _eval_node(node.right))
                elif isinstance(node, ast.UnaryOp):
                    return allowed_operators[type(node.op)](_eval_node(node.operand))
                else: raise ValueError("Unsupported node")
            return _eval_node(tree)
        except Exception as e:
            return f"Error: {str(e)}"
