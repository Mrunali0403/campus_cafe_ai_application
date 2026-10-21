"""
SCENARIO: "The Campus Café Launch Team"
=======================================
A university wants to open a new student café. A crew of four AI agents
collaborates to produce a launch brief for the dean:

  1. Market Researcher  -> gathers background info (LangChain search + Wikipedia tools)
  2. Financial Analyst  -> does the maths (custom LangChain calculator tool)
  3. Marketing Writer   -> drafts the brief using the others' findings
  4. Skeptical Reviewer -> critiques the draft and produces the FINAL version

Concepts demonstrated
---------------------
- Agents (role / goal / backstory)
- Tasks (description / expected_output / context = who feeds whom)
- Crew + Process.sequential
- Wrapping LangChain tools so CrewAI agents can use them

Setup
-----
    pip install -r requirements.txt
    # Set CREWAI_API_KEY in the environment or Streamlit Community Cloud Secrets.
    export CAMPUS_CAFE_MODEL="openrouter/free"
    export CREWAI_BASE_URL="https://openrouter.ai/api/v1"
    python campus_cafe_crew.py
"""

import ast
import math
import operator
import os
from pathlib import Path
from typing import Mapping

import requests
from ddgs.exceptions import DDGSException
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import BaseTool
from langchain_core.tools import tool as langchain_tool
from langchain_community.tools import DuckDuckGoSearchResults, WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from wikipedia.exceptions import WikipediaException

# --------------------------------------------------------------------------
# 1. THE LLM  (swap the model string to try different providers)
# --------------------------------------------------------------------------
llm = LLM(
    model=os.getenv("CAMPUS_CAFE_MODEL", "openrouter/free"),
    api_key=os.getenv("CREWAI_API_KEY"),
    base_url=os.getenv("CREWAI_BASE_URL", "https://openrouter.ai/api/v1"),
    temperature=float(os.getenv("CREWAI_TEMPERATURE", "0")),
    max_retries=0,
    custom_openai=True,
)


# --------------------------------------------------------------------------
# 2. TOOLS  (LangChain tools wrapped for CrewAI)
# --------------------------------------------------------------------------
# A custom LangChain tool: restricted arithmetic for financial estimates.
@langchain_tool
def calculator(expression: str) -> str:
    """Calculate basic arithmetic and ceil(...) for financial estimates."""
    operations = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
    }

    def evaluate(node):
        if isinstance(node, ast.Expression):
            return evaluate(node.body)

        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value

        if isinstance(node, ast.BinOp) and type(node.op) in operations:
            left = evaluate(node.left)
            right = evaluate(node.right)

            if abs(left) > 1e12 or abs(right) > 1e12:
                raise ValueError("Number is too large.")

            result = operations[type(node.op)](left, right)

            if abs(result) > 1e12:
                raise ValueError("Result is too large.")

            return result

        if isinstance(node, ast.UnaryOp) and isinstance(
            node.op, (ast.UAdd, ast.USub)
        ):
            value = evaluate(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value

        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "ceil"
            and len(node.args) == 1
            and not node.keywords
        ):
            return math.ceil(evaluate(node.args[0]))

        raise ValueError("Only basic arithmetic is supported.")

    try:
        if not expression or len(expression) > 200:
            raise ValueError("Expression is empty or too long.")

        tree = ast.parse(expression, mode="eval")
        result = evaluate(tree)

        if not isinstance(result, (int, float)) or not math.isfinite(result):
            raise ValueError("Result must be a finite number.")

        return str(result)

    except (
        SyntaxError,
        ValueError,
        ZeroDivisionError,
        OverflowError,
        RecursionError,
    ) as e:
        return f"Calculation error: {e}"



class LangChainToolAdapter(BaseTool):
    """Generic adapter: lets a CrewAI agent call ANY LangChain tool."""

    name: str
    description: str
    lc_tool: object  # the wrapped LangChain tool

    def _run(self, query: str) -> str:
        try:
            return str(self.lc_tool.invoke(query))
        except (
            DDGSException,
            requests.exceptions.RequestException,
            WikipediaException,
            TimeoutError,
            OSError,
        ) as error:
            return (
                f"Research tool unavailable ({type(error).__name__}); "
                "no result was verified. Do not cite or infer findings from "
                "this failed search."
            )


def wrap(lc_tool) -> LangChainToolAdapter:
    return LangChainToolAdapter(
        name=lc_tool.name, description=lc_tool.description, lc_tool=lc_tool
    )


