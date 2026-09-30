# ✉️ AI Agent Email Dispatcher

A Streamlit app that writes, themes, illustrates, and sends personalized bulk emails using a [LangGraph](https://github.com/langchain-ai/langgraph) agent workflow powered by Google Gemini.

**Docker image:** [`mirzaasadijaz/ai-email-dispatcher`](https://hub.docker.com/repository/docker/mirzaasadijaz/ai-email-dispatcher)

## Features

- **AI-written emails** from a short prompt (Gemini), or paste your own exact content
- **Per-recipient personalization** – `[Recipient Name]` is replaced for every recipient in both body and subject
- **Automatic sender signature** from your name and title (falls back to "The Team")
- **Placeholder cleanup** – stray AI-invented brackets like `[Link: ...]` are stripped before sending
- **Themes** – simple default, or your own HTML wrapper using `{{content}}`
- **Image attachments** – upload one, write a prompt, or let the agent craft a prompt from your email (Imagen 3)
- **Flexible recipients** – type them in or upload a `.txt` file (`Name <email@domain.com>`, comma or newline separated)
- **Dispatch report** – success/failure status per recipient

## Workflow

```
START → generate_content → create_image_prompt → generate_image → dispatch_emails → END
```

## Project structure

| File | Purpose |
|---|---|
| `app.py` | Streamlit UI |
| `graph.py` | LangGraph workflow definition |
| `nodes.py` | Node logic: content, image prompt, image generation, SMTP dispatch |
| `state.py` | Shared `EmailState` TypedDict |
| `Dockerfile` / `docker-compose.yml` | Container setup |
| `.env.example` | Template for environment variables |

## Configuration

Copy the template and fill it in:

```bash
cp .env.example .env
```

| Variable | Description | Default |
|---|---|---|
| `GOOGLE_API_KEY` | Gemini API key | – |
| `SMTP_EMAIL` | Sender email address | – |
| `SMTP_PASSWORD` | SMTP password (Gmail: App Password) | – |
| `SMTP_SERVER` | SMTP host | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP port (STARTTLS) | `587` |

All values can also be entered in the app's sidebar.

## Run with Docker

**From Docker Hub:**

```bash
docker run -p 8501:8501 --env-file .env mirzaasadijaz/ai-email-dispatcher
```

**With Docker Compose (builds locally):**

```bash
docker compose up --build
```

Open <http://localhost:8501>.

## Run locally

Requires Python 3.11+.

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Usage

1. **Setup & Recipients** – enter your name/title, subject, and recipients.
2. **Text Content** – generate from a prompt or provide exact text.
3. **Theme & Styling** – choose Simple or a custom HTML template containing `{{content}}`.
4. **Image Attachment** – none, upload, manual prompt, or auto-generate.
5. Click **🚀 Execute Email Campaign** and review the dispatch report.

### Recipient format

```
Abdullah <abdullah@example.com>
jane@example.com
```

## Notes

- Gmail requires an **App Password** (with 2-Step Verification), not your normal password.
- Gmail limits daily sends (~500 for personal accounts); large lists may be throttled.
- Only send to people who have agreed to receive your email.
- Never commit `.env` or your mailing list. Both are in `.gitignore`.
- `requirements.txt` lists `langchain-groq`, which the code doesn't use; you can remove it.
