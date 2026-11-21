# Root-file inspection register

**Repository:** NeuralBlitz/LRS-NeuralBlitz. **Baseline:** `e54ac39bfd053740f5af152bfe2fa6fc2aa72a23` (November 21, 2026). **Scope: 110 Git-tracked root entries.** This document intentionally treats every file separately rather than equating a whole-tree scanner with a complete semantic or functional review.

**Method:** Source and documentation were retrieved for targeted inspection of Python imports/classes/functions/entry points, Markdown headings/introductory claims, JSON structures, and root configurations; key gateway and deployment functions were inspected more deeply. Binary objects, symlinks, and external Gitlinks have explicit inspection boundaries. This register is **not** a line-by-line correctness audit, a successful execution of every implementation, or certification of scientific claims. The CI consistency gate requires a row for each tracked root path and flags additions/removals.

## Individually indexed root files

| Tracked path | Purpose/topic | Inspection method | Finding or next verification |
| --- | --- | --- | --- |
| `.coverage` | coverage | Binary (not semantically decoded) | Binary coverage artifact; current test coverage cannot be inferred. Review provenance/privacy before removal. |
| `.env.example` | env | Configuration/source (reviewed) | Placeholder secrets only; operational credentials and rotation have not been verified. |
| `.eslintrc.cjs` | eslintrc | Configuration/source (reviewed) | Minimal lint rules; type-aware security review remains. |
| `.gitignore` | gitignore | Configuration/source (reviewed) | Tracked caches remain tracked despite ignore patterns. |
| `.gitmodules` | gitmodules | Configuration/source (reviewed) | Only lrs_agents is mapped although the repository has four Gitlinks. |
| `.lrsgate` | lrsgate | Configuration/source (reviewed) | Architecture illustration, not a verified operating service. |
| `.replit` | replit | Configuration/source (reviewed) | Autoscales an index.js stub, not a working web service; misleading deployment contract. |
| `advanced_autonomous_agent_framework_README.md` | advanced autonomous agent framework README | Markdown (sections, introductions and claims sampled) | Contains technical or research claims; examples not integration-tested. |
| `advanced_autonomous_agent_framework.py` | advanced autonomous agent framework | Python source (imports/classes/entry point sampled) | Async in-memory demo; no authenticated multi-host execution. |
| `agent_communication_protocols.md` | agent communication protocols | Markdown (sections, introductions and claims sampled) | Contains technical or research claims; examples not integration-tested. |
| `AGENTS.md` | AGENTS | Markdown (sections, introductions and claims sampled) | Long architectural instruction document; targeted headings/sections reviewed, not independently verified as implemented. |
| `Automated_Charter_Enforcement_Report.md` | Automated Charter Enforcement Report | Markdown (sections, introductions and claims sampled) | Contains technical or research claims; examples not integration-tested. |
| `autonomous_self_evolution_simplified.py` | autonomous self evolution simplified | Python source (imports/classes/entry point sampled) | Illustrative self-evolution rules, not audited autonomous code deployment. |
| `autonomous_self_evolution_upgrades_report.py` | autonomous self evolution upgrades report | Python source (imports/classes/entry point sampled) | Research algorithms; no integration/guardrail proof. |
| `autonomous_self_evolution_UPGRADES_SUMMARY.md` | autonomous self evolution UPGRADES SUMMARY | Markdown (sections, introductions and claims sampled) | Contains technical or research claims; examples not integration-tested. |
| `bci_security_framework.md` | bci security framework | Markdown (sections, introductions and claims sampled) | Custom brain-signal security protocol requires cryptanalysis and equipment tests. |
| `bci_security_implementation.py` | bci security implementation | Python source (imports/classes/entry point sampled) | Neural authentication/crypto examples have no independent safety/security assessment. |
| `bioinformatics_ck_contracts.json` | bioinformatics ck contracts | JSON (parsed; semantics not proven) | JSON contract existence does not prove output accuracy. |
| `BIOINFORMATICS_CK_REPORT.md` | BIOINFORMATICS CK REPORT | Markdown (sections, introductions and claims sampled) | Contains technical or research claims; examples not integration-tested. |
| `bioinformatics_ck.py` | bioinformatics ck | Python source (imports/classes/entry point sampled) | Biopython models/biology data and numerical accuracy untested. |
| `BLOCKCHAIN_IMPLEMENTATION_REPORT.md` | BLOCKCHAIN IMPLEMENTATION REPORT | Markdown (sections, introductions and claims sampled) | Claims implementation complete; live Ethereum/Fabric integrations not evidenced. |
| `BLOCKCHAIN_INTEGRATION_REPORT.md` | BLOCKCHAIN INTEGRATION REPORT | Markdown (sections, introductions and claims sampled) | Contains production-ready wording without on-chain integration tests. |
| `blockchain_integration.py` | blockchain integration | Python source (imports/classes/entry point sampled) | SDK integrations not tested against live chains, identity or wallets. |
| `bun.lock` | bun | Lockfile (metadata inspected) | Locked Bun install passes CI; dependency audit is separate. |
| `chromadb_integration.py` | chromadb integration | Python source (imports/classes/entry point sampled) | Persistence/SDK compatibility untested. |
| `ck_data_quality_assessment_schema.json` | ck data quality assessment schema | JSON (parsed; semantics not proven) | Valid JSON structure alone does not verify schema or live behavior. |
| `ck_data_quality_assessment.py` | ck data quality assessment | Python source (imports/classes/entry point sampled) | Runs and dependencies require isolated tests; source inspection is not a passing test. |
| `ck_data_science_suite_report.md` | ck data science suite report | Markdown (sections, introductions and claims sampled) | OPERATIONAL status is not evidence of end-to-end data science pipeline. |
| `ck_feature_engineering_automation_schema.json` | ck feature engineering automation schema | JSON (parsed; semantics not proven) | Valid JSON structure alone does not verify schema or live behavior. |
| `ck_feature_engineering_automation.py` | ck feature engineering automation | Python source (imports/classes/entry point sampled) | Runs and dependencies require isolated tests; source inspection is not a passing test. |
| `ck_ml_automated_pipeline_schema.json` | ck ml automated pipeline schema | JSON (parsed; semantics not proven) | Valid JSON structure alone does not verify schema or live behavior. |
| `ck_ml_automated_pipeline.py` | ck ml automated pipeline | Python source (imports/classes/entry point sampled) | Runs and dependencies require isolated tests; source inspection is not a passing test. |
| `CODE_GENERATION_CK_REPORT.md` | CODE GENERATION CK REPORT | Markdown (sections, introductions and claims sampled) | Production-ready CK statement lacks isolated runtime and threat-model tests. |
| `CODE_OF_CONDUCT.md` | CODE OF CONDUCT | Markdown (sections, introductions and claims sampled) | Contains technical or research claims; examples not integration-tested. |
| `consensus_mechanisms_report.md` | consensus mechanisms report | Markdown (sections, introductions and claims sampled) | Contains technical or research claims; examples not integration-tested. |
| `consensus_protocols_report.md` | consensus protocols report | Markdown (sections, introductions and claims sampled) | Contains technical or research claims; examples not integration-tested. |
| `CONTRIBUTING.md` | CONTRIBUTING | Markdown (sections, introductions and claims sampled) | Contains technical or research claims; examples not integration-tested. |
| `CV_CAPABILITY_KERNELS_REPORT.md` | CV CAPABILITY KERNELS REPORT | Markdown (sections, introductions and claims sampled) | CV metrics and face/emotion use require datasets, bias/privacy assessment and consent. |
| `cv_capability_kernels.py` | cv capability kernels | Python source (imports/classes/entry point sampled) | GPU/dataset/face privacy evaluation pending. |
| `cybersecurity_ck_registry.json` | cybersecurity ck registry | JSON (parsed; semantics not proven) | Registry schema does not demonstrate detector efficacy. |
| `deployment_goldendag.json` | deployment goldendag | JSON (parsed; semantics not proven) | Synthetic event hashes, not externally attested deployments. |
| `deployment_summary.py` | deployment summary | Python source (imports/classes/entry point sampled) | Generates simulated counts but labels millions of agents deployed/active. |
| `dimensional_computing_demo.py` | dimensional computing demo | Python source (imports/classes/entry point sampled) | Fallback demo is not quantum or higher-dimensional hardware. |
| `DISTRIBUTED_MLMAS_UPGRADES_REPORT.md` | DISTRIBUTED MLMAS UPGRADES REPORT | Markdown (sections, introductions and claims sampled) | Topology scalability assertions are not network-tested. |
| `distributed_mlmas.py` | distributed mlmas | Python source (imports/classes/entry point sampled) | Runs and dependencies require isolated tests; source inspection is not a passing test. |
| `docker-compose.yml` | docker compose | Configuration/source (reviewed) | cAdvisor privileged, five mutable image tags; local configuration only. |
| `EDGE_COMPUTING_REPORT.md` | EDGE COMPUTING REPORT | Markdown (sections, introductions and claims sampled) | Pi/Jetson/Coral instructions not verified on real hardware. |
| `evolutionary_algorithms_report.md` | evolutionary algorithms report | Markdown (sections, introductions and claims sampled) | Contains technical or research claims; examples not integration-tested. |
| `fault_tolerance_layer.py` | fault tolerance layer | Python source (imports/classes/entry point sampled) | Pickle serialization and distributed recovery need adversarial review. |
| `fault_tolerance_report.md` | fault tolerance report | Markdown (sections, introductions and claims sampled) | Contains technical or research claims; examples not integration-tested. |
| `FEDERATED_LEARNING_REPORT.md` | FEDERATED LEARNING REPORT | Markdown (sections, introductions and claims sampled) | Differential privacy and secure aggregation need independent security proofs. |
| `fitness_optimization_report.md` | fitness optimization report | Markdown (sections, introductions and claims sampled) | Contains technical or research claims; examples not integration-tested. |
| `generated-icon.png` | generated icon | Binary (not semantically decoded) | Binary icon packaged; visual/accessibility assessment incomplete. |
| `gg.md` | gg | Markdown (sections, introductions and claims sampled) | Metaphysical/creative codex, not experimental evidence. |
| `governance_ethics_system.py` | governance ethics system | Python source (imports/classes/entry point sampled) | Runs and dependencies require isolated tests; source inspection is not a passing test. |
| `governance_upgrade_report.md` | governance upgrade report | Markdown (sections, introductions and claims sampled) | Production-ready upgrades not independently tested. |
| `graph_databases_report.md` | graph databases report | Markdown (sections, introductions and claims sampled) | Contains technical or research claims; examples not integration-tested. |
| `HierarchicalOrchestration_Report_v20.1.md` | HierarchicalOrchestration Report v20.1 | Markdown (sections, introductions and claims sampled) | Agent hierarchy and command definitions are architecture, not an integrated endpoint. |
| `index.js` | index | Configuration/source (reviewed) | Console/log metadata stub, not HTTP service. |
| `LICENSE` | LICENSE | Configuration/source (reviewed) | No release-level functional validation established. |
| `lrs` | lrs | Symlink (target not followed) | Tracked symlink; destination not recursively inspected. |
| `lrs_agents` | lrs agents | Gitlink (not read) | Gitlink outside this repository; content not inspected. |
| `main.py` | main | Python source (imports/classes/entry point sampled) | Gateway route source inspected; no authenticated ASGI test; work in audit branch removes fabricated status and speeds. |
| `malware_signature_analyzer_ck.py` | malware signature analyzer ck | Python source (imports/classes/entry point sampled) | Demo threat signatures lack ROC/FP/evasion assessment. |
| `MLMAS_RESEARCH_REPORT.md` | MLMAS RESEARCH REPORT | Markdown (sections, introductions and claims sampled) | Composite architectural claims not reproduced as a working system. |
| `mlmas_upgrades_report.py` | mlmas upgrades report | Python source (imports/classes/entry point sampled) | Optional aioredis/aio-pika dependency and multi-node behavior untested. |
| `multi_layered_multi_agent_system.py` | multi layered multi agent system | Python source (imports/classes/entry point sampled) | In-process orchestrator is not evidence of remote agents. |
| `multi_reality_sync_report.md` | multi reality sync report | Markdown (sections, introductions and claims sampled) | Conceptual multi-reality vocabulary not physical experiment. |
| `network_anomaly_detector_ck.py` | network anomaly detector ck | Python source (imports/classes/entry point sampled) | Anomaly thresholds lack benchmark false-positive evidence. |
| `network_topology_optimizer.py` | network topology optimizer | Python source (imports/classes/entry point sampled) | Runs and dependencies require isolated tests; source inspection is not a passing test. |
| `network_topology_report.md` | network topology report | Markdown (sections, introductions and claims sampled) | Contains technical or research claims; examples not integration-tested. |
| `neuralblitz_code_kernels.py` | neuralblitz code kernels | Python source (imports/classes/entry point sampled) | Dynamic code/embedded Flask/pytest prototypes require sandboxing. |
| `NEURALBLITZ_COMPREHENSIVE_ACHIEVEMENTS.md` | NEURALBLITZ COMPREHENSIVE ACHIEVEMENTS | Markdown (sections, introductions and claims sampled) | Historical implementation timeline and performance figures not cross-checked against commits. |
| `neuralblitz_federated_learning.py` | neuralblitz federated learning | Python source (imports/classes/entry point sampled) | DP accounting/security not independently validated; tests not run here. |
| `neuralblitz_federated_pysyft.py` | neuralblitz federated pysyft | Python source (imports/classes/entry point sampled) | Version-sensitive PySyft imports unverified. |
| `NEURALBLITZ_OPENCODE_COLLABORATIVE_ACHIEVEMENTS.md` | NEURALBLITZ OPENCODE COLLABORATIVE ACHIEVEMENTS | Markdown (sections, introductions and claims sampled) | Historical achievement claims require separate commit-linked evidence. |
| `neuralblitz_quantum_upgrades_report.md` | neuralblitz quantum upgrades report | Markdown (sections, introductions and claims sampled) | No hardware quantum-performance replication. |
| `NEURALBLITZ_ROS2_INTEGRATION_REPORT.md` | NEURALBLITZ ROS2 INTEGRATION REPORT | Markdown (sections, introductions and claims sampled) | Robotics integrations not tested on ROS2 hardware. |
| `neuro_symbiotic_demo.py` | neuro symbiotic demo | Python source (imports/classes/entry point sampled) | Fallback simulation does not establish BCI coupling. |
| `NEURO_SYMBIOTIC_UPGRADES_REPORT.md` | NEURO SYMBIOTIC UPGRADES REPORT | Markdown (sections, introductions and claims sampled) | BCI claims need human-safety, device and independent scientific validation. |
| `neuroplasticity_algorithms_report.md` | neuroplasticity algorithms report | Markdown (sections, introductions and claims sampled) | Contains technical or research claims; examples not integration-tested. |
| `OMEGA_CTOS_ARCHITECTURE.md` | OMEGA CTOS ARCHITECTURE | Markdown (sections, introductions and claims sampled) | 5-billion-agent active deployment assertion has no operational infrastructure evidence. |
| `OMEGA_CTOS_VISUALIZATION.txt` | OMEGA CTOS VISUALIZATION | Text (structure sampled) | Symbolic agent topology, not live measurements. |
| `package.json` | package | JSON (parsed; semantics not proven) | Root VS Code extension is pre-release; locked compile/lint tests pass, but Extension Host integration pending. |
| `pinecone_integration.py` | pinecone integration | Python source (imports/classes/entry point sampled) | API integration not exercised with cloud service. |
| `pyproject.toml` | pyproject | Configuration/source (reviewed) | No Python runtime deps declared despite FastAPI/Flask/scientific imports. |
| `quadratic_voting_ck.py` | quadratic voting ck | Python source (imports/classes/entry point sampled) | Runs and dependencies require isolated tests; source inspection is not a passing test. |
| `quantum_foundation_demo.py` | quantum foundation demo | Python source (imports/classes/entry point sampled) | Fallback simulation must not be described as quantum hardware. |
| `raft_consensus.py` | raft consensus | Python source (imports/classes/entry point sampled) | No partition/failure model integration tests. |
| `README_SIMPLE.md` | README SIMPLE | Markdown (sections, introductions and claims sampled) | Legacy Replit immediate launch is unverified and differs from .replit entrypoint. |
| `README.md` | README | Markdown (sections, introductions and claims sampled) | Pre-production boundary stated; keep claims synchronized with CI. |
| `requirements_vector_dbs.txt` | requirements vector dbs | Text (structure sampled) | Broad SDK versions; no isolated lock for vector DB adapters. |
| `research_summary.md` | research summary | Markdown (sections, introductions and claims sampled) | Contains technical or research claims; examples not integration-tested. |
| `SECURITY.md` | SECURITY | Markdown (sections, introductions and claims sampled) | Disclosure policy is not evidence of certified security or runtime authorization. |
| `server.py` | server | Python source (imports/classes/entry point sampled) | Uvicorn launcher requires undeclared Python dependencies; localhost bound. |
| `simple_app.py` | simple app | Python source (imports/classes/entry point sampled) | Prototype counts literal code keywords, not AI or validated benchmarking. |
| `smart_city_energy_management.py` | smart city energy management | Python source (imports/classes/entry point sampled) | Grid safety assumptions have no SCADA/hardware validation. |
| `smart_city_safety_coordination.py` | smart city safety coordination | Python source (imports/classes/entry point sampled) | No validated dispatch integration with emergency services. |
| `smart_city_traffic_optimization.py` | smart city traffic optimization | Python source (imports/classes/entry point sampled) | No operational intersection/traffic-control authorization. |
| `smart_city_unified_controller.py` | smart city unified controller | Python source (imports/classes/entry point sampled) | Integrates simulations, not actual city infrastructure. |
| `SmartCity_Integration_Architecture.md` | SmartCity Integration Architecture | Markdown (sections, introductions and claims sampled) | City infrastructure control not verified in live municipal operations. |
| `STAGE_CLUSTERS_5000_9999_DEPLOYMENT_REPORT.md` | STAGE CLUSTERS 5000 9999 DEPLOYMENT REPORT | Markdown (sections, introductions and claims sampled) | 500-million deployed agents claim has arithmetic simulation, not deployment attestations. |
| `stage_clusters_5000_9999_deployment.py` | stage clusters 5000 9999 deployment | Python source (imports/classes/entry point sampled) | Huge simulated agent counts are not real deployed processes. |
| `tensor_operations_report.md` | tensor operations report | Markdown (sections, introductions and claims sampled) | Contains technical or research claims; examples not integration-tested. |
| `test_neuralblitz_federated_learning.py` | test neuralblitz federated learning | Python source (imports/classes/entry point sampled) | Standalone dependency-heavy tests not exercised by root CI. |
| `tsconfig.json` | tsconfig | JSON (parsed; semantics not proven) | Valid JSON structure alone does not verify schema or live behavior. |
| `uv.lock` | uv | Lockfile (metadata inspected) | Empty project only, does not resolve FastAPI or scientific stack. |
| `voting_mechanisms_report.md` | voting mechanisms report | Markdown (sections, introductions and claims sampled) | Contains technical or research claims; examples not integration-tested. |
| `voting_systems_report_metadata.json` | voting systems report metadata | JSON (parsed; semantics not proven) | Stored OK-200 status is documentary, not external attestation. |
| `weaviate_integration.py` | weaviate integration | Python source (imports/classes/entry point sampled) | Remote service compatibility/data safety untested. |

