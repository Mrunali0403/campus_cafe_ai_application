# Campus Café Launch Team AI

This Python 3.12 project combines a Streamlit planning interface with a
sequential CrewAI crew (Market Researcher, Financial Analyst, Marketing Writer,
and Skeptical Reviewer). LangChain tools provide DuckDuckGo search, optional
Wikipedia research, and restricted arithmetic for the financial analysis.

## Setup

Create and activate a Python 3.12 virtual environment, then install the
project's existing dependencies:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

For local runs, set the required model credentials in your shell. Do not
commit credentials or paste them into source files:

```bash
export CAMPUS_CAFE_MODEL="openrouter/free"
export CREWAI_BASE_URL="https://openrouter.ai/api/v1"
```

Set `CREWAI_API_KEY` in your environment. For Streamlit Community Cloud,
open the app's **Settings → Secrets** and add:

```toml
CREWAI_API_KEY = "your-provider-api-key"
```

The app reads this secret without displaying it. `CAMPUS_CAFE_MODEL` defaults to
`openrouter/free`; `CREWAI_BASE_URL` defaults to the OpenRouter endpoint.
`CREWAI_TEMPERATURE` is optional and defaults to `0`. The application uses
`CAMPUS_CAFE_MODEL`; it does not change or depend on the shared
`CREWAI_MODEL` setting.

## Launch the interface

```bash
streamlit run app.py
```

Enter the café concept and target customers, then review or replace the
editable example financial assumptions before generating a plan. The app
displays and offers a Markdown download only when the backend completes
successfully. A successful run saves `final_brief.md` in the current working
directory. Failed or rate-limited runs show an error instead of presenting an
incomplete brief as a result.

The backend can also be imported as `campus_cafe_crew.run_launch_team(inputs)`.
Running `python campus_cafe_crew.py` prints the Streamlit launch command; use
the interface to provide the required planning inputs.

## Deploy to Streamlit Community Cloud

Push the project to GitHub, then create a Community Cloud app using this
repository, the `main` branch, and `app.py` as the entry point. Add
`CREWAI_API_KEY` under the app's Secrets settings before generating a plan.
The application uses `requirements.txt` to install dependencies. Generated
`final_brief.md` output and local credentials are excluded from Git.

## Limitations

- OpenRouter free-model quotas and model availability are provider-controlled.
  CrewAI rate-limit retries are disabled for this run so an HTTP 429 does not
  trigger repeated requests. For an exhausted `free-models-per-day` quota,
  wait for the reset or select another free model that is actually available
  to your account.
- Web search and Wikipedia require network access and may fail or return
  incomplete results. Failed searches are labeled unverified; the crew is
  instructed not to create citations or market facts from memory.
- Financial figures entered in the interface are user-provided assumptions,
  not independently verified facts. Startup costs are separated from monthly
  operating break-even, which is not a demand forecast.
- A credible, cited final brief cannot be produced until the model is
  available and the research tools return verifiable sources. The local
  `reflection.md` describes the approach and limitations; it does not claim
  that the model workflow has been run successfully.
