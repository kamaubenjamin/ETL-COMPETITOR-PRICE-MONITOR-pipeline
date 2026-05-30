# Matching Runtime v1 Architecture

## Purpose

Matching Runtime v1 provides deterministic reconciliation between extracted entities (from Entity Runtime) and master data sources. It performs name normalization, candidate generation, similarity scoring, and confidence calculation to identify matching entities without requiring human review, ERP integration, or machine learning.

Matching Runtime enables workflow stages to:
- Match `Customer` entities to ERP customer records
- Match `Supplier` entities to ERP vendor records
- Match `LineItem` entities to ERP product catalogs
- Match `Address` entities to ERP delivery locations
- Build historical match recommendations

## Architecture

### Position in Runtime Stack

```
Entity Runtime
       ↓
Matching Runtime ← (consumes EntitySet)
       ↓
Workflow Runtime ← (consumes MatchSet)
```

### Core Responsibilities

- **Normalization**: deterministic text normalization for entity fields
- **Candidate Generation**: retrieve potential master data matches
- **Scoring**: similarity and relevance scoring using configurable strategies
- **Confidence Calculation**: explainable confidence scores from match evidence
- **Result Assembly**: immutable `MatchSet` containing matched entities
- **Explanation**: audit trail of how each match was determined

### Out of Scope (v1)

- ERP posting or data mutation
- Human review workflows
- Machine learning or embeddings
- LLM-based matching
- External API calls (local matching only)
- Historical data management beyond in-memory session state

## Contracts

All contracts use immutable `dataclass(frozen=True)` with full serialization support (`to_dict()`, `to_json()`).

### MatchType Enum

```python
from enum import Enum

class MatchType(str, Enum):
    EXACT = "exact"                    # Exact string match
    NORMALIZED = "normalized"          # Match after normalization
    FUZZY = "fuzzy"                    # Similarity-based match
    HISTORICAL = "historical"          # Match from historical records
    MANUAL = "manual"                  # Manual/user-provided match (future)
```

### MatchRequest

Wraps an entity and context for matching:

```python
@dataclass(frozen=True)
class MatchRequest:
    entity_id: str                          # Source entity ID
    entity_type: str                        # "customer" | "supplier" | "line_item" | "address"
    entity_data: Dict[str, Any]             # Normalized entity payload
    master_data_type: str                   # Target master data type
    match_strategy: str = "default"         # Matching strategy to use
    confidence_threshold: float = 0.7       # Minimum confidence to accept match
    allow_multiple_matches: bool = False    # Return all matches or best only
    source_lineage: SourceLineage = None    # Provenance from Entity Runtime
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### MatchCandidate

A potential matching master record:

```python
@dataclass(frozen=True)
class MatchCandidate:
    candidate_id: str                       # Master data record ID
    candidate_name: str                     # Master data record name
    candidate_fields: Dict[str, Any]        # Full candidate record data
    source: str                             # Master data source (e.g., "erp_customers")
    similarity_score: float                 # 0.0–1.0
    match_explanation: MatchExplanation     # Why this candidate matched
    confidence: float = 0.0                 # Final confidence
```

### MatchExplanation

Audit trail for how a match was determined:

```python
@dataclass(frozen=True)
class MatchExplanation:
    strategy_used: str                      # "exact" | "normalized" | "fuzzy" | "historical"
    match_signals: List[str]                # Evidence list, e.g., ["exact_name", "zip_match"]
    confidence_factors: Dict[str, float]    # Individual factor scores
    fallback_strategies: List[str]          # Strategies tried before success
    notes: str = ""                         # Human-readable summary
```

### MatchResult

The outcome of a single match request:

```python
@dataclass(frozen=True)
class MatchResult:
    request_id: str                         # Correlates to MatchRequest
    entity_id: str                          # Source entity ID
    matched: bool                           # True if a match was found
    best_match: Optional[MatchCandidate]    # Highest-confidence match
    all_candidates: List[MatchCandidate]    # All candidates if allow_multiple_matches=True
    overall_confidence: float                # Aggregate confidence (0.0–1.0)
    explanation: MatchExplanation           # Audit trail
    created_at: str                         # ISO timestamp
```

### MatchSet

Immutable container for all match results from a batch:

```python
@dataclass(frozen=True)
class MatchSet:
    source_document_id: str                 # From EntitySet
    matches: List[MatchResult]              # All match results
    match_statistics: Dict[str, Any]        # Counts: matched, unmatched, by_strategy
    overall_confidence: float                # Average across all results
    matching_metadata: Dict[str, Any]       # Strategy config, thresholds used
    created_at: str                         # ISO timestamp
