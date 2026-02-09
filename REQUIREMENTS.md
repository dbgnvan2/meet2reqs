### Requirements for Modifying the trans-summary Repository

This document provides a comprehensive set of requirements for an AI coding agent to implement modifications to the GitHub repository **dbgnvan2/trans-summary**. The goal is to adapt the existing transcript summarization pipeline to process meeting transcripts into structured outputs focused on extracting and enriching requirements (as user stories), decisions, action items, technology stack, and emphasized items. The workflow emphasizes token efficiency through caching, chunking, and multi-task prompting. Retain the core step-by-step logic (configuration validation, input selection, formatting, metadata addition, summarization/extraction, validation, output generation, packaging/archiving), but shift extraction from abstracts/summaries/blog posts to the new elements. Outputs are simplified to a set of documents (Markdown, HTML, PDF). Integrate Agile best practices for enriching user stories with acceptance criteria and functional requirements.

Requirements are framed as user stories with expanded acceptance criteria and functional requirements, derived from the modification plan. Prioritize modularity, security, and testing from the original repo.

1. **As a developer, I want an initial cleaning and formatting step that processes the raw transcript once and caches the output so that downstream extractions use a concise version to save tokens.**
   - **Expanded Acceptance Criteria**:
     - The pipeline starts with a single LLM call to clean the raw transcript (remove timestamps, noise, filler words) and format it into Markdown with speaker labels and basic sections.
     - Cleaned output is saved to a file (e.g., `cleaned.md`) or in-memory cache; subsequent steps load from cache if it exists.
     - Handles transcripts up to 15,000 tokens without exceeding model limits; if over, flag for chunking.
     - Validation checks fidelity (cleaned text preserves original meaning) and conciseness (output tokens < 70% of input).
     - Configurable via `config.py` (e.g., `cache_cleaned: true`).
   - **Functional Requirements**:
     - System must use Anthropic Claude API for cleaning with a simple prompt (e.g., "Clean and format this transcript into Markdown, removing unnecessary elements while preserving content.").
     - Implement file-based caching with existence checks to avoid redundant API calls.
     - Log token usage for the cleaning step using tiktoken for estimation.

2. **As a developer, I want optional chunking of the cleaned transcript into smaller segments so that long transcripts can be processed efficiently without full re-sends.**
   - **Expanded Acceptance Criteria**:
     - Chunking splits the cleaned text at natural boundaries (e.g., paragraphs or speaker turns) with configurable max tokens (e.g., 4,000) and overlap (e.g., 200 tokens).
     - Chunks are processed in parallel or sequentially; results are aggregated post-extraction (e.g., merge lists and deduplicate).
     - Applies only if cleaned text > 10,000 tokens; configurable threshold in `config.py`.
     - Validation ensures no data loss across chunks (e.g., overlapping items are not duplicated).
     - Tests cover edge cases like uneven chunk sizes or transcripts exactly at limits.
   - **Functional Requirements**:
     - System must use tiktoken for accurate token counting and splitting.
     - Support threading/multiprocessing for parallel chunk processing to reduce latency.
     - Aggregation logic must handle lists (e.g., for requirements) by combining and sorting by transcript order.

3. **As a developer, I want a multi-output extraction step that pulls all categories (requirements, decisions, action items, technology stack, emphasized items) in one LLM call from the cleaned/chunked transcript so that token usage is minimized.**
   - **Expanded Acceptance Criteria**:
     - Single API call extracts all five categories into structured JSON.
     - Requirements are formatted as user stories ("As a [role], I want [feature] so that [benefit]") following INVEST principles.
     - Decisions include outcome and rationale; action items include task, assignee, deadline (inferred if not explicit); technology stack lists mentioned tools; emphasized items capture key phrases.
     - If chunked, extract per chunk and aggregate.
     - Validation checks coverage (e.g., all mentioned actions captured) and structure (e.g., JSON schema compliance).
     - Outputs saved as separate JSON files per category (e.g., `requirements.json`).
   - **Functional Requirements**:
     - System must use a multi-task prompt instructing Claude to output only JSON with defined schema.
     - Parse JSON response and handle errors (e.g., retry on malformed output).
     - Deduplication during aggregation uses semantic similarity (e.g., fuzzy matching).

4. **As a developer, I want an enrichment step for extracted requirements that automatically adds acceptance criteria and functional requirements so that user stories are complete and testable.**
   - **Expanded Acceptance Criteria**:
     - For each user story, append 3-5 acceptance criteria in Given-When-Then format and functional requirements focusing on system behaviors (e.g., "The system must [behavior]").
     - Draws from embedded Agile templates (e.g., SMART principles, testability from Atlassian/AltexSoft resources stored in a static file).
     - Uses a separate low-token LLM call with requirements JSON as input.
     - Validation ensures relevance (e.g., criteria match story intent) and testability (e.g., measurable outcomes).
     - Enriched output saved as `enriched_requirements.json`.
   - **Functional Requirements**:
     - System must load `requirements.json` and prompt Claude for enrichment with examples from best practices.
     - Embed resource templates in `prompts/enrichment.md` or a data file to avoid external calls.
     - Flag ambiguous stories for manual review if enrichment confidence is low.

5. **As a developer, I want adapted validation logic applied to all extracted and enriched elements so that outputs maintain accuracy, coverage, and fidelity.**
   - **Expanded Acceptance Criteria**:
     - Multi-level validation (API response, format, completeness) extended to new categories: e.g., check if decisions match transcript verbatim, actions are actionable, user stories are INVEST-compliant.
     - For enriched items, validate testability (e.g., acceptance criteria have clear outcomes).
     - Triggers warnings/errors in logs; optional retries for low-coverage results.
     - Tests ensure 100% pass rate on sample transcripts.
     - Configurable thresholds (e.g., minimum coverage score) in `config.py`.
   - **Functional Requirements**:
     - System must perform fuzzy string matching for fidelity and semantic checks for coverage.
     - Integrate with existing validation pipeline, adding category-specific rules.
     - Log detailed validation results for debugging.

6. **As a developer, I want simplified document generation focused on the extracted/enriched content so that final outputs are concise and actionable.**
   - **Expanded Acceptance Criteria**:
     - Generates Markdown (core content), HTML (navigable with sections), and PDF (print-ready).
     - Templates exclude old elements (e.g., no abstracts); include sections for each category, with enriched requirements.
     - Uses Jinja2 for rendering; CSS for clean formatting.
     - Outputs stored in `projects/<transcript>/` (e.g., `formatted.md`, `webpage.html`, `pdf.pdf`).
     - Validation confirms all files are generated without errors and meet length thresholds.
   - **Functional Requirements**:
     - System must load JSON files and inject into updated templates.
     - PDF generation via WeasyPrint with table of contents.
     - Support GUI/CLI previews of outputs.

7. **As a maintainer, I want retained setup, interfaces, security, and testing with updates for new features so that the modified repo is reliable and production-ready.**
   - **Expanded Acceptance Criteria**:
     - Config validation covers new settings (e.g., chunk_size, enrichment_threshold); dependencies updated if needed (e.g., tiktoken).
     - GUI (`transcript_processor_gui.py`) and CLI support new workflow steps.
     - Security features (path sanitization, XSS prevention) apply to all outputs.
     - Tests expanded to cover chunking, multi-extraction, enrichment (e.g., 100+ tests total).
     - Documentation (README.md, ARCHITECTURE_DESIGN.md) updated to describe changes.
   - **Functional Requirements**:
     - System must auto-create directories and load .env for API keys.
     - Logging tracks token usage and steps throughout.
     - Ensure compatibility with original repo's modular architecture.
