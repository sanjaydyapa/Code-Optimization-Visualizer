import ast
import io
import re
import tokenize
from typing import Dict, List, Set

from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

ASSIGNMENT_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+?)\s*$")


def compute_lexical_tokens(source: str) -> List[str]:
    tokens: List[str] = []
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type in {tokenize.ENDMARKER, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT}:
            continue
        tokens.append(f"{tokenize.tok_name[token.type]}:{token.string}")
    return tokens


def compute_ast_summary(source: str) -> List[str]:
    tree = ast.parse(source)
    nodes = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.Assign, ast.Name, ast.Constant, ast.BinOp, ast.UnaryOp, ast.If, ast.Return, ast.Call)):
            nodes.append(type(node).__name__)
    return nodes


def normalize_expression(expression: str) -> str:
    return " ".join(expression.replace(" ", "").split())


def find_names_in_expression(expression: str) -> Set[str]:
    try:
        parsed = ast.parse(expression, mode="eval")
    except SyntaxError:
        return set()

    names: Set[str] = set()
    for node in ast.walk(parsed):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            names.add(node.id)
    return names


def evaluate_expression(expression: str, environment: Dict[str, float]) -> float | None:
    try:
        parsed = ast.parse(expression, mode="eval")
    except SyntaxError:
        return None

    def evaluate(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.Name):
            if node.id in environment:
                return float(environment[node.id])
            return None
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            value = evaluate(node.operand)
            return None if value is None else -value
        if isinstance(node, ast.BinOp):
            left = evaluate(node.left)
            right = evaluate(node.right)
            if left is None or right is None:
                return None
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                if abs(right) < 1e-9:
                    return None
                return left / right
            if isinstance(node.op, ast.Mod):
                if abs(right) < 1e-9:
                    return None
                return left % right
            return None
        return None

    result = evaluate(parsed.body)
    if result is None:
        return None
    return float(result)


def replace_constants_in_expression(expression: str, environment: Dict[str, float]) -> str:
    try:
        parsed = ast.parse(expression, mode="eval")
    except SyntaxError:
        return expression

    class ConstantReplacer(ast.NodeTransformer):
        def visit_Name(self, node):
            if isinstance(node.ctx, ast.Load) and node.id in environment:
                return ast.copy_location(ast.Constant(value=environment[node.id]), node)
            return node

    transformed = ConstantReplacer().visit(parsed)
    return ast.unparse(transformed)


def fold_constants(line: str, environment: Dict[str, float]) -> tuple[str, str | None]:
    match = ASSIGNMENT_RE.match(line)
    if not match:
        return line, None

    lhs, rhs = match.groups()
    folded_value = evaluate_expression(rhs, environment)
    if folded_value is None:
        return line, None

    new_line = f"{lhs} = {int(folded_value) if folded_value.is_integer() else folded_value}"
    return new_line, f"Constant folding: {rhs} became {new_line.split('= ', 1)[1]}"


def propagate_constants(line: str, environment: Dict[str, float]) -> tuple[str, str | None]:
    match = ASSIGNMENT_RE.match(line)
    if not match:
        return line, None

    lhs, rhs = match.groups()
    substituted = replace_constants_in_expression(rhs, environment)
    if substituted == rhs:
        return line, None

    new_line = f"{lhs} = {substituted}"
    return new_line, f"Constant propagation: replaced names inside {rhs} with literal values"


def remove_dead_code(lines: List[str]) -> tuple[List[str], List[str]]:
    forward_reads: set[str] = set()
    for line in lines:
        if "=" not in line:
            forward_reads |= find_names_in_expression(line)

    live_lines: List[str] = []
    steps: List[str] = []
    for index, line in enumerate(lines):
        match = ASSIGNMENT_RE.match(line)
        if not match:
            live_lines.append(line)
            continue

        lhs, rhs = match.groups()
        later_reads = set()
        for later_line in lines[index + 1:]:
            later_reads |= find_names_in_expression(later_line.replace("=", " "))

        # Preserve the final assignment in a straight-line snippet: it is
        # commonly the observable result even when no later statement reads it.
        is_final_assignment = index == len(lines) - 1
        if lhs in later_reads or is_final_assignment:
            live_lines.append(line)
        else:
            steps.append(f"Dead code elimination: removed {line} because {lhs} is never read later.")

    return live_lines, steps


