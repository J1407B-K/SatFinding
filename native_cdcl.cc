// Thin driver for unmodified Glucose 3.0 search plus observational counters.
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <zlib.h>
#include "core/Solver.h"
#include "core/Dimacs.h"

extern unsigned long long sf_analysis, sf_redundancy, sf_binary;

int main(int argc, char **argv) {
    if (argc != 4) {
        fprintf(stderr, "usage: native_cdcl input.cnf output.drup conflict_budget\n");
        return 2;
    }
    auto start = std::chrono::steady_clock::now();
    Glucose::Solver solver;
    solver.verbosity = 0;
    solver.certifiedUNSAT = true;
    solver.certifiedOutput = fopen(argv[2], "w");
    if (!solver.certifiedOutput) return 3;
    gzFile in = gzopen(argv[1], "rb");
    if (!in) return 4;
    Glucose::parse_DIMACS(in, solver);
    gzclose(in);
    solver.setConfBudget(atoll(argv[3]));
    Glucose::vec<Glucose::Lit> assumptions;
    Glucose::lbool result = solver.solveLimited(assumptions);
    double seconds = std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
    const char *status = result == Glucose::lbool((uint8_t)0) ? "SAT" :
                         result == Glucose::lbool((uint8_t)1) ? "UNSAT" : "UNKNOWN";
    printf("{\"status\":\"%s\",\"seconds\":%.9f,\"analysis_resolution_steps\":%llu,"
           "\"minimization_reason_visits\":%llu,\"binary_minimization_candidates\":%llu,"
           "\"conflicts\":%llu,\"decisions\":%llu,\"propagations\":%llu}\n",
           status, seconds, sf_analysis, sf_redundancy, sf_binary,
           (unsigned long long)solver.conflicts, (unsigned long long)solver.decisions,
           (unsigned long long)solver.propagations);
    return 0;
}
