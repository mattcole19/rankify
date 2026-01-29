## Rankify Infrastructure

Pulumi (Python) program lives here. Phase 0 only reserves the directory; actual stacks, configuration, and deployment automation will arrive during Phase 2 when we wire up AWS ECS, ALB, RDS, S3, and CloudFront.

Planned structure:

- `pulumi/` – modules for network, compute, data, and delivery layers.
- `stacks/` – stack definition files (e.g., `dev`, `prod`).
- `Pulumi.<stack>.yaml` – per-stack config managed via `pulumi config`.

Until then, this folder acts as a placeholder to keep repo structure complete.