```

## Matching Lifecycle

1. **Request Reception**
   - Receive `EntitySet` from Entity Runtime
   - For each entity, create a `MatchRequest`

2. **Field Normalization**
   - Normalize entity names, addresses, and codes using `TextNormalizer`
   - Extract searchable features (brand, size, category, etc.)

3. **Candidate Generation**
   - Query master data sources (in-memory or local files)
   - Generate list of potential candidates per entity
   - Bound candidate set to avoid exponential growth

4. **Similarity Scoring**
   - Apply selected matching strategy (exact, normalized, fuzzy, historical)
   - Compute similarity scores using field-specific algorithms
   - Build similarity vectors for multi-field matching

5. **Confidence Calculation**
   - Combine similarity scores with confidence factors
   - Weight by match signal types (exact > normalized > fuzzy)
   - Apply strategy-specific confidence adjustments

6. **Result Generation**
   - Filter candidates by minimum confidence threshold
   - Rank by confidence (highest first)
   - Assemble `MatchResult` with audit trail

7. **MatchSet Assembly**
   - Collect all `MatchResult` objects
   - Compute aggregate statistics
   - Return immutable `MatchSet` to Workflow Runtime

## Matching Strategies

All strategies are **deterministic** and **reproducible** with identical input.

### 1. Exact Match

- Exact string comparison (case-insensitive)
- Confidence: 1.0 on match, 0.0 on no match
- Fast, zero false positives
- Fallback: none

### 2. Normalized Match

- Normalize both entity and candidate names (whitespace, punctuation, stop words)
- Compare normalized strings for equality
- Confidence: 0.95 on match, escalate to next strategy on no match
- Useful for typos and formatting differences

### 3. Fuzzy Match

- Use similarity algorithms (e.g., Levenshtein, Jaro-Winkler) from RapidFuzz
- Configurable per-strategy thresholds (default: 0.75 similarity → 0.85 confidence)
- Multi-field matching: combine scores for name, brand, category, size
- Similarity matrix optimization for batch matching
- Confidence calculation: `confidence = base_threshold + (similarity - threshold) * scaling_factor`

### 4. Historical Match

- Treat historical matching as a first-class strategy
- Compare the current entity against prior successful matched entities
- Use historical evidence to select candidates directly, not only as a boost
- Historical matches may be exact, normalized, or fuzzy matches with prior confirmation
- In v1, historical records are maintained in-memory for reproducibility

## Execution Order

1. Try exact match
2. If no match, try normalized match
3. If no match, try historical match
4. If no match, try fuzzy match with default threshold
5. Return results; if no match found, create "no_match" result

## Confidence Model

Confidence scores are **deterministic, explainable, and auditable**.

### Design Principles

- No machine learning or learned weights
- Explicit factors with clear semantics
- Full audit trail in `MatchExplanation`
- Reproducible with identical input
- Entity-specific calculators for domain-sensitive scoring

### Confidence Calculators

Matching Runtime uses entity-specific confidence calculators:

- `CustomerConfidenceCalculator`
- `SupplierConfidenceCalculator`
- `ProductConfidenceCalculator`

Each calculator defines:

- domain-specific factor weights
- relevant match signals per entity type
- a `calculate_confidence(match_candidate, request)` method
- `confidence_factors` output for auditability

Shared scoring components are reused where applicable, but the calculator selects which signals matter most for the entity type.

### Scoring Factors

Each factor returns a 0.0–1.0 score:

- **Name Similarity**: Levenshtein ratio or Jaro-Winkler (0.0–1.0)
- **Brand Match**: 1.0 if brands match, 0.0 if they differ, 0.5 if one is missing
- **Category Match**: 1.0 if both products are in same category, 0.0 otherwise
- **Size Match**: 1.0 if dimensions match, 0.0 if they differ, 0.5 if missing
- **Code Match** (SKU, product code, vendor ID): 1.0 on exact match, escalate on no match
- **Address Match**: 1.0 for exact address, 0.5 for postal code only (customer/supplier)
- **Contact Match**: 1.0 for exact email/phone, 0.5 for partial contact overlap
- **Historical Signal**: prior successful match evidence used by historical strategy

### Overall Confidence Calculation

Entity-specific calculators may use formulas such as:

```
confidence = (
    name_similarity * name_weight +
    brand_match * brand_weight +
    category_match * category_weight +
    size_match * size_weight +
    code_match * code_weight +
    contact_match * contact_weight
)
```

Exact weights vary by calculator and are defined explicitly in the architecture, not learned.

Confidence is clamped to [0.0, 1.0].

## Historical Matching Strategy

Matching Runtime treats historical matching as a first-class strategy.

### Historical Strategy Behavior

- Compare incoming entities against prior successful matches saved during the workflow
- Use history as a direct candidate source, not just a confidence multiplier
- Generate `MatchType.HISTORICAL` when a historical candidate is selected
- Historical matches may still be validated by entity-specific confidence calculators
- Record historical evidence in `MatchExplanation`

### Cache Structure

```python
historical_matches: Dict[str, List[MatchCandidate]]
# key: normalized_signature + entity_type + master_data_type
# value: prior successful matches for that signature
```

### Usage

- On each new match request, query the historical cache for matching normalized signatures
- If matching history exists, evaluate those candidates first
- Use historical evidence as a strong signal within the confidence calculator
- Add signals such as `historical_candidate_id`, `historical_strategy_applied`, and `historical_name_similarity`

### Lifetime

- Per-workflow-execution only (in-memory session)
- Cleared between workflow runs
- Future versions may persist history to durable store

## Workflow Integration

### Stage Placement

Matching Runtime integrates as a workflow stage called `match`:

```yaml
stages:
  - name: extract
    type: entity_extract
    depends_on: [document_ingest]
    config:
      extraction_rule: entity_runtime_v1

  - name: match
    type: match
    depends_on: [extract]
    config:
      match_strategy: default
      confidence_threshold: 0.75
      master_data_source: erp

  - name: review
    type: review  # Future: Review Runtime
    depends_on: [match]
