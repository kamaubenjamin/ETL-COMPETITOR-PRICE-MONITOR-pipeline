# Status
Accepted

# Context
The platform must support human review for low-confidence or ambiguous matches. Defining a Review Feedback Runtime ensures review actions are integrated into the architecture rather than bolted on later.

# Decision
Review Feedback Runtime is defined as a distinct runtime responsible for capturing review decisions, managing review queues, enforcing confidence thresholds, and emitting corrections back into the workflow pipeline.

# Consequences
Benefits:
- Provides a dedicated architectural home for human feedback.
- Enables auditability of review decisions and correction history.
- Prepares the platform for future review-driven learning and automation.

Tradeoffs:
- Adds a new runtime boundary that must be coordinated with Workflow and Matching runtimes.
- Leaves UI and review tooling out of scope for v1.

Future implications:
- Review outputs can become training signals for future learning-based matching enhancements.

# Human review workflow
- Identify low-confidence or unmatched entities from Matching Runtime
- Enqueue review tasks for human validation and correction
- Capture review outcome and associate it with the original entity and match request

# Confidence thresholds
- Define review eligibility based on match confidence and strategy
- Use configurable thresholds to determine when review is required
- Allow higher-confidence results to bypass review while flagging ambiguous cases

# Review queue ownership
- Review Feedback Runtime owns the queue of pending review tasks
- It tracks task state, assignment, and processing metadata
- It exposes review task summaries to Workflow Runtime and downstream consumers

# Correction lifecycle
- Receive reviewer feedback and correction data
- Validate and normalize correction inputs
- Persist correction metadata and update review task state
- Emit review completion events to the workflow pipeline

# Feedback capture
- Record review rationale, corrected values, reviewer identifiers, and timestamp
- Maintain an audit trail for each correction
- Preserve review metadata for downstream reporting and traceability

# Future learning integration
- Design review output to support future learning or rule-updating pipelines
- Capture structured correction signals for matching strategy improvements
- Avoid tying v1 feedback capture to specific learning implementations

# Runtime boundaries
- Upstream: Matching Runtime results and Workflow Runtime review stage
- Downstream: Workflow Runtime, future Matching Runtime feedback loops, and audit/reporting systems
- Review Feedback Runtime must not perform direct entity extraction or document parsing

# Tradeoffs
- Defining review as its own runtime provides clarity but adds architectural complexity.
- Deferring UI and machine learning integration keeps v1 focused on workflow boundaries.

# Deferred functionality
- No review user interface is included in v1
- No machine learning or automated correction inference is included
- No persistent feedback model beyond workflow metadata is required for v1
