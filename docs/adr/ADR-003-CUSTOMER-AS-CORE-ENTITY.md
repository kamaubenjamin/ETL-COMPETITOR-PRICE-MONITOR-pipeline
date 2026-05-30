# Status
Accepted

# Context
Extracted business entities must include customers as core participants in invoice and purchase order workflows. The platform needs a stable entity type for matching and reconciliation.

# Decision
The architecture treats `Customer` as a core entity type in Entity Runtime and Matching Runtime. Customer entities are modeled explicitly alongside `Supplier`, `LineItem`, and `Address`, with dedicated contracts and matching support.

# Consequences
Benefits:
- Simplifies entity extraction and matching for buyer-side workflows.
- Enables targeted normalization, validation, and confidence scoring for customer data.
- Supports future ERP reconciliation for customers and billing partners.

Tradeoffs:
- Increases the number of explicit entity contracts that must be maintained.
- May require separate normalization rules from supplier/product entities.

Future implications:
- Customer-specific confidence calculators and review workflows should be added as matching and review runtime capabilities evolve.
