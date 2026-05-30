# Status
Accepted

# Context
The platform design could abstract buyers and sellers under a common "party" concept, but early-stage delivery requires simpler, concrete entity models.

# Decision
For v1, the architecture avoids a generic `Party` abstraction and instead keeps `Customer` and `Supplier` as distinct entity types. This preserves clarity in extraction, validation, and matching semantics.

# Consequences
Benefits:
- Reduces complexity in early runtime implementation.
- Avoids ambiguous entity semantics when document roles differ.
- Makes matching strategies easier to tune per entity type.

Tradeoffs:
- May duplicate some common logic between customer and supplier flows.
- Could require refactoring later if a party abstraction becomes necessary.

Future implications:
- A future runtime version may introduce a shared party abstraction once customer/supplier workflows converge and the architecture supports polymorphic entity handling.