## Root-level findings requiring remediation

1. **Root API truthfulness:** `main.py` previously reported an active integration without a verified authenticated health probe and advertised unsupported performance/security capabilities in HTML. Audit branch edits make these limits visible and mark integration health unverified, with isolated response tests.
2. **Deployment mismatch:** `.replit` invokes `index.js`, a metadata stub; the Replit autoscale configuration and its advertised service are not equivalent. `pyproject.toml` and `uv.lock` omit dependencies required by the Python gateway and Flask demo.
3. **Simulation presented as deployment:** `deployment_summary.py`, `stage_clusters_5000_9999_deployment.py`, `STAGE_CLUSTERS_5000_9999_DEPLOYMENT_REPORT.md`, and `OMEGA_CTOS_ARCHITECTURE.md` contain large calculated/simulated agent quantities without corroborating worker processes or platform records. Treat as simulation/reference designs, not deployment results.
4. **Scientific and security assertions:** Computer vision, medical/BCI, federation, custom crypto, quantum, voting and smart-city modules require component-specific dependencies, datasets, negative tests and independent review before operational or safety claims.
5. **Repository hygiene:** `.coverage` and `generated-icon.png` are binary; `lrs` is a symlink and `lrs_agents` a Gitlink. External Gitlink content was **not** recursively read.

### Verification tiers

- **Text inspected:** file fetched and targeted sections or symbols examined. This does not imply execution or validation.
- **Structural validation:** parse/build/unit check passed on the applicable commit. Does not imply backend/hardware integration.
- **Not verified:** benchmark, production, deployment, security or scientific claims without appropriate independent evidence.

The next review phase should expand selected root files from *targeted inspection* to full behavioral and security review, with executable tests and artifact links. For nested directories, use the [repository-wide inventory](repository-wide-inspection.md) and the [legacy README claims audit](../readme-claim-audit.md).
