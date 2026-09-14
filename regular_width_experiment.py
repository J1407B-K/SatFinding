"""Simple random 6-regular graphs, spectral diagnostics, paired XOR encodings."""
import csv
import hashlib
import json
import time
from pathlib import Path

import networkx as nx
import numpy as np
from scipy.sparse.linalg import eigsh

from extension_width_experiment import build
from paired_width_analysis import analyze


def main():
    prefix = Path('results/extension_regular6_sampled')
    fields = ['n', 'seed', 'method', 'extended', 'width', 'original_vars',
              'total_vars', 'extension_vars', 'width_per_original',
              'width_per_total', 'seconds', 'degree', 'connected',
              'lambda2', 'normalized_gap', 'edge_expansion_lower_bound', 'graph_sha256']
    with open(str(prefix)+'_raw.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for n in (80, 160, 320, 640):
            for seed in range(10):
                graph = nx.random_regular_graph(6, n, seed=seed)
                assert not graph.is_multigraph() and nx.number_of_selfloops(graph) == 0
                assert all(d == 6 for _, d in graph.degree())
                assert nx.is_connected(graph)
                edges = sorted(tuple(sorted(e)) for e in graph.edges())
                digest = hashlib.sha256(json.dumps(edges).encode()).hexdigest()
                matrix = nx.to_scipy_sparse_array(graph, nodelist=range(n), dtype=float)
                vals = eigsh(matrix, k=2, which='LA', return_eigenvectors=False,
                             v0=np.random.default_rng(seed).normal(size=n), tol=1e-10)
                lambda2 = float(sorted(vals)[-2])
                for ext in (False, True):
                    start = time.perf_counter()
                    orig, total, width = build(n, 6, ext, seed, 'sampled', edges=edges)
                    assert orig == 3*n and total == (7*n if ext else 3*n)
                    writer.writerow(dict(n=n, seed=seed, method='sampled', extended=ext,
                        width=width, original_vars=orig, total_vars=total,
                        extension_vars=total-orig, width_per_original=width/orig,
                        width_per_total=width/total, seconds=time.perf_counter()-start,
                        degree=6, connected=True, lambda2=lambda2,
                        normalized_gap=1-lambda2/6,
                        edge_expansion_lower_bound=(6-lambda2)/2, graph_sha256=digest))
                    f.flush()
                print(f'n={n}, seed={seed}: complete; normalized gap={1-lambda2/6:.4f}', flush=True)
    analyze(str(prefix)+'_raw.csv', str(prefix)+'_paired')


if __name__ == '__main__':
    main()
