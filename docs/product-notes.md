# Chronograph product notes

## Product thesis

Reactive AI waits for users to bring context. Chronograph should help a system preserve continuity by turning scattered work signals into a structured, source-grounded context graph.

## Core characteristics

1. **Context graph**
   - Connect people, projects, decisions, tasks, deadlines, owners, meetings, documents, messages, and artifacts.

2. **Task extraction**
   - Separate real commitments from conversational noise.
   - Distinguish active work, stale work, blockers, and review-needed items.

3. **Source grounding**
   - Every extracted task or claim should point back to its source material.
   - Preserve provenance: where it came from, who said it, and when it changed.

4. **Continuity over time**
   - Track what changed since the last review.
   - Track open loops, owners, blockers, and next likely artifact.

5. **Proactive surfacing**
   - Surface what needs attention without requiring the user to reconstruct state manually.
   - Avoid shallow notification spam; curate signal.

## Example

Meeting: Finance should follow up.
Slack: Deadline is Friday.
Email: Alex is now owner.

Chronograph should merge this into one active work item:

- Task: Finance follow-up
- Owner: Alex
- Due: Friday
- Sources: meeting + Slack + email
- State: active
- Needs review: yes/no depending on confidence and policy
