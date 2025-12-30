"""
Bulk School Term Class Result Generator
Handles bulk generation of School Term Results for an entire class arm
Generates results on SAVE (before_insert)
Skips existing results to preserve teacher's work
"""

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate


class BulkSchoolTermClassResultGenerator(Document):
    """
    Generates School Term Results for all students in a class arm (Student Group)
    """
    
    def validate(self):
        """Validate required fields"""
        if not (self.assessment_group and self.academic_year and self.academic_term and self.student_group):
            frappe.throw("Assessment Group, Academic Year, Academic Term, and Class Arm are required.")
    
    def before_insert(self):
        """Generate results when document is saved (before insert)"""
        self.generate_results()
    
    def generate_results(self):
        """Generate School Term Results for all students in the class arm"""
        
        # Get the student group document
        student_group_doc = frappe.get_doc("Student Group", self.student_group)
        
        # Get all students from the students child table
        student_list = [s.student for s in student_group_doc.students]
        
        if not student_list:
            frappe.throw(f"No students found in class arm {self.student_group}")
        
        # Track results
        success_count = 0
        failed_count = 0
        skipped_count = 0
        failed_students = []
        skipped_students = []
        
        # Generate result for each student
        for idx, student in enumerate(student_list, 1):
            try:
                frappe.publish_progress(idx, len(student_list), f"Processing {student}")
                
                # Check if result already exists
                existing_result = frappe.db.get_value(
                    "School Term Result",
                    {
                        "student": student,
                        "assessment_group": self.assessment_group,
                        "academic_year": self.academic_year
                    },
                    "name"
                )
                
                if existing_result:
                    # Skip existing result - preserve teacher's work
                    skipped_count += 1
                    skipped_students.append(student)
                    continue
                
                # Create new result only
                doc = frappe.new_doc("School Term Result")
                doc.student = student
                doc.assessment_group = self.assessment_group
                doc.academic_year = self.academic_year
                doc.academic_term = self.academic_term
                
                doc.flags.ignore_permissions = True
                
                # Populate skills BEFORE insert
                self._populate_skills_for_result(doc)
                
                doc.insert()
                doc.save()
                
                frappe.db.commit()
                success_count += 1
                
            except Exception as e:
                failed_count += 1
                failed_students.append({
                    "student": student,
                    "error": str(e)
                })
        
        frappe.publish_progress(len(student_list), len(student_list), "Bulk generation complete")
        
        # Create summary message
        summary = f"""
        <b>✓ Bulk Result Generation Complete</b><br><br>
        <b>Class Arm:</b> {self.student_group}<br>
        <b>Assessment Group:</b> {self.assessment_group}<br>
        <b>Academic Year:</b> {self.academic_year}<br>
        <b>Total Students:</b> {len(student_list)}<br>
        <b style="color: green;">✓ Created:</b> {success_count}<br>
        <b style="color: orange;">⊘ Skipped (already exist):</b> {skipped_count}<br>
        <b style="color: red;">✗ Failed:</b> {failed_count}
        """
        
        if skipped_students:
            summary += "<br><br><b>Skipped Students (already have results):</b><ul>"
            for student in skipped_students[:10]:  # Show first 10
                summary += f"<li>{student}</li>"
            if len(skipped_students) > 10:
                summary += f"<li>... and {len(skipped_students) - 10} more</li>"
            summary += "</ul>"
        
        if failed_students:
            summary += "<br><br><b>Failed Students:</b><ul>"
            for item in failed_students:
                summary += f"<li>{item['student']}: {item['error']}</li>"
            summary += "</ul>"
        
        frappe.msgprint(summary)
    
    def _populate_skills_for_result(self, doc):
        """
        Populate psychomotor and affective skills for a School Term Result.
        
        Args:
            doc: School Term Result document
        """
        try:
            # Get the student's program
            program_enrollment = frappe.get_all(
                "Program Enrollment",
                filters={
                    "student": doc.student,
                    "academic_year": doc.academic_year,
                    "docstatus": 1
                },
                fields=["program"]
            )
            
            if not program_enrollment:
                return
            
            program = program_enrollment[0]["program"]
            
            # Get School Settings
            school_settings = frappe.get_doc("School Settings")
            
            # Determine school level based on program
            primary_programs = [p.program for p in (school_settings.primary_programs or [])]
            secondary_programs = [p.program for p in (school_settings.secondary_programs or [])]
            
            psychomotor_field = None
            affective_field = None
            
            if program in primary_programs:
                psychomotor_field = "primary_psychomotor_skills"
                affective_field = "primary_affective_skills"
            elif program in secondary_programs:
                psychomotor_field = "secondary_psychomotor_skills"
                affective_field = "secondary_affective_skills"
            else:
                return
            
            # Clear existing skills
            doc.psychomotor_skills = []
            doc.affective_skills = []
            
            # Get skills from settings
            psychomotor_skills = school_settings.get(psychomotor_field) or []
            affective_skills = school_settings.get(affective_field) or []
            
            # Populate psychomotor skills with rating 1
            for skill in psychomotor_skills:
                doc.append("psychomotor_skills", {
                    "skill": skill.skill_name,
                    "rating": 1
                })
            
            # Populate affective skills with rating 1
            for skill in affective_skills:
                doc.append("affective_skills", {
                    "skill": skill.skill_name,
                    "rating": 1
                })
        
        except Exception as e:
            frappe.log_error(f"Error populating skills for result: {str(e)}")
            import traceback
            frappe.log_error(traceback.format_exc())