# AIMPF Architecture

```text
Next.js / React UI
        |
        v
FastAPI API
        |
        +--> PostgreSQL / pgvector
        |
        +--> Change fingerprint
        |       |
        |       v
        |   NetworkX dependency graph
        |       |
        |       v
        |   Behavior-conditioned prediction
        |       |
        |       v
        |   Adaptive validation selector
        |       |
        |       v
        |   Observation -> residual -> calibration
        |
        +--> Maintainability metrics
        |       |
        |       +--> structural evidence
        |       +--> evaluation evidence
        |       +--> validation history
        |
        +--> Research comparison
                |
                +--> AIMPF adaptive
                +--> uncertainty-only baseline
                +--> cheapest-first baseline
                +--> full-suite baseline
                +--> exact finite-set oracle
```

The system is intentionally local and modular. No external LLM, paid API, cloud service, Neo4j instance, Kubernetes cluster, or microservice deployment is required.
