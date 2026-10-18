"""Deterministic numerical-fidelity checks (protocol §5.C).

An AI judge maps each numeric assertion in a generated text to the evidence *the text refers to*
(an arithmetic expression over evidence IDs, or a verbatim quote of package prose). Everything after that is
deterministic and lives here: resolving evidence values, evaluating the expression safely, applying unit
scale and rounding tolerance, classifying errors, and matching assertions to required numeric facts.

Evidence-value keys (all derived from the package, never from gold):
  T1.r3.avg           table cell value             T1.r3.avg.spread   the ± value shown in the cell
  S1 / S1.p_value     test p-value                 S1.statistic, S1.df, S1.n, S1.ci_low, S1.ci_high,
                                                   S1.alpha, S1.ci_level
Expressions may use + - * / (and the unicode − × ÷), parentheses, numbers, and the functions
abs, min, max, mean, sum, round, and count(<comparison>, ...) which counts true comparisons.
"""
from __future__ import annotations

import ast
import itertools
import math
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

from src.package_schema import ResearchPackage
from src.render import render_package

NUM_RE = re.compile(r"(?<![A-Za-z0-9_.])[-−+]?\d+(?:,\d{3})*(?:\.\d+)?")
ALLOWED_SCALES = (1.0, 100.0, 0.01, 1000.0, 0.001)
APPROX_REL_TOL = 0.05
TEST_FIELDS = ("p_value", "statistic", "df", "n", "ci_low", "ci_high", "alpha", "ci_level")
CORRECT = "CORRECT"
ERROR_TYPES = ("VALUE_MISMATCH", "MISATTRIBUTED", "SIGN_OR_DIRECTION", "UNIT_OR_SCALE", "ARITHMETIC",
               "STAT_MISASSOCIATION", "FABRICATED")
INVALID = "INVALID_MAPPING"
PRIMARY_ROLES = ("result", "derived", "statistical", "cited", "count_outcome")


WORD_NUMBERS = {"zero": 0, "one": 1, "single": 1, "once": 1, "two": 2, "twice": 2, "both": 2, "three": 3, "thrice": 3,
                "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
                "twelve": 12, "half": 0.5, "halved": 0.5, "double": 2, "doubled": 2, "triple": 3, "tripled": 3}
WORD_RE = re.compile(r"\b(" + "|".join(WORD_NUMBERS) + r")\b", re.I)


def numbers_in(text: str) -> list[tuple[str, float]]:
    """Digit numbers and number words in package prose, as (token, value)."""
    t = normalize_text(text)
    out = [(tok, parse_number(tok)) for tok in NUM_RE.findall(t)]
    out += [(m.group(1), float(WORD_NUMBERS[m.group(1).lower()])) for m in WORD_RE.finditer(t)]
    return [(tok, v) for tok, v in out if v is not None]


def normalize_text(s: str) -> str:
    s = (s or "").replace("`", "").replace("**", "").replace("−", "-").replace("–", "-").replace("×", "x").replace(" ", " ")
    return re.sub(r"\s+", " ", s).strip()


def decimals_of(token: str) -> int:
    token = token.strip().replace(",", "")
    m = re.search(r"\.(\d+)", token)
    return len(m.group(1)) if m else 0


def parse_number(token: str) -> Optional[float]:
    m = NUM_RE.search(normalize_text(str(token)))
    if not m:
        return None
    return float(m.group(0).replace(",", "").replace("−", "-"))


# ----------------------------------------------------------------------------- evidence values
@dataclass
class Quantity:
    value: float
    half_unit: float  # display-rounding half unit of the package value
    kind: str  # cell | spread | test
    upper_bound: bool = False  # p-value known only as "p < x"


