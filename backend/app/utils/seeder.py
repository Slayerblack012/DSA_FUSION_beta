"""
DSA AutoGrader - Database Seeder.

Seed sample data for testing and demonstration.
"""

import logging
from datetime import datetime, timedelta
from app.containers.container import get_container
from app.utils.auth import hash_password

logger = logging.getLogger("dsa.seeder")


def seed_demo_data():
    """Seed demo data for testing."""
    logger.info("Starting data seeding...")
    
    container = get_container()
    repo = container.get_repository()
    
    # 1. Create demo users
    logger.info("Creating demo users...")
    
    users_to_create = [
        {
            "username": "122000001",
            "password": "sv123",
            "full_name": "Nguyễn Văn A",
            "role": "STUDENT"
        },
        {
            "username": "122000002",
            "password": "sv123",
            "full_name": "Trần Thị B",
            "role": "STUDENT"
        },
        {
            "username": "122000003",
            "password": "sv123",
            "full_name": "Lê Văn C",
            "role": "STUDENT"
        }
    ]
    
    for user_data in users_to_create:
        if not repo.get_user_by_username(user_data["username"]):
            user_id = repo.create_user(
                username=user_data["username"],
                password_hash=hash_password(user_data["password"]),
                full_name=user_data["full_name"],
                role=user_data["role"]
            )
            logger.info(f"Created user: {user_data['username']} (ID: {user_id})")
        else:
            logger.info(f"User exists: {user_data['username']}")
    
    # 2. Create demo submissions
    logger.info("Creating demo submissions...")
    
    demo_submissions = [
        {
            "student_id": "122000001",
            "student_name": "Nguyễn Văn A",
            "assignment_code": "DSA2024_BAI1",
            "topic": "Sorting Algorithms",
            "filename": "bubble_sort.py",
            "code": """def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr

# Test
arr = [64, 34, 25, 12, 22, 11, 90]
sorted_arr = bubble_sort(arr)
print("Sorted array:", sorted_arr)
""",
            "total_score": 8.5,
            "final_score": 8.5,
            "status": "AC",
            "algorithms_detected": ["Bubble Sort", "Sorting"],
            "plagiarism_detected": False,
            "submitted_at": datetime.now() - timedelta(days=2, hours=5)
        },
        {
            "student_id": "122000002",
            "student_name": "Trần Thị B",
            "assignment_code": "DSA2024_BAI1",
            "topic": "Sorting Algorithms",
            "filename": "quick_sort.py",
            "code": """def quick_sort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + middle + quick_sort(right)

# Test
arr = [64, 34, 25, 12, 22, 11, 90]
sorted_arr = quick_sort(arr)
print("Sorted array:", sorted_arr)
""",
            "total_score": 9.0,
            "final_score": 9.0,
            "status": "AC",
            "algorithms_detected": ["Quick Sort", "Sorting", "Divide and Conquer"],
            "plagiarism_detected": False,
            "submitted_at": datetime.now() - timedelta(days=1, hours=10)
        },
        {
            "student_id": "122000003",
            "student_name": "Lê Văn C",
            "assignment_code": "DSA2024_BAI1",
            "topic": "Sorting Algorithms",
            "filename": "insertion_sort.py",
            "code": """def insertion_sort(arr):
    for i in range(1, len(arr)):
        key = arr[i]
        j = i - 1
        while j >= 0 and key < arr[j]:
            arr[j + 1] = arr[j]
            j -= 1
        arr[j + 1] = key
    return arr

# Test
arr = [64, 34, 25, 12, 22, 11, 90]
sorted_arr = insertion_sort(arr)
print("Sorted array:", sorted_arr)
""",
            "total_score": 7.5,
            "final_score": 7.5,
            "status": "AC",
            "algorithms_detected": ["Insertion Sort", "Sorting"],
            "plagiarism_detected": False,
            "submitted_at": datetime.now() - timedelta(hours=3)
        },
        {
            "student_id": "122000001",
            "student_name": "Nguyễn Văn A",
            "assignment_code": "DSA2024_BAI2",
            "topic": "Binary Search Tree",
            "filename": "bst.py",
            "code": """class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def insert_bst(root, val):
    if not root:
        return TreeNode(val)
    if val < root.val:
        root.left = insert_bst(root.left, val)
    else:
        root.right = insert_bst(root.right, val)
    return root

# Test
root = None
for val in [50, 30, 70, 20, 40, 60, 80]:
    root = insert_bst(root, val)
print("BST created successfully")
""",
            "total_score": 6.0,
            "final_score": 6.0,
            "status": "WA",
            "algorithms_detected": ["Binary Search Tree", "Tree Traversal"],
            "plagiarism_detected": False,
            "submitted_at": datetime.now() - timedelta(days=5)
        }
    ]
    
    # Save submissions
    saved_count = 0
    for sub in demo_submissions:
        try:
            result_dict = {
                "job_id": f"demo_{sub['student_id']}_{sub['assignment_code']}",
                "student_id": sub["student_id"],
                "student_name": sub["student_name"],
                "assignment_code": sub["assignment_code"],
                "filename": sub["filename"],
                "topic": sub["topic"],
                "total_score": sub["total_score"],
                "final_score": sub["final_score"],
                "status": sub["status"],
                "algorithms_detected": sub["algorithms_detected"],
                "plagiarism_detected": sub["plagiarism_detected"],
                "code": sub["code"],
                "language": "python"
            }
            
            repo.save_result(result_dict)
            saved_count += 1
            logger.info(f"Saved submission: {sub['filename']} by {sub['student_name']}")
            
        except Exception as e:
            logger.error(f"Failed to save submission: {e}")
    
    logger.info(f"Seeding complete! Created {saved_count} demo submissions.")
    
    return {
        "users_created": len(users_to_create),
        "submissions_created": saved_count
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = seed_demo_data()
    print("\n✅ Seeding completed!")
    print(f"   Users: {result['users_created']}")
    print(f"   Submissions: {result['submissions_created']}")
