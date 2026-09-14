"""Reproducible observational instrumentation, no heuristic/config changes.

Input source is the original Glucose 3.0 archive bundled by installed PySAT.
Build both counted and counter-disabled binaries to check identical traces.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f'Unexpected source anchor count: {old[:70]}')
    return text.replace(old, new)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--archive', default='/private/tmp/python_sat-1.9.dev15/solvers/glucose30.tar.gz')
    ap.add_argument('--build', default='/private/tmp/satfinding-native-cdcl')
    args = ap.parse_args()
    build = Path(args.build)
    build.mkdir(parents=True, exist_ok=True)
    with tarfile.open(args.archive) as archive:
        for member in archive.getmembers():
            destination = (build/member.name).resolve()
            if build.resolve() not in destination.parents or not (member.isdir() or member.isfile()):
                raise ValueError('Unsafe archive member')
        archive.extractall(build)
    root = build/'glucose-3.0'
    # Syntax-only compatibility fixes for current Clang; same in both builds.
    types = root/'core/SolverTypes.h'
    compatible = replace_once(types.read_text(), 'friend Lit mkLit(Var var, bool sign = false);',
                              'friend Lit mkLit(Var var, bool sign);')
    compatible = replace_once(compatible, 'mkLit     (Var var, bool sign)',
                              'mkLit     (Var var, bool sign = false)')
    types.write_text(compatible)
    options = root/'utils/Options.h'
    options.write_text(options.read_text().replace('"PRIi64', '" PRIi64'))
    source = root/'core/Solver.cc'
    original = source.read_text()
    instrumented = '''
unsigned long long sf_analysis=0, sf_redundancy=0, sf_binary=0;
#ifdef SATFINDING_COUNTERS_OFF
#define SF_COUNT(x) ((void)0)
#else
#define SF_COUNT(x) (++(x))
#endif
''' + original
    instrumented = replace_once(instrumented,
        'Clause& c = ca[confl];\n\n\t// Special case for binary clauses',
        'Clause& c = ca[confl];\n        if (p != lit_Undef) SF_COUNT(sf_analysis);\n\n\t// Special case for binary clauses')
    instrumented = replace_once(instrumented,
        'Clause& c = ca[reason(var(analyze_stack.last()))]; analyze_stack.pop();',
        'Clause& c = ca[reason(var(analyze_stack.last()))]; analyze_stack.pop();\n        SF_COUNT(sf_redundancy);')
    instrumented = replace_once(instrumented,
        'Clause& c = ca[reason(var(out_learnt[i]))];',
        'Clause& c = ca[reason(var(out_learnt[i]))];\n                SF_COUNT(sf_redundancy);')
    instrumented = replace_once(instrumented,
        'for(int k = 0;k<wbin.size();k++) {\n      Lit imp',
        'for(int k = 0;k<wbin.size();k++) {\n      SF_COUNT(sf_binary);\n      Lit imp')
    source.write_text(instrumented)
    driver = Path('native_cdcl.cc').resolve()
    common = ['c++', '-O3', '-DNDEBUG', '-std=c++11', '-Wno-deprecated',
              '-I'+str(root), str(driver), str(source), str(root/'utils/Options.cc'),
              str(root/'utils/System.cc'), '-lz']
    binaries = {}
    for mode, extra in (('counted', []), ('control', ['-DSATFINDING_COUNTERS_OFF'])):
        target = build/mode
        subprocess.run(common+extra+['-o', str(target)], check=True)
        binaries[mode] = dict(path=str(target), sha256=hashlib.sha256(target.read_bytes()).hexdigest())
    meta = dict(archive=str(Path(args.archive).resolve()),
                archive_sha256=hashlib.sha256(Path(args.archive).read_bytes()).hexdigest(),
                source_original_sha256=hashlib.sha256(original.encode()).hexdigest(),
                source_instrumented_sha256=hashlib.sha256(instrumented.encode()).hexdigest(),
                driver_sha256=hashlib.sha256(driver.read_bytes()).hexdigest(),
                builder_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                compatibility_fixes=['C++11 PRIi64 token spacing', 'move mkLit default argument from friend declaration to definition'],
                compiler=subprocess.check_output(['c++', '--version'], text=True),
                binaries=binaries,
                metrics=dict(analysis_resolution_steps='noninitial antecedent visits in first-UIP analysis',
                    minimization_reason_visits='reason-clause visits in recursive/basic learned-clause minimization',
                    binary_minimization_candidates='binary watcher candidates inspected by minimization'),
                limitation='These are native CDCL work counters, not old enumerator attempts; BCP/decisions are separate.')
    (build/'build.json').write_text(json.dumps(meta, indent=2))
    print(json.dumps(binaries))


if __name__ == '__main__':
    main()
