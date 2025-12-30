import frappe

@frappe.whitelist()
def get_student_reports_with_program():
    """Get all School Term Results for the current student"""
    student_id = frappe.db.get_value("Student", {"user": frappe.session.user}, "name")
    
    if not student_id:
        return []
    
    reports = frappe.db.get_list(
        "School Term Result",
        filters={"student": student_id},
        fields=["name", "academic_year", "assessment_group", "program", 
                "academic_term", "total_marks_obtained", "total_max_marks", 
                "term_average", "overall_grade", "class_arm_position"],
        order_by="academic_year desc"
    )
    
    return reports