# Project Plan

## Objective
Build a phased AWS CDK (Python) project for a custom VPC foundation POC using Poetry, PyCharm, and a Codex-assisted workflow where the user writes the production code.

## Current Architecture Intent
- VPC CIDR: `10.0.0.0/16`
- 2 AZ deployment
- 6 active subnets now, 10 `/20` subnets reserved for future growth
- NAT-free by default
- ECS Fargate planned for the app tier
- Add one NAT Gateway later only if validation proves it is required

## Milestones

### M1 — Repository bootstrap
#### Scope
- Create Poetry project
- Establish repo structure
- Add memory/control files
- Add `.gitignore`
- Add basic quality tooling placeholders

#### Done Definition
- `poetry install` works
- repo files exist
- initial Git commit created

#### Validation
- `poetry env info`
- `git status`
- open project successfully in PyCharm

---

### M2 — CDK bootstrap
#### Scope
- Add AWS CDK dependencies
- Initialize CDK app structure
- Add placeholder stack
- Confirm synth works

#### Done Definition
- `cdk synth` succeeds
- basic stack entrypoint exists
- project layout is stable

#### Validation
- `poetry run cdk synth`

---

### M3 — Network model
#### Scope
- Add VPC stack
- Add 2-AZ subnet layout
- Add route table model
- No NAT initially

#### Done Definition
- 6 subnets exist in synth output
- subnet CIDRs match agreed mapping
- public/app/db tiers are clearly separated
- no NAT resources present

#### Validation
- synth output inspection
- CDK assertion tests for subnet count and CIDRs

---

### M4 — Endpoint-first private access
#### Scope
- Add only the endpoints required for the current phase
- Keep app and DB subnets private
- Preserve least-privilege routing and security posture

#### Done Definition
- selected VPC endpoints synth correctly
- route tables remain minimal
- SGs remain least privilege

#### Validation
- synth output inspection
- CDK assertion tests for endpoints and route tables

---

### M5 — Security groups and flow model
#### Scope
- Web SG
- App SG
- DB SG
- Optional app-to-app SGs for least-privilege flows
- Self-referencing app rules only if justified

#### Done Definition
- SG rules match the spec
- no CIDR-based DB ingress
- no broad unnecessary ingress rules

#### Validation
- CDK assertion tests for SG rules
- design review against spec

---

### M6 — Runtime validation gate
#### Scope
- Validate whether planned workloads can operate without NAT
- Record evidence
- Decide whether NAT remains unnecessary or must be added in the next milestone

#### Done Definition
- evidence captured in session log and decisions log
- explicit NAT decision recorded

#### Validation
- ECS/Fargate runtime checks when workload phase exists
- evidence logged in `docs/decisions.md`

---

### M7 — Optional single NAT phase
#### Scope
- Add exactly one NAT Gateway only if M6 proves it is required
- Document trade-offs: SPOF and cross-AZ data charges

#### Done Definition
- one NAT only
- only required private subnet routes point to it
- rationale recorded

#### Validation
- synth output inspection
- route table assertions
- decision record updated

## Stop Rules
- Do not move to the next milestone until the current one is validated.
- If the scope changes, update `docs/progress/progress.json` and `docs/decisions.md` first.
- If a design assumption changes, record it before implementation.