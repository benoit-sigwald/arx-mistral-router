# Agent Directives & Delegation Rules — ARX Mistral MCP Router

## Mission & Governance

Antigravity agents interacting with this repository and server MUST adhere to these rules:

### 1. English Standard
- All codebase documentation, comments, function docstrings, and commit messages MUST be written in **English**.

### 2. Delegation Strategy
- **Delegate to Mistral Router**:
  - Structured extraction from text or articles (`mistral_extract`).
  - Summarizing deployment or execution logs (`mistral_summarize_logs`).
  - Generating unit tests for self-contained functions or modules (`mistral_generate_tests`).
  - Localized inspection of code snippets (< 500 lines) (`mistral_analyze_code`).
  - Reviewing localized git diffs (`mistral_review_diff`).
- **Retain in Gemini Pro / Antigravity**:
  - Global multi-repository architecture planning.
  - Complex cross-module refactoring.
  - Interactive debugging sessions requiring active CLI tool loops.

### 3. Safety & Secret Policy
- Never include raw credentials, DB passwords, or API keys in prompts sent to the router.
- Never deploy modifications to OCI production without explicit user authorization.
