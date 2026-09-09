"""Reconstruct independently checkable extra-reuse witnesses from a recorded run."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from benchmark import archive
from research import glucose_sat
from satcache import check


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True)
    parser.add_argument("--rti", required=True)
    parser.add_argument("--bms", required=True)
    parser.add_argument("--output", default="results/reuse-certificates.json")
    args = parser.parse_args()
    results = json.loads(Path(args.results).read_text())
    formulas = {}
    for kind, path in (("RTI", args.rti), ("BMS", args.bms)):
        if sha256(Path(path).read_bytes()).hexdigest() != results["archives"][kind]["sha256"]:
            raise ValueError("Archive hash mismatch")
        for name, formula, digest in archive(path).values():
            formulas[name] = (formula, digest)
    certificates = []
    for witness in results["nonisomorphic_reuse_witnesses"]:
        source, source_digest = formulas[witness["source"]]
        query, query_digest = formulas[witness["query"]]
        cert = glucose_sat(source)
        if cert is None or not check(query, cert):
            raise ValueError("Cannot reconstruct transferred model")
        if len(source) == len(query):
            raise ValueError("Clause count does not separate isomorphism classes")
        certificates.append(dict(**witness, source_sha256=source_digest,
                                 query_sha256=query_digest, assignment=cert.assignment))
    Path(args.output).write_text(json.dumps(dict(
        note="Models independently regenerated from recorded sources and checked on queries; "
             "not a byte-for-byte log of timed-run models.",
        certificates=certificates), indent=2)+"\n")
    print(f"Independently checked {len(certificates)} non-isomorphic SAT model transfers")


if __name__ == "__main__":
    main()
