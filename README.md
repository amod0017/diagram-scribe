# DiagramScribe

Describe a diagram in plain English. DiagramScribe generates it.

```bash
diagram-scribe
> Describe your diagram: CI/CD pipeline — push code, run tests, if tests pass deploy to
>                         staging, run smoke tests, if smoke tests pass deploy to production,
>                         otherwise notify the team.
> [diagram opens in Excalidraw]
> Refine (or press Enter to finish): add a manual approval step before production deploy
> [diagram updates]
> Refine (or press Enter to finish):
> Done.
```

Works as a CLI tool or as a Python library you can embed in your own project.

---

## Example prompts

**Flowchart with decision branches:**
```
user login flow with decisions: user submits login form, system validates
credentials, if valid show dashboard, if invalid show error message
```

**System architecture diagram:**
```
Generate a high-level system architecture diagram for an e-commerce platform.
The system should have an API Gateway that routes traffic to three distinct
microservices: 1. An Auth Service connected to a PostgreSQL database. 2. An
Order Service connected to a MongoDB database. 3. A Notification Service that
handles emails. Show an asynchronous message queue (like RabbitMQ) sitting
between the Order Service and the Notification Service to handle background tasks.
```

**UML sequence diagram:**
```
Create a UML sequence diagram showing a user logging into a mobile application.
The flow should include four participants: User, Mobile App, API Gateway, and
Identity Provider. The sequence must show: 1. The User entering credentials into
the Mobile App. 2. The Mobile App sending a POST request to the API Gateway.
3. The API Gateway forwarding the validation request to the Identity Provider.
4. The Identity Provider verifying the credentials, returning a JWT token back
to the Gateway, which passes it to the Mobile App. 5. The Mobile App successfully
displaying the home dashboard to the User.
```

---

## Install

```bash
pip install diagram-scribe
```

---

## Usage

**CLI** — interactive, no code needed:
```bash
diagram-scribe
```

**Library** — embed in your own tool:
```python
from diagram_scribe import DiagramScribe

ds = DiagramScribe()
ds.draw("User authentication flow — user submits credentials, validate token, "
        "if valid return dashboard, if invalid increment retry count, "
        "if retries exceeded lock account.")
ds.refine("add a password reset path after account lock")
```

---

## LLM Options

DiagramScribe needs an LLM to interpret your description. By default it uses [OpenRouter](https://openrouter.ai) — free models available, no credit card required. Or run one locally with [Ollama](https://ollama.com) (no account needed).

```bash
# Free via OpenRouter (default) — sign up at openrouter.ai, create a key
OPENROUTER_API_KEY=sk-or-... diagram-scribe

# Local via Ollama (no internet, no account)
OLLAMA_MODEL=qwen2.5 diagram-scribe

# Claude via Anthropic (paid) — pip install "diagram-scribe[claude]"
ANTHROPIC_API_KEY=sk-ant-... diagram-scribe
```

Or create `~/.config/diagram-scribe/.env` (works from any directory):

```ini
# OpenRouter (default)
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=nvidia/nemotron-3-super-120b-a12b:free

# Ollama
# OLLAMA_MODEL=qwen2.5

# Anthropic
# ANTHROPIC_API_KEY=sk-ant-...
```

---

## Documentation

- **[User Guide](docs/guide.md)** — setup, all LLM options, CLI and library examples, architecture
- **[API Reference](https://amod0017.github.io/diagram-scribe/)** — full class and method docs generated from source

---

## License

MIT