@dataclass
class EvidenceValues:
    package: ResearchPackage
    values: dict[str, Quantity] = field(default_factory=dict)
    rendered: str = ""

    @classmethod
    def from_package(cls, pkg: ResearchPackage) -> "EvidenceValues":
        ev = cls(pkg)
        for t in pkg.results_tables:
            for r in t.rows:
                for cid, cell in r.cells.items():
                    key = f"{t.table_id}.{r.row_id}.{cid}"
                    nums = NUM_RE.findall(normalize_text(cell.text))
                    if cell.value is not None:
                        tok = next((n for n in nums if parse_number(n) is not None
                                    and math.isclose(abs(parse_number(n)), abs(cell.value), rel_tol=1e-9, abs_tol=1e-12)),
                                   nums[0] if nums else repr(cell.value))
                        ev.values[key] = Quantity(cell.value, 0.5 * 10 ** -decimals_of(tok), "cell")
                    if cell.spread is not None:
                        tok = next((n for n in nums[1:] if parse_number(n) is not None
                                    and math.isclose(abs(parse_number(n)), abs(cell.spread), rel_tol=1e-9)),
                                   repr(cell.spread))
                        ev.values[key + ".spread"] = Quantity(cell.spread, 0.5 * 10 ** -decimals_of(tok), "spread")
                    else:  # a "± x" shown in the cell text without a structured spread field
                        m = re.search(r"±\s*([0-9]+(?:\.[0-9]+)?)", cell.text)
                        if m:
                            ev.values[key + ".spread"] = Quantity(float(m.group(1)), 0.5 * 10 ** -decimals_of(m.group(1)), "spread")
        for s in pkg.statistical_tests:
            for f in TEST_FIELDS:
                v = getattr(s, f)
                if f == "p_value" and v is None and s.p_value_text:
                    m = re.search(r"<\s*=?\s*([0-9.eE-]+)", s.p_value_text)
                    if m:
                        ev.values[f"{s.test_id}.p_value"] = Quantity(float(m.group(1)), 0.0, "test", upper_bound=True)
                    continue
                if v is None:
                    continue
                tok = f"{v:g}"
                if f == "p_value" and s.p_value_text:
                    tok = next(iter(NUM_RE.findall(s.p_value_text)), tok)
                ev.values[f"{s.test_id}.{f}"] = Quantity(float(v), 0.5 * 10 ** -decimals_of(tok) if "e" not in tok else 0.0, "test")
        ev.rendered = normalize_text(render_package(pkg))
        return ev

    def resolve_key(self, key: str) -> Optional[str]:
        if key in self.values:
            return key
        if f"{key}.p_value" in self.values:  # bare test id means its p-value
            return f"{key}.p_value"
        return None

    def keys_sorted(self) -> list[str]:
        ks = set(self.values)
        ks |= {k.rsplit(".", 1)[0] for k in self.values if k.endswith(".p_value")}
        return sorted(ks, key=len, reverse=True)


# ----------------------------------------------------------------------------- safe expression evaluation
class ExpressionError(ValueError):
    pass


_FUNCS = {"abs", "min", "max", "mean", "sum", "count", "round"}


def tokenize_expression(expr: str, ev: EvidenceValues) -> tuple[str, dict[str, str]]:
    """Replace evidence keys (longest match first) by placeholder names; return (python_expr, {name: key})."""
    s = (expr or "").replace("−", "-").replace("–", "-").replace("×", "*").replace("÷", "/").replace("·", "*")
    s = re.sub(r"\s+", " ", s).strip()
    keys = ev.keys_sorted()
    out, names, i = [], {}, 0
    while i < len(s):
        hit = None
        if s[i].isalpha() and (i == 0 or not re.match(r"[A-Za-z0-9_.]", s[i - 1])):
            for k in keys:
                if s.startswith(k, i):
                    end = i + len(k)
                    if end == len(s) or not re.match(r"[A-Za-z0-9_.]", s[end]):
                        hit = k
                        break
        if hit is not None:
            resolved = ev.resolve_key(hit)
            name = next((n for n, kk in names.items() if kk == resolved), None)
            if name is None:
                name = f"_v{len(names)}"
                names[name] = resolved
            out.append(name)
            i += len(hit)
        else:
            out.append(s[i])
            i += 1
    py = "".join(out)
    # a bare "x" between operands is a multiplication sign in judge output ("100 x a")
    py = re.sub(r"(?<=[\d)\s])x(?=[\s\d(_])", "*", py)
    return py, names


