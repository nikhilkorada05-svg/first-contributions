# CropShield AI

CropShield AI is a local-first Streamlit MVP for recording crop observations,
reviewing explainable field-risk indicators, and preparing cautious next steps.
Its rule-based risk score is calculated in Python. An optional Ollama model can
help describe possible causes and ask follow-up questions; it does not diagnose
crops or determine the risk score.

## Requirements

- Windows 10 or later
- Python 3.10 or later
- Optional: [Ollama for Windows](https://ollama.com/download) for local AI

## Windows setup

Open PowerShell in the project folder:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If a `.venv` already exists, reuse it and run the two install commands.

## Configure Ollama (optional)

Install and start Ollama separately. In PowerShell, check that the local service
and a model are available:

```powershell
ollama --version
ollama list
```

If no model is installed, select a model suitable for your computer from
Ollama's model library and install it yourself using Ollama. For example, after
choosing a model:

```powershell
ollama pull llama3.2
```

CropShield AI never downloads a model automatically and never falls back to a
cloud AI service. It checks the local Ollama API at
`http://localhost:11434/api/tags` and sends chat requests to
`http://localhost:11434/api/chat`. If Ollama is unavailable, local risk checks
and report storage continue to work.

## Run the app

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open the local address printed by Streamlit if a browser window does not open
automatically. Use **Crop assistant** to submit crop and field observations.
Enter or select an installed Ollama model to request a local explanation; leave
the model blank to use only deterministic risk rules. Reports are saved to
`data/reports.csv`, which is excluded from version control. The report dashboard
can show fictional sample reports and download the displayed table as CSV.

## Deploy on Streamlit Community Cloud

The GitHub repository includes this app in the `CropShield-AI` subfolder.
After the code is pushed:

1. Sign in to [Streamlit Community Cloud](https://share.streamlit.io/) with the
   GitHub account that can access the repository and authorize access if asked.
2. Choose **Create app** and select `nikhilkorada05-svg/first-contributions`,
   branch `main`.
3. Set the app's root directory to `CropShield-AI` and the main file to
   `app.py`, then deploy.

Community Cloud does not run Ollama on your computer. The hosted version
therefore disables Ollama and keeps reports only in the current browser session;
it does not save farmer reports to the shared server filesystem. For persistent
local reports and local Ollama, run the app on your own computer using the
instructions above. Do not enter private or personally identifying information
into a public hosted app.

## Run tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The tests cover deterministic rule scoring and local CSV storage. They require
neither Ollama nor internet access.

## Risk rules

The score adds points for selected field observations and is capped at 10:

| Observation | Points |
| --- | ---: |
| Wilting | 3 |
| Yellowing | 2 |
| Standing water | 3 |
| Dry soil | 2 |
| Wet soil | 2 |

Scores 0–2 are labelled Low, 3–5 Moderate, and 6–10 High. These are screening
indicators, not validated disease probabilities or a diagnosis. A field
observation may have multiple explanations.

## Safety and limitations

- AI-generated explanations may be incorrect and must be verified by a
  qualified agricultural officer or local extension service.
- No disease is diagnosed with certainty. Seek expert help when the cause is
  uncertain, the crop is deteriorating, or consequential decisions are needed.
- The app does not provide pesticide recommendations, concentrations, or
  application rates.
- It does not fetch weather, laboratory results, live market prices, or
  government services.
- The sample reports are fictional demonstration data and are not saved as real
  farmer reports.
- Report data is stored locally as CSV. Treat access to the project folder as
  access to the reports; do not enter confidential personal information.

## Screenshots

To document the interface, run the app locally and capture screenshots of the
crop assistant and report dashboard. Review screenshots for private information
before sharing or adding them to a public repository.