web_search = wrap(
    DuckDuckGoSearchResults(num_results=3, output_format="json")
)
wikipedia = wrap(WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper(top_k_results=1)))
calc = wrap(calculator)


# --------------------------------------------------------------------------
# 3. AGENTS
# --------------------------------------------------------------------------
researcher = Agent(
    role="Market Researcher",
    goal="Find reliable facts on student café trends, pricing and demand",
    backstory=(
        "You spent ten years in campus retail research. You never state a "
        "number without saying where it came from."
    ),
    tools=[web_search, wikipedia],
    llm=llm,
    verbose=True,
    max_iter=2,
    max_retry_limit=0,
)

analyst = Agent(
    role="Financial Analyst",
    goal="Build a simple, transparent break-even estimate for the café",
    backstory=(
        "A careful accountant who always shows the arithmetic and states "
        "every assumption explicitly."
    ),
    tools=[calc],
    llm=llm,
    verbose=True,
    max_iter=2,
    max_retry_limit=0,
)

writer = Agent(
    role="Marketing Writer",
    goal="Turn research and numbers into a persuasive, readable one-page brief",
    backstory="A former student-newspaper editor who writes crisp, friendly prose.",
    llm=llm,
    verbose=True,
    max_iter=2,
    max_retry_limit=0,
)

reviewer = Agent(
    role="Skeptical Reviewer",
    goal="Find weak claims, missing risks and unsupported numbers, then fix them",
    backstory=(
        "A dean's office advisor who has seen a hundred over-optimistic "
        "proposals and rejects anything vague."
    ),
    llm=llm,
    allow_delegation=False,
    verbose=True,
    max_iter=2,
    max_retry_limit=0,
)


# --------------------------------------------------------------------------
# 4. TASKS  (context=[...] is how agents hand work to each other)
# --------------------------------------------------------------------------

research_task = Task(
    description=(
        "Research the case for launching a student cafe at a university with "
        "the following concept and location: {concept_location}. Target "
        "customers: {target_customers}. Treat an approximately 8,000-student "
        "population as scenario information only, not verified research or "
        "evidence of customer demand. Find credible, accessible sources for "
        "student spending habits, typical cafe prices, and 2-3 relevant trends "
        "such as sustainability, reusable packaging, and plant-based options. "
        "Prioritize government statistics, university studies, reputable "
        "industry reports, and current menus from identifiable cafes. "
        "For each finding, provide the exact source title, publisher, URL, "
        "publication date when available, and the specific fact it supports. "
        "Use only URLs and facts present in successful search-tool results; "
        "do not cite sources recalled from memory. "
        "Distinguish verified facts from general observations. Do not invent "
        "sources, prices, statistics, or student preferences. If reliable "
        "evidence specific to university students or the local area is "
        "unavailable, state that limitation clearly. Treat the university's "
        "8,000-student population as given scenario information, not evidence "
        "that 8,000 students will become customers."
    ),
    expected_output=(
        "Six to eight concise findings, each with a factual claim, source "
        "title, publisher, URL, and date when available. Cover student "
        "spending, cafe pricing, and sustainability or plant-based trends. "
        "Clearly flag evidence gaps and avoid unsupported numerical claims. "
        "If search tools fail, report that research could not be verified "
        "instead of supplying remembered or invented citations."
    ),
    agent=researcher,
)



finance_task = Task(
    description=(
        "Prepare a transparent monthly break-even estimate for the campus "
        "cafe using the market research as context. These are user-provided "
        "illustrative assumptions, not independently verified facts: "
        "one-time startup costs: ${startup_costs}; monthly fixed costs: "
        "${monthly_fixed_costs}; average selling price/customer spend: "
        "${average_selling_price}; variable cost per customer: "
        "${variable_cost_per_customer}; operating days per month: "
        "{operating_days_per_month}. Target customers: {target_customers}. "
        "Use USD and label every input as a user-provided assumption, never as "
        "researched data. Treat startup costs separately from monthly operating "
        "break-even and state they are excluded from that monthly calculation. "
        "Use the calculator tool for EVERY arithmetic calculation. "
        "Show these calculations explicitly: "
        "(1) contribution per customer = average spend - variable cost; "
        "(2) monthly break-even customers = fixed costs / contribution per "
        "customer; "
        "(3) daily break-even customers = monthly break-even customers / "
        "operating days; calculate the daily figure with ceil(...) so it is "
        "rounded UP to a whole customer; "
        "(4) break-even monthly revenue = monthly break-even customers * "
        "average spend. "
        "Check that contribution per customer is positive. If it is zero "
        "or negative, explain that break-even cannot be reached under those "
        "assumptions. Do not treat university enrollment as customer count. "
        "Clearly state that the estimate "
        "excludes any costs not listed and is not a demand forecast."
    ),
    expected_output=(
        "A concise table of every assumption, followed by the calculator "
        "expressions and results for contribution per customer, monthly "
        "break-even customers, daily break-even customers rounded up, and "
        "break-even monthly revenue. Clearly label sourced facts versus "
        "illustrative assumptions and identify exclusions."
    ),
    agent=analyst,
    context=[research_task],
)


