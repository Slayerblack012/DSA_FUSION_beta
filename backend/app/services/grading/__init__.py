"""
DSA AutoGrader - Grading Sub-Package.

Splits the monolithic ast_grader.py into focused modules:
- constants         : Scoring constants & data classes
- pep8              : PEP8 style checking
- extractor         : AST feature extraction
- scorer            : DSA algorithm scoring
- test_runner       : Static & dynamic test scoring
- batch_test_runner : Efficient batch test execution
- grader            : Main orchestrator (DSALightningGrader)
"""

from app.services.grading.batch_test_runner import (
    BatchTestReport,
    BatchTestRunner,
    TestCase,
    TestCaseResult,
    load_test_cases,
    run_batch_from_directory,
    run_batch_tests,
)
from app.services.grading.constants import SCORING_CONSTANTS, CodeFeatures
from app.services.grading.extractor import ASTFeatureExtractor
from app.services.grading.grader import DSALightningGrader
from app.services.grading.scorer import DSAScorer

__all__ = [
    "SCORING_CONSTANTS",
    "CodeFeatures",
    "ASTFeatureExtractor",
    "DSAScorer",
    "DSALightningGrader",
    "BatchTestRunner",
    "BatchTestReport",
    "TestCase",
    "TestCaseResult",
    "load_test_cases",
    "run_batch_tests",
    "run_batch_from_directory",
]