def _eval(node: ast.AST, env: dict[str, float]) -> Any:
    if isinstance(node, ast.Expression):
        return _eval(node.body, env)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return float(node.value)
    if isinstance(node, ast.Name):
        if node.id not in env:
            raise ExpressionError(f"unknown identifier {node.id!r}")
        return env[node.id]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        v = _eval(node.operand, env)
        return -v if isinstance(node.op, ast.USub) else v
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
        a, b = _eval(node.left, env), _eval(node.right, env)
        if isinstance(node.op, ast.Add):
            return a + b
        if isinstance(node.op, ast.Sub):
            return a - b
        if isinstance(node.op, ast.Mult):
            return a * b
        if b == 0:
            raise ExpressionError("division by zero")
        return a / b
    if isinstance(node, ast.Compare) and len(node.ops) == 1:
        a, b = _eval(node.left, env), _eval(node.comparators[0], env)
        op = node.ops[0]
        table = {ast.Gt: a > b, ast.GtE: a >= b, ast.Lt: a < b, ast.LtE: a <= b, ast.Eq: a == b, ast.NotEq: a != b}
        for t, v in table.items():
            if isinstance(op, t):
                return bool(v)
        raise ExpressionError("unsupported comparison")
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCS and not node.keywords:
        args = [_eval(a, env) for a in node.args]
        f = node.func.id
        if f == "count":
            return float(sum(1 for a in args if a is True or (not isinstance(a, bool) and a)))
        if any(isinstance(a, bool) for a in args):
            raise ExpressionError("boolean used as a number")
        if f == "abs" and len(args) == 1:
            return abs(args[0])
        if f == "round" and len(args) in (1, 2):
            return float(round(args[0], int(args[1]) if len(args) == 2 else 0))
        if not args:
            raise ExpressionError(f"{f}() needs arguments")
        return {"min": min, "max": max, "sum": sum}.get(f, lambda xs: sum(xs) / len(xs))(args)
    raise ExpressionError(f"unsupported syntax: {ast.dump(node)[:60]}")


def evaluate(expr: str, ev: EvidenceValues, perturb: Optional[dict[str, float]] = None) -> tuple[float, dict[str, str]]:
    py, names = tokenize_expression(expr, ev)
    if not names:
        raise ExpressionError("expression references no evidence")
    try:
        tree = ast.parse(py, mode="eval")
    except SyntaxError as e:
        raise ExpressionError(f"syntax error in {py!r}") from e
    env = {n: ev.values[k].value + (perturb or {}).get(n, 0.0) for n, k in names.items()}
    val = _eval(tree, env)
    if isinstance(val, bool):
        raise ExpressionError("expression is a comparison, not a quantity")
    return float(val), names


def package_tolerance(expr: str, ev: EvidenceValues, max_operands: int = 10) -> float:
    """Largest change of the expression when each operand moves within its display-rounding half unit."""
    center, names = evaluate(expr, ev)
    halves = {n: ev.values[k].half_unit for n, k in names.items()}
    active = [n for n, h in halves.items() if h > 0]
    if not active:
        return 0.0
    if len(active) > max_operands:
        return 0.0
    worst = 0.0
    for signs in itertools.product((-1.0, 1.0), repeat=len(active)):
        try:
            v, _ = evaluate(expr, ev, {n: s * halves[n] for n, s in zip(active, signs)})
        except ExpressionError:
            continue
        worst = max(worst, abs(v - center))
    return worst


# ----------------------------------------------------------------------------- assertion checking
@dataclass
class Assertion:
    as_written: str
    value: float
    approximate: bool = False
    role: str = "result"
    unit: Optional[str] = None


@dataclass
class Mapping:
    source_type: str  # cell | test | text | none
    expression: Optional[str] = None
    quote: Optional[str] = None
    scale: float = 1.0
    comparator: str = "="


@dataclass
class Verdict:
    status: str  # CORRECT, one of ERROR_TYPES, or INVALID_MAPPING
    expected: Optional[float] = None  # in text units
    tolerance: Optional[float] = None
    operands: tuple[str, ...] = ()
    note: str = ""

    @property
    def correct(self) -> bool:
        return self.status == CORRECT

    @property
    def is_error(self) -> bool:
        return self.status in ERROR_TYPES


