# Second readiness screen: six-regular graph candidates

The first fixed screen (5-regular graphs, six inputs) returned six checked SAT
models and no eligible UNSAT pairs. Keep all those results. Before any history
transfer measurement, screen this fixed second batch:

| Vertices | H seed | T seed | Degree |
|---:|---:|---:|---:|
| 120 | 6200 | 6201 | 6 |
| 200 | 6202 | 6203 | 6 |
| 320 | 6204 | 6205 | 6 |

Increase graph degree to seek UNSAT candidates, not to optimize history wins.
Same independent graph generator, same one-hot coloring encoding, same three
CNF-only methods and 15-second process caps. No planting, retained historical
support, symmetry-breaking hints, or resampling of a seed. Any SAT/timeouts
remain visible. This is an explicitly adaptive domain-readiness screen;
neither batch is a preregistered confirmatory transfer experiment. If this
batch yields no usable proofs, report the limitation rather than synthesizing
a replacement-clause family. No BLIND or repair result informed either screen.
