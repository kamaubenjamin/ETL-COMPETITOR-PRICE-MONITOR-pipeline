# Status
Accepted

# Context
Matching Runtime needs a way to leverage prior successful matches without introducing machine learning or external persistence in v1. Historical evidence can improve confidence for repeated entities.

# Decision
Matching Runtime v1 treats historical matching as a first-class strategy. Prior successful matches are maintained in-memory for the current workflow execution and can be selected directly as `MatchType.HISTORICAL` candidates.

# Consequences
Benefits:
- Improves match recall for repeated entities within the same execution session.
- Keeps the runtime deterministic and explainable.
- Avoids early commitment to persistent history stores or learned models.

Tradeoffs:
- Historical evidence is not durable across workflow runs.
- The current implementation does not support persisted match history or replay across executions.

Future implications:
- Later versions should add a persistence layer for historical matches and integrate review feedback into the historical strategy.
