# path: sylabus.md
# PolicyLens: Insurance Ops Claims Triage and Compliance Workflow

Duration: 6 Weeks (30 Lab Days, Mon–Fri)  
Format: Hands-on postgraduate programming lab  
Focus: API-first Workflow Design • DRF Contracts • Auditability • ML-assisted Completeness • Ops UI • CI/CD • Deployment Readiness

## Course Overview

Insurance operations teams spend time chasing missing documents, reconciling decision history, and proving why a case was handled a certain way. This lab guides you through building PolicyLens, a production-style workflow tool that supports claim and policy-change intake, document handling, reviewer queues, SLA timers, internal notes, decisioning, and exportable audit evidence.

The project stance is API-first for core workflow, server-rendered UI for ops. Django REST Framework serializers define the canonical contract, domain services implement behaviour, and the ops dashboard is added later using Django Templates, Bootstrap, and HTMX without duplicating business logic. A lightweight ML component scores submissions for likely incompleteness, producing a score, label, and reason codes that are stored and exportable as evidence.

## Weekly Structure

| Week | Theme | Core Skills | Key Deliverables |
|---|---|---|---|
| 1 | Foundations and API contract begins | Repo bootstrap • Docker Compose + Postgres • Baseline domain models • DRF contract-first approach • pytest + factory_boy • CI pipeline | docker-compose.yml, core models, /api/claims list-create, test harness, GitHub Actions, seed path |
| 2 | Core workflow API-first | Claim lifecycle • Document upload • Notes • Decisions • Audit events • Permissions and roles • End-to-end API integration tests | /api/claims/{id}/documents, /decisions, /notes, append-only AuditEvent table, API permission gates, flow tests |
| 3 | Operational features in API | SLA clock rules • Queue prioritisation • Filtering • Idempotency and error handling • Audit export JSON | /api/queue/claims, deterministic SLA classification, /api/claims/{id}/audit-export, contract validation tests |
| 4 | ML scoring module and integration | Synthetic data generation • Feature contract • Deterministic preprocessing • Train, save, load • Scoring service • Reason codes • Threshold monotonicity | ml/ feature extractor, train script, model artefact directory, /api/claims/{id}/ml-score, ML contract tests |
| 5 | Server-rendered ops UI | Templates + Bootstrap tokens • HTMX partials • Queue and claim detail pages • Timeline narrative • UI tests | /ops/queue, /ops/claims/{id}, HTMX actions for notes, docs, decisions, ML score, UI integration tests |
| 6 | Production readiness | Gunicorn + Nginx • Health checks • Secure settings • Coverage gates • Deployment runbook • PDF evidence export | /api/health, Dockerfile.prod, docker-compose.prod, CI coverage threshold, docs/DEPLOYMENT.md, audit export PDF |

## Learning Outcomes

By completing PolicyLens, you will be able to:

- Design workflow software with a canonical API contract that stays stable as the UI evolves.
- Build a domain service layer that prevents duplicated business logic across API and UI.
- Implement an append-only audit trail and produce exportable evidence bundles for compliance.
- Build prioritised reviewer queues driven by deterministic SLA rules and filterable views.
- Integrate a pragmatic ML scorer that emits reason codes and remains reproducible across runs.
- Write unit and integration tests that hit the database and validate real workflow behaviour.
- Package and ship a production-style Django service with health checks, security settings, and CI gates.

## Assessment and Artifacts

- Source with tests: pytest and pytest-django, factories, DB-hitting integration tests, CI passing, coverage threshold enforced
- API contract: DRF serializers and stable request and response shapes for core endpoints
- Evidence exports: JSON audit export plus PDF export for reviewer and compliance workflows
- ML artefacts: deterministic feature extraction, saved model artefacts, reproducible scoring behaviour, reason-code stability tests
- Ops UI: server-rendered dashboard with queue and claim detail timeline, HTMX actions, and UI tests
- Production packaging: Gunicorn, Nginx, production compose file, env-driven settings, health check endpoint
- Documentation: setup guide, deployment guide, runbook, and a demo script

## Reflective Practice

Weekly short reflections to consolidate engineering and communication skills:

- Week 1: Contracts and reproducibility, why determinism matters early
- Week 2: Workflow correctness, making lifecycle operations testable and auditable
- Week 3: Operational readiness, SLA rules, prioritisation, and evidence exports
- Week 4: ML integration without hype, reason codes, contracts, and governance
- Week 5: UX for ops teams, timelines, empty states, and HTMX as a testable pattern
- Week 6: Production credibility, health checks, CI gates, and deploy documentation

## Tools and Stack

Languages: Python 3.11 • HTML/CSS (Bootstrap)  
Backend: Django • Django REST Framework  
Database: PostgreSQL  
UI: Django Templates • Bootstrap 5.3 • HTMX  
ML: scikit-learn • joblib, optional NumPy  
Testing: pytest • pytest-django • factory_boy • pytest-cov  
Quality: ruff • black  
Infrastructure: Docker • Docker Compose • GitHub Actions • Gunicorn • Nginx  
Exports: reportlab for PDF evidence generation  
Data: synthetic claims and document metadata, plus optional sample datasets for testing scenarios

## Final Deliverable

A reproducible, deployable insurance ops workflow tool that triages claims with SLA-aware queues, captures decisions and notes with an append-only audit trail, integrates an ML completeness scorer with reason codes, and produces exportable evidence bundles in JSON and PDF, ready for portfolio review and recruiter demos.
