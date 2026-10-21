# Project Reflection

The project separates launch planning into four CrewAI roles: a Market
Researcher looks for evidence, a Financial Analyst calculates break-even,
a Marketing Writer drafts the plan, and a Skeptical Reviewer checks its
claims and risks. A Streamlit form collects the café concept, intended
customers, and editable financial assumptions before passing them to the
existing crew. This keeps presentation and workflow orchestration separate.

LangChain tools provide DuckDuckGo search, Wikipedia research when available,
and a restricted arithmetic calculator. The financial inputs are planning
assumptions supplied by the user, not verified research. Startup costs are
kept separate from monthly operating break-even; the student population or
target-customer description is not treated as proof of demand. Search results
may be incomplete or unavailable, and only successful workflow output is
presented as a final brief.

The provider quota, live model, and network search services limit what can be
validated without making external requests. This implementation pass did not
run the CrewAI workflow, so no research findings, financial results, or launch
recommendations have been verified. The project reinforced the importance of
distinguishing assumptions from evidence, making tool failures visible, and
keeping a generated deliverable separate from an honest failure status.
