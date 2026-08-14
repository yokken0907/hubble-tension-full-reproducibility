# Evidence-coordinate status schema

The F0-F6 coordinates are independent questions, not a score, ladder, ranking, or cumulative grade. A later-coordinate HOLD does not erase an earlier-coordinate PASS, and a coordinate-specific FAIL is not an overall case failure.

- **PASS**: the coordinate question is answered positively within the stated frozen contract.
- **MIXED**: subobjects or parts of the coordinate have different states, or support is explicitly partial.
- **HOLD**: the current public/frozen evidence does not define a unique completion; a named re-entry object is required.
- **FAIL**: a stated coordinate-specific test rejected the tested proposition within its contract.
- **NOT_TESTED**: the coordinate was not tested; no positive or negative inference follows.
- **NOT_APPLICABLE**: the coordinate is outside the declared question for that case.

Coordinates: F0 artifact identity; F1 numerical/output traceability; F2 algebraic representation relation; F3 target-inference invariance or sufficiency; F4 diagnostic/model-support sufficiency; F5 executed lineage/provenance; F6 generative/causal closure.
