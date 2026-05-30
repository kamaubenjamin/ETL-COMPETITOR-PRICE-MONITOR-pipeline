# Review Runtime Handoff

## Current Implementation Status

Review Runtime v1 is implemented as a standalone package in `src/review_runtime`. The runtime supports:

- Review task creation from downstream review requests
- Review assignment and lifecycle management
- Approval, rejection, and correction flows
- Structured feedback record generation
- In-memory repository persistence

## Known Limitations

- Review persistence is currently in-memory only.
- There is no external review UI or reviewer assignment system.
- Feedback records are stored only for the duration of the runtime process.
- No integration with a long-term learning or training pipeline is implemented.

## Deferred Work

- Implement durable persistence for review items and feedback records.
- Add a review-stage integration point within the Workflow Runtime.
- Add a review UI or API endpoints for reviewer interactions.
- Support reviewer assignments, queue prioritization, and work distribution.

## Next Milestone

The next milestone should focus on Review Runtime implementation completeness:

1. Add persistent review storage.
2. Expose Review Runtime through a workflow stage or API contract.
3. Add review queue ownership and assignment metadata.
4. Integrate feedback into matching and review data retention.

## Recommended Reading Order

1. `docs/architecture/REVIEW_RUNTIME_IMPLEMENTATION.md`
2. `docs/architecture/REVIEW_RUNTIME_SUMMARY.md`
3. `docs/architecture/REVIEW_RUNTIME_HANDOFF.md`
4. `docs/architecture/RUNTIME_BOUNDARIES.md`
5. `docs/architecture/ENTITY_RUNTIME_V1_ARCHITECTURE.md`
6. `docs/architecture/MATCHING_RUNTIME_V1_ARCHITECTURE.md`
7. `docs/ROADMAP.md`
8. `docs/TECHNICAL_DEBT.md`
