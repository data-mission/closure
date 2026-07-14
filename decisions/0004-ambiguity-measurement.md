# 0004 — Preserved ambiguity (P): embedding model, clustering, dispersion

- Status: proposed
- Deciders: closure research program contributors
- Scope: E0 (two of its seven sub-indicators)

## Context
E0's protocol names preserved ambiguity as "N=10 generations, embedding/NLI clustering, dispersion score" and
names two sub-indicators (cluster count, dispersion). The "embedding/NLI" slash is an unresolved choice, and no
embedding model, clustering algorithm, or dispersion metric is fixed. The clustering algorithm in particular
determines the cluster-count sub-indicator directly.

## Decision
- **Embedding model:** `nomic-ai/nomic-embed-text-v1.5` (pin the revision) — a current CPU-viable sentence
  embedder. Lower-latency alternative: `BAAI/bge-small-en-v1.5`. This resolves the "embedding/NLI" choice toward
  embeddings.
- **Clustering:** `sklearn.cluster.HDBSCAN` (built into scikit-learn since 1.3; not the standalone `hdbscan`
  package, which can differ on identical parameters). Global `min_cluster_size = 2`, never tuned per item.
  `cluster_count` = number of clusters returned, with noise points counted as singletons. **Not k-means** —
  k-means requires the number of clusters to be supplied, which would bias the very sub-indicator being measured;
  a density method discovers the count instead.
- **Distance:** cosine; HDBSCAN derives its density boundary from `min_cluster_size`, so there is no separately
  hand-set cutoff.
- **Dispersion:** mean pairwise cosine distance over the 10 embeddings (no centroid — a centroid would presuppose
  a single cluster, which cluster-count may contradict).
- **Unit:** the 10 `conclusion` fields (N = 10 generations at the 0001 sampler), aligning P with R's focus on the
  conclusion rather than full output text.

## Consequences
Defines P as two numbers for E0's seven sub-indicators. The clustering algorithm is the single
highest-contamination choice in the whole measurement: a wrong pick (k-means) would make the cluster-count
sub-indicator partly a function of the analyst's assumed k rather than the model's behavior. Fixing a
count-discovering method with one global parameter closes that.