```

### Stage Contract

```python
class MatchStage(BaseStage):
    def run(self, input_artifact: EntitySet, context: ExecutionContext) -> StageResult:
        """
        Args:
            input_artifact: EntitySet from entity_extract stage
            context: Workflow execution context

        Returns:
            StageResult with output_artifact=MatchSet
        """
        # Deserialize config
        # Instantiate MatchingEngine
        # Execute matching
        # Return StageResult with MatchSet
```

### Config Options

- `match_strategy`: "default" | "exact_only" | "fuzzy_aggressive"
- `confidence_threshold`: 0.0–1.0
- `allow_multiple_matches`: boolean
- `master_data_source`: "erp" | "local" | "file"
- `fuzzy_threshold`: 0.0–1.0 for fuzzy match similarity requirement

## Runtime Boundaries

### Allowed Dependencies

- Entity Runtime: consume `EntitySet` and its contracts
- Workflow Runtime: return `MatchSet` in `StageResult`
- Local text utilities (normalization, hashing)
- Third-party matching libraries (RapidFuzz, etc.)

### Forbidden Dependencies

- ERP Runtime (not yet implemented)
- Review Runtime (not yet implemented)
- AI Runtime (future, not yet implemented)
- External APIs (for v1; future versions may add connectors)
- Database access (use in-memory or file-based master data)

### Artifact Boundaries

Input: `EntitySet` (from Entity Runtime)
Output: `MatchSet` (to Workflow Runtime)
Internal: Master data snapshots (file-based or in-memory DataFrames)

## Package Structure

Proposed structure mirrors Entity Runtime organization:

```
src/matching_runtime/
├── __init__.py
├── engine.py                        # MatchingEngine facade
├── contracts/
│   ├── __init__.py
│   ├── match_request.py
│   ├── match_candidate.py
│   ├── match_explanation.py
│   ├── match_result.py
│   └── match_set.py
├── strategies/
│   ├── __init__.py
│   ├── exact_matcher.py
│   ├── normalized_matcher.py
│   ├── fuzzy_matcher.py
│   └── historical_matcher.py
├── normalization/
│   ├── __init__.py
│   └── text_normalizer.py           # Inherit from Entity Runtime
├── candidate_generation/
│   ├── __init__.py
│   ├── master_data_loader.py
│   └── candidate_selector.py
├── confidence/
│   ├── __init__.py
│   └── scorer.py                    # Deterministic scoring
└── orchestration/
    ├── __init__.py
    └── orchestrator.py
```

## Future Evolution

### Phase 2: Review Runtime

Post-Matching Runtime, implement Review Runtime for:
- Manual review of low-confidence matches
- UI for user approval/rejection
- Feedback loop to improve match confidence

### Phase 3: ERP Runtime

After Review, implement ERP Runtime for:
- Create/update ERP records from matched entities
- Handle validation failures
- Audit trail of ERP mutations

### Phase 4: Agent Runtime

Future Agent Runtime may:
- Use LLMs to enhance matching confidence
- Integrate external data sources
- Support complex multi-entity reconciliation

### Transition Path

- Matching Runtime architecture is **stable** for Review and ERP runtimes
- Match results (`MatchSet`, `MatchResult`) are the contract boundary
- ERP Runtime will consume `MatchSet` and emit posting results
- Review Runtime will wrap matching in an approval loop

## Design Decisions

### 1. Immutable Contracts Only

- Contracts are frozen dataclasses
- Ensures reproducibility and auditability
- Simplifies testing and debugging

### 2. Deterministic Scoring Without ML

- Explainable confidence by design
- No learning or weight adjustment
- Fully auditable match decisions

### 3. In-Memory Master Data (v1)

- No database dependency in v1
- Master data loaded from files at workflow start
- Future versions add database connectors

### 4. Strategy-Based Matching

- Pluggable strategies allow flexible matching
- Execution order is deterministic
- Easy to add new strategies without breaking existing logic

### 5. Comprehensive Explanation Trail

- Every match decision has an explanation
- Confidence factors are documented
- Fallback strategies are recorded

## Verification Checklist

Before implementation:

- [ ] Contracts are frozen dataclasses with serialization
- [ ] All strategies are deterministic and reproducible
- [ ] Confidence scoring is explainable and auditable
- [ ] No circular imports between packages
- [ ] Matching lifecycle is clear and sequential
- [ ] Runtime boundaries forbid disallowed dependencies
- [ ] Integration path with Workflow Runtime is clear
- [ ] Master data loading strategy is documented
- [ ] Historical matching scope is bounded
- [ ] Package structure mirrors Entity Runtime patterns