def asserted_tolerance(a: Assertion, expected: float) -> float:
    tol = 0.5 * 10 ** -decimals_of(a.as_written)
    if a.approximate:
        tol += APPROX_REL_TOL * abs(expected)
    return tol + 1e-9


def _compare(a: float, comparator: str, expected: float, tol: float, upper_bound: bool) -> bool:
    if upper_bound:  # package only says p < expected
        # an exact or lower-bound statement cannot be verified from "p < x"
        return comparator in ("<", "<=") and expected <= a + tol
    if comparator == "=":
        return abs(a - expected) <= tol
    if comparator == "<":
        return expected < a + tol
    if comparator == "<=":
        return expected <= a + tol
    if comparator == ">":
        return expected > a - tol
    if comparator == ">=":
        return expected >= a - tol
    return False


def _cell_parts(key: str) -> Optional[tuple[str, str, str]]:
    parts = key.split(".")
    return (parts[0], parts[1], parts[2]) if len(parts) == 3 else None


def plausible_alternatives(operands: tuple[str, ...], derived: bool, ev: EvidenceValues) -> list[tuple[str, float]]:
    """Quantities a misattributed number plausibly came from, given what the text refers to.

    Direct lookups: another cell in the same row or column of the same table, or any test value.
    Two-cell comparisons along one column (method A vs B on a metric): the same two rows on another
    column, or another pair of rows on the same column; along one row: the transposed alternatives.
    Anything more complex has no plausible alternative set (an error there is classed as ARITHMETIC)."""
    cells = [c for c in (_cell_parts(o) for o in operands) if c]
    out: list[tuple[str, float]] = []

    def val(t: str, r: str, c: str) -> Optional[float]:
        q = ev.values.get(f"{t}.{r}.{c}")
        return q.value if q else None

    tables = {t.table_id: t for t in ev.package.results_tables}
    if not derived and len(cells) == 1:
        t, r, c = cells[0]
        tab = tables.get(t)
        if tab:
            for row in tab.rows:
                for col in row.cells:
                    if (row.row_id == r) != (col == c) and (v := val(t, row.row_id, col)) is not None:
                        out.append((f"{t}.{row.row_id}.{col}", v))
        out += [(k, q.value) for k, q in ev.values.items() if q.kind == "test"]
        return out
    if not derived or len(cells) != 2 or len(operands) != 2 or cells[0][0] != cells[1][0]:
        return out
    (t, r1, c1), (_, r2, c2) = cells
    tab = tables.get(t)
    if tab is None:
        return out
    pairs: list[tuple[tuple[str, str], tuple[str, str]]] = []
    if c1 == c2 and r1 != r2:
        cols = {col for row in tab.rows for col in row.cells}
        rows = [row.row_id for row in tab.rows]
        pairs += [((r1, x), (r2, x)) for x in cols if x != c1]
        pairs += [((a, c1), (b, c1)) for a in rows for b in rows if a != b and {a, b} != {r1, r2}]
    elif r1 == r2 and c1 != c2:
        cols = sorted({col for row in tab.rows for col in row.cells})
        pairs += [((y, c1), (y, c2)) for y in (row.row_id for row in tab.rows) if y != r1]
        pairs += [((r1, a), (r1, b)) for a in cols for b in cols if a != b and {a, b} != {c1, c2}]
    for (ra, ca), (rb, cb) in pairs:
        a, b = val(t, ra, ca), val(t, rb, cb)
        if a is None or b is None:
            continue
        x, y = f"{t}.{ra}.{ca}", f"{t}.{rb}.{cb}"
        out += [(f"{x} - {y}", a - b), (f"{y} - {x}", b - a)]
        if b:
            out += [(f"{x} / {y}", a / b), (f"({x} - {y}) / {y} * 100", (a - b) / b * 100)]
        if a:
            out += [(f"{y} / {x}", b / a), (f"({y} - {x}) / {x} * 100", (b - a) / a * 100)]
    return out


