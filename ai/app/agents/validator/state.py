from __future__ import annotations
from typing import TypedDict, List, Dict, Any, Optional
from app.schemas.fact import FactSet
from app.schemas.claim import ValidatedClaims

# Internal models can be defined here or imported if they are in a shared location.
# For now, since they were inner classes or local to the agent, we might need to define them here 
# or keep them in a utils file. 
# Given the plan, let's put the internal CanonicalClaim class in nodes.py or a separate internal model file?
# Ideally `state` should just type hints.
# Let's import Any for now for the internal classes if they are not yet separated, 
# but strictly we should probably define them in `models.py` inside the validator package 
# or just use `Any` if we want to avoid circular imports before nodes.py is ready.

# Actually, the implementation plan didn't specify a `models.py` for internal classes.
# I will define `CanonicalClaim` in a `models.py` inside validator to be clean, 
# or just keep it in `nodes.py` if it's functional. 
# However, keeping it in `state.py` might be messy.
# Let's use `Any` for internal complex objects in the TypedDict for now to avoid circular dependency hell,
# or better yet, define the internal dataclasses in `app/agents/validator/internal_models.py`?
# I'll stick to defining the State now.

class ValidatorState(TypedDict, total=False):
    # Input
    fact_set: FactSet
    
    # Internal
    canonical_claims: List[Any] # List[CanonicalClaim]
    clusters: Dict[tuple, List[Any]] # Dict[Key, List[CanonicalClaim]]
    
    # Output
    validated_claims: ValidatedClaims
