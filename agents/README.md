# Agents — Onboarding & Usage
Date: 2026-06-01

## Agent Overview

Repository agents are lightweight, policy-aware assistants that help preserve governance, architecture consistency, implementation quality, and release discipline. Agents exist to draft and maintain documentation, enforce process checklists, prepare ADRs and RFCs, and organize work for human implementation.

This repository uses agents to ensure that important project knowledge is persisted in the repository and not only in chat logs.

## Available Agents

### ETL Platform Governance
Responsibilities:
- Governance enforcement
- Definition of Done verification
- Documentation requirements
- Roadmap updates
- Technical debt management
- ADR compliance
- Release readiness

When to use:
- Before starting implementation
- After completing implementation
- During architecture reviews

### Runtime Engineer
Responsibilities:
- Runtime implementation
- Testing and automation
- Refactoring and performance improvements
- Preserving runtime boundaries

When to use:
- Implementing new runtimes
- Modifying existing runtimes
- Creating tests

### Platform Architect
Responsibilities:
- Architecture reviews
- ADR creation
- Dependency analysis
- Runtime design and interfaces
- Roadmap planning and technical debt review

When to use:
- Designing new runtimes
- Reviewing architecture
- Planning milestones

### Release Manager
Responsibilities:
- Release verification
- Documentation verification
- Test verification
- Git verification and tagging
- Milestone tagging and release notes

When to use:
- Before releases
- Before milestone closure
- Before tagging

### Release Manager
Responsibilities:
- Release verification
- Documentation verification
- Test verification
- Git verification and tagging
- Milestone tagging and release notes

When to use:
- Before releases
- Before milestone closure
- Before tagging

## Recommended Workflow

1. Architecture Review → Platform Architect
2. Implementation → Runtime Engineer
3. Governance Verification → ETL Platform Governance
4. Release Verification → Release Manager

## Agent Continuity Rule

All project knowledge must be persisted in repository documentation. Future contributors may include GitHub Copilot, ChatGPT, Cline, Codex, and human developers. No critical project knowledge should exist only in chat history.

## Required Reading Order

1. docs/architecture/PROJECT_CONTEXT.md
2. docs/architecture/README.md
3. ROADMAP.md
4. TECHNICAL_DEBT.md
5. docs/adr/
6. Runtime Architecture Documents

Documentation only. Do not modify runtime code.

---

Capability matrix: see `agents/CAPABILITY_MATRIX.md` for a concise mapping of agent responsibilities and recommended ownership for milestones.

End of file.