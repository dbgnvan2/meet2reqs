# Requirements Extraction Prompt v1

You are an expert business analyst extracting requirements from meeting transcripts. Your task is to identify all requirements discussed in the transcript and frame them as user stories following the standard Agile format.

## Instructions

1. Read the entire transcript carefully.
2. Identify every requirement, feature request, need, or capability discussed by any participant.
3. Frame each as a user story: **"As a [role], I want [capability/feature] so that [benefit/value]."**
4. Extract the **exact supporting quote(s)** from the transcript that establish this requirement.
5. Assign a priority based on context clues (explicit priority statements, emphasis, urgency language).
6. Tag the status if mentioned (e.g., "agreed", "proposed", "deferred", "contested").

## User Story Quality — INVEST Principles

Each user story must be:
- **Independent**: Can be developed without depending on another story (where possible)
- **Negotiable**: Not a rigid contract; captures intent, not implementation
- **Valuable**: Delivers clear value to a user or stakeholder
- **Estimable**: Specific enough that effort can be estimated
- **Small**: Focused on a single capability or need
- **Testable**: Has a clear definition of done

## Output Format

Return a valid JSON array. Each element must follow this exact schema:

```json
[
  {
    "id": "REQ-001",
    "user_story": "As a [role], I want [feature] so that [benefit]",
    "role": "the specific role extracted from context",
    "capability": "what they want/need",
    "benefit": "why they want it",
    "priority": "high|medium|low",
    "status": "agreed|proposed|deferred|contested|implied",
    "source_quotes": [
      "exact verbatim quote from transcript supporting this requirement"
    ],
    "context": "brief description of the discussion context where this came up",
    "speaker": "name of person who raised this (if identifiable)"
  }
]
```

## Rules

- Extract ONLY requirements that are actually discussed or implied in the transcript.
- Do NOT invent, infer, or hallucinate requirements not grounded in the transcript text.
- Each `source_quotes` entry must be a verbatim excerpt from the transcript (word-for-word).
- If a requirement is discussed by multiple speakers, include all relevant quotes.
- If priority is not explicitly stated, infer from context (urgency words, emphasis, ordering).
- If the role is not explicit, infer the most logical role from context.
- Number requirements sequentially: REQ-001, REQ-002, etc.
- Return ONLY the JSON array. No preamble, no explanation, no markdown fences.

## Transcript

{{insert_transcript_text_here}}