draft_task = Task(
    description=(
        "Write a one-page launch brief for the dean combining the research "
        "and the financial estimate. Preserve these user-provided financial "
        "assumptions exactly: one-time startup costs USD ${startup_costs}; "
        "monthly fixed costs USD ${monthly_fixed_costs}; average selling "
        "price USD ${average_selling_price}; variable cost per customer "
        "USD ${variable_cost_per_customer}; and {operating_days_per_month} "
        "operating days per month. Do not substitute other values or describe "
        "these assumptions as verified research. Keep startup costs separate "
        "from monthly break-even calculations. Include a summary, opportunity, "
        "numbers, and call to action."
    ),
    expected_output=(
        "A ~300-word Markdown draft that reproduces the supplied financial "
        "assumptions accurately and labels them user-provided assumptions."
    ),
    agent=writer,
    context=[research_task, finance_task],
)


review_task = Task(
    description=(
        "Critically review the Marketing Writer's draft against the original "
        "market research and financial analysis. Identify the three biggest "
        "weaknesses internally. Check that factual claims have identifiable "
        "sources, financial figures are labelled as sourced facts or explicit "
        "assumptions, and every calculation agrees with the analyst's "
        "arithmetic. Check for missing risks, including uncertain demand, "
        "seasonality, food waste, staffing, and operating costs. The user's "
        "financial assumptions are startup costs USD ${startup_costs}, "
        "monthly fixed costs USD ${monthly_fixed_costs}, average selling "
        "price USD ${average_selling_price}, variable cost per customer "
        "USD ${variable_cost_per_customer}, and "
        "{operating_days_per_month} operating days per month. Preserve these "
        "values exactly, label them user-provided assumptions, and keep "
        "startup costs separate from monthly break-even. Verify that "
        "sustainability and plant-based claims are supported rather than "
        "presented as proven student preferences without evidence. Correct "
        "unsupported claims; do not invent sources or numbers. If a source "
        "cannot be verified, remove the claim or clearly label the limitation. "
        "Return only a concise, one-page FINAL launch brief for the Dean, "
        "including sourced facts, transparent break-even assumptions and "
        "arithmetic, key risks, and a clear recommendation. Do not include "
        "the critique in the final output."
    ),
    expected_output=(
        "Only the final one-page Markdown launch brief, with source-backed "
        "claims, explicit assumptions, correct arithmetic, risks, and a "
        "recommendation. Do not include critique text."
    ),
    agent=reviewer,
    context=[research_task, finance_task, draft_task],
)



# --------------------------------------------------------------------------
# 5. THE CREW
# --------------------------------------------------------------------------
crew = Crew(
    agents=[researcher, analyst, writer, reviewer],
    tasks=[research_task, finance_task, draft_task, review_task],
    process=Process.sequential,
    verbose=True,
    max_rpm=8,
)

FINAL_BRIEF_PATH = Path(__file__).resolve().with_name("final_brief.md")
FINANCIAL_INPUT_KEYS = (
    "concept_location",
    "target_customers",
    "startup_costs",
    "monthly_fixed_costs",
    "average_selling_price",
    "variable_cost_per_customer",
    "operating_days_per_month",
)


def _exception_chain(error: BaseException):
    seen = set()
    current = error
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = current.__cause__ or current.__context__


def _provider_status_code(error: BaseException) -> int | None:
    for item in _exception_chain(error):
        status = getattr(item, "status_code", None)
        response = getattr(item, "response", None)
        if status is None:
            status = getattr(response, "status_code", None)
        if isinstance(status, int):
            return status
    return None


def _is_exhausted_free_model_quota(error: BaseException) -> bool:
    details = " ".join(
        " ".join(
            str(value)
            for value in (
                item,
                getattr(item, "code", ""),
                getattr(item, "message", ""),
            )
        ).lower()
        for item in _exception_chain(error)
    )
    return (
        "free-models-per-day" in details
        or (
            _provider_status_code(error) == 429
            and (
                "0 requests remaining" in details
                or "zero requests remaining" in details
                or "free-model quota" in details
            )
        )
    )


