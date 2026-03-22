## Multiple Testing Correction

**Default rule: collect ALL p-values before correcting.**

When per-family correction IS appropriate:
- Cluster markers: correct separately per cluster
- Multi-omic integration: correct separately per omic layer

Common pitfall: Correcting p-values within each analysis step separately rather than globally — this inflates FDR.
