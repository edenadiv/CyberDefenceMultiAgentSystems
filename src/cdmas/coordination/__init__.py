"""MAS coordination protocols (SDD §4): auction, coalition, voting, failure/resilience.

Each module exposes the pure algorithm (deterministic, unit-testable) plus the message
types the agents exchange. Agent integration lives in the agent packages; these modules
hold the decision logic so the SRS functional requirements can be asserted directly.
"""
