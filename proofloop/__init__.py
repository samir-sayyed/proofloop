"""ProofLoop: accept an agent-written Android UI test only after proving it.

A test is proven when it passes on every clean run of the good build and fails
at the expected checkpoint on every proof-bug build. The verdict is computed by
plain code; no model decides whether a test is proven.
"""

__version__ = "0.1.0"
RECORD_SCHEMA_VERSION = 2  # 2: artifact hashes, plan-bound approval, proof bugs after the first good run