def _first_match(a: float, cands: list[tuple[str, float]], tol: float, exclude: Iterable[float] = ()) -> Optional[str]:
    excl = list(exclude)
    for key, v in cands:
        if any(abs(v - e) <= 1e-12 for e in excl):
            continue
        if abs(a - v) <= tol:
            return key
    return None


def _anywhere(a: float, ev: EvidenceValues, tol: float) -> Optional[str]:
    """Used only when the judge found no referenced source: does the value occur as any evidence value?"""
    for k, q in ev.values.items():
        for scale in (1.0, 100.0, 0.01):
            if abs(a - q.value * scale) <= tol:
                return k
    return None


def check_assertion(a: Assertion, m: Mapping, ev: EvidenceValues) -> Verdict:
    scale = float(m.scale or 1.0)
    if not any(math.isclose(scale, s) for s in ALLOWED_SCALES):
        return Verdict(INVALID, note=f"scale {scale} not allowed")
    comparator = (m.comparator or "=").replace("≤", "<=").replace("≥", ">=")
    if comparator not in ("=", "<", "<=", ">", ">="):
        return Verdict(INVALID, note=f"bad comparator {comparator}")
    st = (m.source_type or "").lower()
    if st == "none":
        tol = asserted_tolerance(a, a.value)
        where = _anywhere(a.value, ev, tol)
        if where:
            return Verdict("MISATTRIBUTED", note=f"value occurs at {where}, not at the referenced evidence")
        if normalize_text(a.as_written) and _number_in_rendered(a, ev):
            return Verdict("MISATTRIBUTED", note="value occurs in package prose, not at the referenced evidence")
        return Verdict("FABRICATED", note="no source in the package")
    if st == "text":
        q = normalize_text(m.quote or "")
        if not q or q not in ev.rendered:
            return Verdict(INVALID, note="quote not found verbatim in the package")
        found = numbers_in(q)
        if not found:  # e.g. "a single dataset" mapped to prose that names one dataset: not checkable
            return Verdict(INVALID, note="quote contains no number to check against")
        for tok, n in found:
            exp = n * scale
            tol = asserted_tolerance(a, exp)
            if _compare(a.value, comparator, exp, tol, False):
                return Verdict(CORRECT, exp, tol, (), "matched quoted prose")
        states_a_count = any(v == int(v) and 0 <= v <= 20 for _, v in found)
        if not re.search(r"\d", a.as_written) and not states_a_count:
            # a count written as a word ("a single dataset") whose quote never states that number: an implicit
            # count cannot be checked deterministically (the judges' qualitative label still covers the claim)
            return Verdict(INVALID, note="implicit count: quoted prose does not state the number")
        return Verdict("VALUE_MISMATCH", note="no number in the quote matches")
    if st not in ("cell", "test"):
        return Verdict(INVALID, note=f"unknown source_type {m.source_type!r}")
    if not m.expression:
        return Verdict(INVALID, note="missing expression")
    try:
        raw, names = evaluate(m.expression, ev)
    except (ExpressionError, KeyError) as e:
        return Verdict(INVALID, note=str(e))
    operands = tuple(sorted(names.values()))
    upper = len(names) == 1 and ev.values[next(iter(names.values()))].upper_bound
    expected = raw * scale
    # package values are treated as exact as displayed (they are the evidence the writer saw); the tolerance
    # is the rounding of the asserted number, widened for explicitly approximate wording
    tol = asserted_tolerance(a, expected)
    if _compare(a.value, comparator, expected, tol, upper):
        return Verdict(CORRECT, expected, tol, operands)
    if comparator != "=":
        return Verdict("VALUE_MISMATCH", expected, tol, operands, "bound not satisfied")
    if expected != 0 and abs(a.value + expected) <= tol:
        return Verdict("SIGN_OR_DIRECTION", expected, tol, operands)
    for k in (100.0, 0.01, 1000.0, 0.001):
        if abs(a.value - expected * k) <= tol * k and not math.isclose(k, 1.0):
            return Verdict("UNIT_OR_SCALE", expected, tol, operands, f"off by factor {k:g}")
    py, _ = tokenize_expression(m.expression, ev)
    derived = len(names) > 1 or bool(re.search(r"[-+*/]|\b(abs|min|max|mean|sum|count|round)\(", py))
    if a.role == "statistical" or st == "test":
        tests = [(k, q.value) for k, q in ev.values.items() if q.kind == "test"]
        where = _first_match(a.value / scale, tests, tol / abs(scale), exclude=[raw])
        if where:
            return Verdict("STAT_MISASSOCIATION", expected, tol, operands, f"value belongs to {where}")
    where = _first_match(a.value / scale, plausible_alternatives(operands, derived, ev), tol / abs(scale), exclude=[raw])
    if where:
        return Verdict("MISATTRIBUTED", expected, tol, operands, f"value matches {where}")
    if derived:
        return Verdict("ARITHMETIC", expected, tol, operands)
    return Verdict("VALUE_MISMATCH", expected, tol, operands)


