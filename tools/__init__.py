"""Developer tools: demos, benchmarks, trace generation, archive freezing.

These modules are *not* part of the library; they are how the numbers and the
printouts in ``docs/`` are produced, so that everything a reader sees can be
regenerated with one command::

    python -m tools.demo          # the guided tour
    python -m tools.bench         # timings and element-read counts
    python -m tools.make_traces   # rewrite docs/traces/*.txt
    python -m tools.freeze_archive
    python -m tools.run_all       # tests + traces + demo, in one go
"""