def common_subexpression_elimination(lines: List[str]) -> tuple[List[str], List[str]]:
    seen: Dict[str, str] = {}
    transformed: List[str] = []
    steps: List[str] = []

    for line in lines:
        match = ASSIGNMENT_RE.match(line)
        if not match:
            transformed.append(line)
            continue

        lhs, rhs = match.groups()
        normalized = normalize_expression(rhs)
        if normalized in seen:
            reused = seen[normalized]
            transformed.append(f"{lhs} = {reused}")
            steps.append(f"Common subexpression elimination: re-used {reused} for {lhs} instead of recalculating {rhs}.")
        else:
            seen[normalized] = lhs
            transformed.append(line)

    return transformed, steps


def optimize_code(code: str, optimizations: List[str]) -> Dict[str, object]:
    lines: List[str] = [line.rstrip() for line in code.splitlines() if line.strip()]
    steps: List[str] = []

    if not lines:
        return {
            "original_code": "",
            "optimized_code": "",
            "steps": ["No valid statements were provided for optimization."],
            "lexical_tokens": [],
            "ast_summary": [],
            "syntax_tree": "",
            "pipeline": [],
            "summary": "No input code was supplied.",
        }

    if "constant_folding" in optimizations:
        working_lines: List[str] = []
        environment: Dict[str, float] = {}
        for line in lines:
            match = ASSIGNMENT_RE.match(line)
            if not match:
                working_lines.append(line)
                continue

            lhs, rhs = match.groups()
            folded_value = evaluate_expression(rhs, environment)
            if folded_value is not None:
                value = int(folded_value) if folded_value.is_integer() else folded_value
                new_line = f"{lhs} = {value}"
                environment[lhs] = float(value)
                working_lines.append(new_line)
                steps.append(f"Constant folding: {line} became {new_line}.")
            else:
                environment[lhs] = float('nan')
                working_lines.append(line)
        lines = working_lines

    if "constant_propagation" in optimizations:
        working_lines: List[str] = []
        environment: Dict[str, float] = {}
        for line in lines:
            match = ASSIGNMENT_RE.match(line)
            if not match:
                working_lines.append(line)
                continue

            lhs, rhs = match.groups()
            propagated = replace_constants_in_expression(rhs, environment)
            if propagated != rhs:
                steps.append(f"Constant propagation: {rhs} was rewritten to {propagated}.")
                line = f"{lhs} = {propagated}"
            working_lines.append(line)

            try:
                evaluated = evaluate_expression(rhs, environment)
            except Exception:
                evaluated = None
            if evaluated is not None:
                environment[lhs] = evaluated
        lines = working_lines

    if "dead_code_elimination" in optimizations:
        lines, dead_steps = remove_dead_code(lines)
        steps.extend(dead_steps)

    if "common_subexpression_elimination" in optimizations:
        lines, cse_steps = common_subexpression_elimination(lines)
        steps.extend(cse_steps)

    optimized_code = "\n".join(lines)
    source = "\n".join([line.rstrip() for line in code.splitlines() if line.strip()])
    lexical_tokens = compute_lexical_tokens(source)
    ast_summary = compute_ast_summary(source)

    syntax_tree = ast.dump(ast.parse(source), include_attributes=False)
    final_summary = (
        f"Applied {len(optimizations)} optimization pass(es) to {len(lines)} executable statement(s). "
        f"The transformed output highlights constant simplification, propagation, removal of unused assignments, and repeated expression reuse."
    )

    pipeline = [
        {"name": "Lexical analysis", "value": f"Detected {len(lexical_tokens)} tokens."},
        {"name": "Syntax analysis", "value": "The code was parsed successfully into an AST."},
        {"name": "AST generation", "value": f"Generated {len(ast_summary)} AST nodes."},
        {"name": "Optimizations", "value": ", ".join(optimizations) or "None selected"},
    ]

    return {
        "original_code": source,
        "optimized_code": optimized_code,
        "steps": steps,
        "lexical_tokens": lexical_tokens,
        "ast_summary": ast_summary,
        "syntax_tree": syntax_tree,
        "pipeline": pipeline,
        "summary": final_summary,
    }


@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"})


@app.route("/api/analyze", methods=["POST"])
def analyze():
    payload = request.get_json(silent=True) or {}
    source = payload.get("source", "")
    optimizations = payload.get("optimizations", [])
    result = optimize_code(source, optimizations)
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

#new 