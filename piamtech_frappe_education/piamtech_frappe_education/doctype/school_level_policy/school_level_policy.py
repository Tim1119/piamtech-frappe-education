import frappe
from frappe.model.document import Document

class SchoolLevelPolicy(Document):
    def validate_promotion(self, student_results):
        """
        Logic to check if a student meets the promotion criteria 
        defined in this policy.
        """
        passed_subjects = [r for r in student_results if r.score >= self.promotion_passing_score]
        
        # Check Core Subjects
        core_subjects = [row.subject for row in self.core_subjects]
        for subject in core_subjects:
            if not any(r.subject == subject and r.score >= self.promotion_passing_score for r in student_results):
                return False, f"Failed Core Subject: {subject}"
        
        # Check total number of subjects passed
        if self.promotion_subjects_threshold and len(passed_subjects) < self.promotion_subjects_threshold:
            return False, f"Did not pass enough subjects (Required: {self.promotion_subjects_threshold})"
            
        return True, "Promoted"