"""
DSA AutoGrader - Test Case Loader.

Loads test cases for dynamic testing.
"""

import logging
import os
from typing import Dict, List

from app.core.config import TESTCASE_ROOT

logger = logging.getLogger("dsa.testcases")


def get_test_cases(topic: str = None) -> List[Dict]:
    """
    Get test cases for a topic.

    Args:
        topic: Topic name (folder name)

    Returns:
        List of test case dictionaries
    """
    if not topic:
        return []

    testcase_dir = os.path.join(TESTCASE_ROOT, topic)

    if not os.path.exists(testcase_dir):
        logger.debug("No testcases found for topic: %s", topic)
        return []

    test_cases = []

    # Look for input files with various suffixes
    for filename in os.listdir(testcase_dir):
        # Support both .input and input_*.txt
        test_id = None
        if filename.endswith(".input"):
            test_id = filename[:-6]
        elif filename.startswith("input_") and filename.endswith(".txt"):
            test_id = filename[6:-4]
            
        if test_id:
            input_file = os.path.join(testcase_dir, filename)
            # Try matching output file
            output_file = os.path.join(testcase_dir, f"{test_id}.output")
            if not os.path.exists(output_file):
                output_file = os.path.join(testcase_dir, f"output_{test_id}.txt")

            if os.path.exists(output_file):
                try:
                    with open(input_file, "r", encoding="utf-8") as f:
                        input_str = f.read()
                    with open(output_file, "r", encoding="utf-8") as f:
                        expected_output = f.read()

                    test_cases.append(
                        {
                            "id": test_id,
                            "name": f"Test Case {test_id}",
                            "input": input_str.strip(),
                            "expected": expected_output.strip(),
                        }
                    )
                except Exception as e:
                    logger.error("Failed to load test case %s: %s", test_id, e)

    logger.debug("Loaded %d test cases for %s", len(test_cases), topic)
    return test_cases


def get_all_topics() -> List[str]:
    """Get all available test case topics."""
    if not os.path.exists(TESTCASE_ROOT):
        return []

    topics = []
    for item in os.listdir(TESTCASE_ROOT):
        item_path = os.path.join(TESTCASE_ROOT, item)
        if os.path.isdir(item_path):
            topics.append(item)

    return sorted(topics)


def save_test_case(topic: str, test_id: str, input_str: str, expected_output: str) -> bool:
    """Save a new test case."""
    try:
        topic_dir = os.path.join(TESTCASE_ROOT, topic)
        if not os.path.exists(topic_dir):
            os.makedirs(topic_dir)
            
        input_file = os.path.join(topic_dir, f"{test_id}.input")
        output_file = os.path.join(topic_dir, f"{test_id}.output")
        
        with open(input_file, "w", encoding="utf-8") as f:
            f.write(input_str)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(expected_output)
            
        logger.info("Saved test case %s for topic %s", test_id, topic)
        return True
    except Exception as e:
        logger.error("Failed to save test case: %s", e)
        return False


def delete_test_case(topic: str, test_id: str) -> bool:
    """Delete a test case."""
    try:
        topic_dir = os.path.join(TESTCASE_ROOT, topic)
        input_file = os.path.join(topic_dir, f"{test_id}.input")
        output_file = os.path.join(topic_dir, f"{test_id}.output")
        
        if os.path.exists(input_file):
            os.remove(input_file)
        if os.path.exists(output_file):
            os.remove(output_file)
            
        logger.info("Deleted test case %s from topic %s", test_id, topic)
        return True
    except Exception as e:
        logger.error("Failed to delete test case: %s", e)
        return False
