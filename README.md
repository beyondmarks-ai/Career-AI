# Career AI

Career AI is a simple, professional resume-screening and career-guidance application.
Users upload a PDF or DOCX resume, enter their target job role, and receive an
AI-generated career report.

## Features

- Resume quality score out of 100
- ATS readiness score out of 100
- Target-role match score out of 100
- Resume strengths and specific improvement suggestions
- Missing role-related keywords
- Prioritized skills to learn with practical next steps
- A clear, measurable action plan
- English, Hindi, and French report options
- Secure keyless Azure authentication
- Responsive professional Streamlit interface

The AI is instructed to use only evidence found in the resume and not invent
experience, education, certifications, or achievements.

## What you need to install

Before downloading the project, install:

1. [Git](https://git-scm.com/downloads)
2. [Python 3.11 or newer](https://www.python.org/downloads/)
3. [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) when using Azure OpenAI
4. Access to either:
   - An Azure OpenAI resource with a deployed chat model, or
   - An OpenAI API key for local fallback

During Python installation on Windows, select **Add Python to PATH**.

## Download the project

Open PowerShell, Terminal, or a command prompt and run:

```bash
git clone https://github.com/beyondmarks-ai/AI-based-Career-Recommendation-System-With-Resume-Insight-and-Skill-Enhancement.git
cd AI-based-Career-Recommendation-System-With-Resume-Insight-and-Skill-Enhancement
```

## Install on Windows

Create a private Python environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell prevents activation, you can skip activation and use the direct Python
commands shown below.

Install the required packages:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Without activating the environment, use:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Install on macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Configure Azure OpenAI (recommended)

Sign in with Azure CLI:

```bash
az login
```

Your Azure user needs the **Cognitive Services OpenAI User** role on the Azure OpenAI
resource. The Azure resource must already have a compatible chat model deployment.

Create your local configuration file.

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS or Linux:

```bash
cp .env.example .env
```

Open `.env` and replace the example values:

```env
AZURE_OPENAI_ENDPOINT=https://YOUR-RESOURCE.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=YOUR-MODEL-DEPLOYMENT
AZURE_OPENAI_API_VERSION=2024-10-21
```

The application uses your Azure CLI login on your computer and Managed Identity when
deployed to Azure. An Azure API key does not need to be saved in the project.

## Configure an OpenAI API key instead

If you do not use Azure, create `.env` and add:

```env
OPENAI_API_KEY=YOUR-OPENAI-API-KEY
OPENAI_MODEL=gpt-4.1-mini
```

Do not commit or share `.env`. It is already excluded by `.gitignore`.

## Start the application

Windows:

```powershell
.\.venv\Scripts\python.exe -m streamlit run main.py
```

macOS or Linux:

```bash
.venv/bin/python -m streamlit run main.py
```

The browser should open automatically. If it does not, visit:

```text
http://localhost:8501
```

Stop the application by pressing `Ctrl+C` in the terminal.

## How to use Career AI

1. Upload a text-based PDF or DOCX resume, up to 8 MB.
2. Enter the job role you want to target.
3. Select the report language.
4. Select **Analyze my resume**.
5. Review your scores, improvements, missing skills, and action plan.

Scanned image-only PDFs need OCR before the application can read them.

## Run the automated tests

Windows:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

macOS or Linux:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

## Deploy to Azure App Service

The included deployment script creates or updates a Linux Azure App Service,
configures the Python runtime, enables Managed Identity, and optionally grants access
to the Azure OpenAI resource.

```powershell
.\deploy-azure.ps1 `
  -AppName 'YOUR-GLOBALLY-UNIQUE-APP-NAME' `
  -AzureOpenAIEndpoint 'https://YOUR-RESOURCE.openai.azure.com/' `
  -AzureOpenAIDeployment 'YOUR-MODEL-DEPLOYMENT' `
  -AzureOpenAIResourceId '/subscriptions/.../providers/Microsoft.CognitiveServices/accounts/YOUR-RESOURCE'
```

Optional parameters include `-ResourceGroup` and `-Location`. The default App Service
tier is B1 and can create billable Azure resources.

## Common problems

### `python` is not recognized

Reinstall Python and enable **Add Python to PATH**, or try `py` on Windows and
`python3` on macOS/Linux.

### PowerShell says script execution is disabled

Run Streamlit directly without activating the environment:

```powershell
.\.venv\Scripts\python.exe -m streamlit run main.py
```

### Azure authentication fails

Run `az login` again and confirm your account has the **Cognitive Services OpenAI
User** role on the correct Azure OpenAI resource.

### The resume has very little extracted text

Use a text-based PDF or DOCX. Image scans must be converted with OCR first.

## Project structure

```text
main.py                 Streamlit user interface
analysis_service.py     Validated scores, recommendations, and AI prompt
resume_parser.py        PDF and DOCX text extraction
llm_helper.py           Azure CLI and Managed Identity authentication
deploy-azure.ps1        Azure CLI deployment automation
Dockerfile              Container deployment option
requirements.txt        Python dependencies
tests/test_core.py      Parser and validation tests
```

## Privacy

The application does not save uploaded resumes. Resume text is sent to the configured
AI provider to create the report. Organizations deploying this project should publish
their own privacy notice and retention policy.
