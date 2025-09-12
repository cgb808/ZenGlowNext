# Swarm Optimizers: ACO (Exploration) + PSO (Exploitation)

Pipeline Concept:
1. Ant Colony Optimization (ACO) explores the combinatorial factor space to surface K (3-5) diverse candidate "paths" (factor sets) strongly correlated with a user query / objective.
2. Particle Swarm Optimization (PSO) then locally optimizes continuous / numeric parameters inside each fixed factor combination, refining dosage, timing, thresholds.
3. Predictive hook (lightweight logistic / heuristic) can bias ACO pheromone update or PSO velocity dampening based on longitudinal feedback.

Terminology:
- Factor: Categorical or binary inclusion dimension (e.g., Vitamin D, Morning Sunlight, Low Sugar Diet).
- Parameter: Tunable numeric attached to a factor (e.g., IU dose, minutes, grams).
- Path: Ordered or unordered set of factors with optional parameter ranges.

Proposed Data Flow:
query -> feature extraction -> ACO explorer.find_paths(query) -> candidate_paths[]
Each path -> PSOOptimizer.refine_path(path, query) -> optimized_path
Aggregate -> rank (optionally re-score with predictive controller) -> respond

Stub Behaviors (current implementation goal):
- ACO returns mock paths with synthetic relevance scores & factor provenance.
- PSO refines by adding numeric suggestions + simple improvement metric.
- Orchestrator coordinates sequential execution (future: parallel + early stopping).

Extensibility Hooks:
- inject_predictive(features) -> adjustments {pheromone_delta, velocity_scale}
- feedback_sink(event) -> append JSONL for training future models.

Future Enhancements:
- Historical performance weighting in pheromone update.
- Diversity penalty (Jaccard) among candidate paths.
- Bayesian refinement for parameter confidence intervals.
- GPU accelerated vector similarity retrieving prior best paths as warm start.

Security / Safety Considerations:
- Add rule-based filter to remove medically unsafe dosage suggestions before returning.
- Provide confidence & disclaimers for health-related recommendations.

Version: 0.1 (scaffolding)
