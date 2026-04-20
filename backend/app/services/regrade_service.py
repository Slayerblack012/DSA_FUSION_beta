"""
DSA AutoGrader - Regrade Service.

Provides comprehensive regrade functionality for instructors.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.containers.container import get_container
from app.services.grading_service import GradingService

logger = logging.getLogger("dsa.services.regrade")


class RegradeService:
    """
    Service for handling all regrade operations.
    
    Features:
    - Single submission regrade
    - Batch regrade by assignment
    - Full system regrade
    - Progress tracking
    """

    def __init__(self):
        self._container = get_container()
        self._grading_service: GradingService = self._container.get_grading_service()
        self._repository = self._container.get_repository()
        self._job_store = self._container.get_job_store()

    async def regrade_single(
        self,
        submission_id: int,
        reviewer_id: str = "system"
    ) -> Dict[str, Any]:
        """
        Regrade a single submission.
        
        Args:
            submission_id: Submission ID to regrade
            reviewer_id: User triggering the regrade
            
        Returns:
            Result dictionary with new score and status
        """
        logger.info("Starting regrade for submission %d", submission_id)
        
        try:
            # 1. Get original submission
            submission = self._repository.get_result_by_id(submission_id)
            if not submission:
                return {
                    "success": False,
                    "error": "Submission not found",
                    "submission_id": submission_id,
                }

            # 2. Get code
            code = submission.get("code", "")
            if not code:
                return {
                    "success": False,
                    "error": "No code found in submission",
                    "submission_id": submission_id,
                }

            # 3. Re-run grading
            files = [(submission.get("filename", "submission.py"), code)]
            
            result = await self._grading_service.grade_submission(
                files=files,
                topic=submission.get("topic", ""),
                student_name=submission.get("student_name", ""),
                student_id=submission.get("student_id", ""),
                assignment_code=submission.get("assignment_code", ""),
            )

            # 4. Update database
            if result.get("results"):
                new_result = result["results"][0]
                new_score = new_result.get("total_score", 0)
                old_score = submission.get("total_score", 0)
                
                # Update with new score
                self._repository.update_submission_score(
                    submission_id=submission_id,
                    new_score=new_score,
                    reviewer_id=reviewer_id,
                    reason=f"Regraded automatically (old score: {old_score:.1f})",
                    feedback=""
                )

                logger.info(
                    "Regrade completed for %d: %f → %f",
                    submission_id, old_score, new_score
                )

                return {
                    "success": True,
                    "submission_id": submission_id,
                    "old_score": old_score,
                    "new_score": new_score,
                    "score_change": round(new_score - old_score, 1),
                }

            return {
                "success": False,
                "error": "Grading returned no results",
                "submission_id": submission_id,
            }

        except Exception as e:
            logger.error("Regrade failed for %d: %s", submission_id, e, exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "submission_id": submission_id,
            }

    async def regrade_by_assignment(
        self,
        assignment_code: str,
        reviewer_id: str = "system"
    ) -> Dict[str, Any]:
        """
        Regrade all submissions for an assignment.
        
        Args:
            assignment_code: Assignment code to regrade
            reviewer_id: User triggering the regrade
            
        Returns:
            Summary of regrade operation
        """
        logger.info("Starting batch regrade for assignment: %s", assignment_code)
        
        # Create job for tracking
        job_id = f"regrade_{assignment_code}_{int(datetime.now().timestamp())}"
        await self._job_store.set(job_id, {
            "type": "batch_regrade",
            "assignment_code": assignment_code,
            "status": "processing",
            "started_at": datetime.now().isoformat(),
            "progress": {"current": 0, "total": 0},
        })

        try:
            # 1. Get ALL submissions for this assignment (paginate through all pages)
            # BEFORE: Only fetched page=1 (max 1000 submissions, silently truncating rest)
            # AFTER:  Paginates through all pages to get every submission
            submissions = []
            page = 1
            page_size = 500
            while True:
                result = self._repository.get_assignment_scores(
                    assignment_code, page=page, page_size=page_size
                )
                batch = result.get("submissions", [])
                if not batch:
                    break
                submissions.extend(batch)
                if len(batch) < page_size:
                    break  # Last page
                page += 1
                logger.debug("  Loaded page %d: %d submissions", page, len(submissions))
            
            if not submissions:
                await self._job_store.set(job_id, {
                    "type": "batch_regrade",
                    "status": "completed",
                    "message": "No submissions found",
                })
                return {
                    "success": True,
                    "message": "No submissions found for this assignment",
                    "regraded_count": 0,
                }

            # 2. Regrade each submission
            total = len(submissions)
            success_count = 0
            failed_count = 0
            score_changes = []

            for i, sub in enumerate(submissions):
                sub_id = sub.get("id")
                if not sub_id:
                    continue

                result = await self.regrade_single(sub_id, reviewer_id)
                
                if result.get("success"):
                    success_count += 1
                    if result.get("score_change", 0) != 0:
                        score_changes.append({
                            "submission_id": sub_id,
                            "student": sub.get("student_name"),
                            "old": result.get("old_score"),
                            "new": result.get("new_score"),
                            "change": result.get("score_change"),
                        })
                else:
                    failed_count += 1

                # Update progress
                await self._job_store.set(job_id, {
                    "type": "batch_regrade",
                    "assignment_code": assignment_code,
                    "status": "processing",
                    "progress": {
                        "current": i + 1,
                        "total": total,
                        "percent": int((i + 1) / total * 100),
                    },
                })

            # 3. Complete job
            await self._job_store.set(job_id, {
                "type": "batch_regrade",
                "assignment_code": assignment_code,
                "status": "completed",
                "completed_at": datetime.now().isoformat(),
                "summary": {
                    "total": total,
                    "success": success_count,
                    "failed": failed_count,
                    "score_changes": len(score_changes),
                },
            })

            logger.info(
                "Batch regrade completed: %d/%d success, %d failed",
                success_count, total, failed_count
            )

            return {
                "success": True,
                "job_id": job_id,
                "total_submissions": total,
                "regraded_count": success_count,
                "failed_count": failed_count,
                "score_changes": score_changes[:10],  # First 10 changes
            }

        except Exception as e:
            logger.error("Batch regrade failed: %s", e, exc_info=True)
            await self._job_store.set(job_id, {
                "type": "batch_regrade",
                "status": "failed",
                "error": str(e),
            })
            return {
                "success": False,
                "error": str(e),
            }

    async def regrade_all(
        self,
        reviewer_id: str = "system"
    ) -> Dict[str, Any]:
        """
        Regrade all submissions in the system.
        
        WARNING: This is a heavy operation. Use with caution.
        
        Args:
            reviewer_id: User triggering the regrade
            
        Returns:
            Summary of regrade operation
        """
        logger.info("Starting FULL SYSTEM regrade")
        
        job_id = f"regrade_all_{int(datetime.now().timestamp())}"
        await self._job_store.set(job_id, {
            "type": "full_regrade",
            "status": "processing",
            "started_at": datetime.now().isoformat(),
        })

        try:
            # 1. Get ALL submissions (paginate through all pages)
            submissions = []
            page = 1
            page_size = 500
            while True:
                result = self._repository.get_all_submissions(page=page, page_size=page_size)
                batch = result.get("submissions", [])
                if not batch:
                    break
                submissions.extend(batch)
                if len(batch) < page_size:
                    break
                page += 1
            
            if not submissions:
                await self._job_store.set(job_id, {
                    "type": "full_regrade",
                    "status": "completed",
                    "message": "No submissions found",
                })
                return {
                    "success": True,
                    "message": "No submissions found in system",
                    "regraded_count": 0,
                }

            # 2. Group by assignment for batch processing
            by_assignment: Dict[str, List] = {}
            for sub in submissions:
                assignment = sub.get("assignment_code", "general")
                if assignment not in by_assignment:
                    by_assignment[assignment] = []
                by_assignment[assignment].append(sub)

            # 3. Process each assignment
            total = len(submissions)
            success_count = 0
            failed_count = 0
            processed = 0

            for assignment_code, subs in by_assignment.items():
                logger.info("Processing assignment: %s (%d submissions)", assignment_code, len(subs))
                
                for sub in subs:
                    sub_id = sub.get("id")
                    if not sub_id:
                        continue

                    result = await self.regrade_single(sub_id, reviewer_id)
                    
                    if result.get("success"):
                        success_count += 1
                    else:
                        failed_count += 1

                    processed += 1
                    
                    # Update progress
                    await self._job_store.set(job_id, {
                        "type": "full_regrade",
                        "status": "processing",
                        "progress": {
                            "current": processed,
                            "total": total,
                            "percent": int(processed / total * 100),
                        },
                        "current_assignment": assignment_code,
                    })

            # 4. Complete job
            await self._job_store.set(job_id, {
                "type": "full_regrade",
                "status": "completed",
                "completed_at": datetime.now().isoformat(),
                "summary": {
                    "total": total,
                    "success": success_count,
                    "failed": failed_count,
                    "assignments_processed": len(by_assignment),
                },
            })

            logger.info(
                "Full system regrade completed: %d/%d success, %d failed",
                success_count, total, failed_count
            )

            return {
                "success": True,
                "job_id": job_id,
                "total_submissions": total,
                "regraded_count": success_count,
                "failed_count": failed_count,
                "assignments_processed": len(by_assignment),
            }

        except Exception as e:
            logger.error("Full system regrade failed: %s", e, exc_info=True)
            await self._job_store.set(job_id, {
                "type": "full_regrade",
                "status": "failed",
                "error": str(e),
            })
            return {
                "success": False,
                "error": str(e),
            }

    async def get_regrade_status(self, job_id: str) -> Dict[str, Any]:
        """Get status of a regrade job."""
        job = await self._job_store.get(job_id)
        if not job:
            return {
                "found": False,
                "error": "Job not found",
            }
        return {
            "found": True,
            "job_id": job_id,
            **job,
        }


# Singleton instance
_regrade_service_instance: Optional[RegradeService] = None


def get_regrade_service() -> RegradeService:
    """Get or create the regrade service singleton."""
    global _regrade_service_instance
    if _regrade_service_instance is None:
        _regrade_service_instance = RegradeService()
    return _regrade_service_instance


__all__ = [
    "RegradeService",
    "get_regrade_service",
]