def _number_in_rendered(a: Assertion, ev: EvidenceValues) -> bool:
    for tok in NUM_RE.findall(ev.rendered):
        n = parse_number(tok)
        if n is not None and abs(n - a.value) <= 0.5 * 10 ** -decimals_of(a.as_written) + 1e-12 and abs(a.value) >= 1:
            return True
    return False


# ----------------------------------------------------------------------------- required numeric facts
ID_IN_TEXT = re.compile(r"\b[A-Z][A-Za-z0-9_\-]*\.[A-Za-z][A-Za-z0-9_\-]*\.[A-Za-z][A-Za-z0-9_\-]*\b|\b[S][0-9]+\b")


@dataclass
class RequiredFact:
    fact_id: str
    value: float  # in package units
    tolerance: float
    operands: Optional[frozenset[str]]  # resolved evidence keys; None if not determinable
    signed_difference: bool = True
    description: str = ""


def gold_fact(f: dict[str, Any], ev: EvidenceValues) -> RequiredFact:
    """Normalise a synthetic-gold numeric fact (evidence_id or derivation string) to resolved operands."""
    ops: Optional[set[str]] = None
    eid = f.get("evidence_id")
    if eid and eid != "derived":
        k = ev.resolve_key(eid)
        ops = {k} if k else None
    else:
        lhs = (f.get("derivation") or "").split("=")[0]
        ids = [ev.resolve_key(x) for x in ID_IN_TEXT.findall(lhs)]
        if ids and all(ids):
            ops = set(ids)  # type: ignore[arg-type]
        else:  # derivation written with numbers: map each number to a unique cell with that value
            nums = [parse_number(t) for t in NUM_RE.findall(normalize_text(lhs))]
            found: set[str] = set()
            for n in nums:
                if n is None or n in (100.0,):
                    continue
                hits = [k for k, q in ev.values.items() if q.kind == "cell" and math.isclose(q.value, n, abs_tol=1e-9)]
                if len(hits) == 1:
                    found.add(hits[0])
            ops = found or None
    return RequiredFact(f["fact_id"], float(f["value"]), float(f.get("tolerance") or 0.0),
                        frozenset(ops) if ops else None, True, f.get("description", ""))


def fact_from_expression(fact_id: str, expression: str, ev: EvidenceValues, description: str = "") -> RequiredFact:
    val, names = evaluate(expression, ev)
    tol = package_tolerance(expression, ev) + 1e-9
    return RequiredFact(fact_id, val, tol, frozenset(names.values()), True, description)


def fact_reported(fact: RequiredFact, checked: list[tuple[Assertion, Mapping, Verdict]]) -> bool:
    """A required fact is reported iff some CORRECT assertion refers to the same operands and value."""
    for a, m, v in checked:
        if not v.correct:
            continue
        scale = float(m.scale or 1.0)
        val = a.value / scale
        tol = max(fact.tolerance, asserted_tolerance(a, a.value) / abs(scale))
        same_value = abs(val - fact.value) <= tol or (fact.signed_difference and abs(abs(val) - abs(fact.value)) <= tol)
        if not same_value:
            continue
        if fact.operands is None or frozenset(v.operands) == fact.operands:
            return True
    return False