def _failure_message(error: BaseException) -> str:
    if _is_exhausted_free_model_quota(error):
        return (
            "The OpenRouter free-model daily quota is exhausted (HTTP 429). "
            "No automatic retry was made. Wait for the quota reset, or set "
            "CAMPUS_CAFE_MODEL to another free model that is currently "
            "available on your OpenRouter account."
        )

    status_code = _provider_status_code(error)
    if status_code == 429:
        return (
            "The model provider returned HTTP 429. Automatic retries are "
            "disabled; check the provider's rate-limit reset or choose a "
            "model that is currently available."
        )

    status = f" (HTTP {status_code})" if status_code else ""
    return (
        f"The multi-agent workflow did not complete{status}: "
        f"{type(error).__name__}. Check the model configuration and "
        "provider availability, then run again."
    )


def _validated_inputs(inputs: Mapping[str, object]) -> dict[str, object]:
    missing = [key for key in FINANCIAL_INPUT_KEYS if key not in inputs]
    if missing:
        raise ValueError(f"Missing required launch-plan inputs: {', '.join(missing)}")

    clean_inputs: dict[str, object] = {}
    for key in ("concept_location", "target_customers"):
        value = inputs[key]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key.replace('_', ' ').capitalize()} cannot be empty.")
        clean_inputs[key] = value.strip()

    for key in (
        "startup_costs",
        "monthly_fixed_costs",
        "average_selling_price",
        "variable_cost_per_customer",
    ):
        value = inputs[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{key.replace('_', ' ').capitalize()} must be numeric.")
        if not math.isfinite(value) or value < 0:
            raise ValueError(
                f"{key.replace('_', ' ').capitalize()} must be a finite, "
                "non-negative amount."
            )
        clean_inputs[key] = value

    if clean_inputs["average_selling_price"] <= 0:
        raise ValueError("Average selling price must be greater than zero.")
    if clean_inputs["variable_cost_per_customer"] >= clean_inputs["average_selling_price"]:
        raise ValueError(
            "Variable cost per customer must be less than the average selling price."
        )

    days = inputs["operating_days_per_month"]
    if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 31:
        raise ValueError("Operating days per month must be a whole number from 1 to 31.")
    clean_inputs["operating_days_per_month"] = days
    return clean_inputs


def run_launch_team(inputs: Mapping[str, object]) -> str:
    """Run the existing crew with validated user inputs and save only a final brief."""
    if not os.getenv("CREWAI_API_KEY"):
        raise RuntimeError("CREWAI_API_KEY is not set; the analysis did not start.")

    clean_inputs = _validated_inputs(inputs)
    from crewai.llms.retry import _active_llm_rate_limit_retry

    retry_token = _active_llm_rate_limit_retry.set(True)
    try:
        result = crew.kickoff(inputs=clean_inputs)
    finally:
        _active_llm_rate_limit_retry.reset(retry_token)

    brief = getattr(result, "raw", None)
    if not isinstance(brief, str) or not brief.strip():
        raise RuntimeError("The workflow returned no final brief; it was not saved.")
    task_outputs = getattr(result, "tasks_output", None)
    if not isinstance(task_outputs, list) or len(task_outputs) != len(crew.tasks):
        raise RuntimeError(
            "The workflow did not complete all four tasks; no final brief was saved."
        )
    brief = brief.strip()

    assumptions = (
        "\n\n## User-provided financial assumptions\n\n"
        "| Input | Assumption |\n"
        "|---|---:|\n"
        "| One-time startup costs (excluded from monthly break-even) | "
        f"${clean_inputs['startup_costs']:,.2f} USD |\n"
        "| Monthly fixed costs | "
        f"${clean_inputs['monthly_fixed_costs']:,.2f} USD |\n"
        "| Average selling price per customer | "
        f"${clean_inputs['average_selling_price']:,.2f} USD |\n"
        "| Variable cost per customer | "
        f"${clean_inputs['variable_cost_per_customer']:,.2f} USD |\n"
        "| Operating days per month | "
        f"{clean_inputs['operating_days_per_month']} |\n\n"
        "All figures above are user-provided planning assumptions, not "
        "independently verified research.\n"
    )
    final_brief = f"{brief}{assumptions}"
    FINAL_BRIEF_PATH.write_text(f"{final_brief}\n", encoding="utf-8")
    return final_brief


def main() -> int:
    print("Launch the Streamlit interface with: streamlit run app.py")
    print("The launch plan requires user-provided concept and financial inputs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
