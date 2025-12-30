"""
School Settings API
Provides utility functions for school configuration and print formats
"""

import frappe


@frappe.whitelist()
def get_school_print_format():
    """
    Get the configured print format from School Settings
    Returns both primary and secondary print formats
    """
    try:
        settings = frappe.get_doc('School Settings')
        return {
            "primary_print_format": settings.primary_school_print_format or "Standard",
            "secondary_print_format": settings.secondary_school_print_format or "Standard"
        }
    except Exception as e:
        frappe.log_error(f"Error getting school print format: {str(e)}")
        return {
            "primary_print_format": "Standard",
            "secondary_print_format": "Standard"
        }


def get_print_format_for_program(program):
    """
    Get the appropriate print format based on program type
    Checks if program is in primary or secondary programs in School Settings
    
    Args:
        program: Program name (e.g., "JSS One", "Basic One")
    
    Returns:
        Print format name (e.g., "Primary School Result", "Secondary School Result")
    """
    try:
        settings = frappe.get_doc('School Settings')
        
        # Check if program is in primary programs
        primary_programs = [p.program for p in (settings.primary_programs or [])]
        secondary_programs = [p.program for p in (settings.secondary_programs or [])]
        
        if program in primary_programs:
            print_format = settings.primary_school_print_format or "Standard"
        elif program in secondary_programs:
            print_format = settings.secondary_school_print_format or "Standard"
        else:
            print_format = "Standard"
        
        return print_format
    except Exception as e:
        frappe.log_error(f"Error getting print format for program {program}: {str(e)}")
        return "Standard"


@frappe.whitelist()
def get_student_reports_with_program():
    """Get all School Term Results for the current student"""
    
    # Get current user's student record
    student_id = frappe.db.get_value("Student", {"user": frappe.session.user}, "name")
    
    if not student_id:
        return []
    
    # Fetch all reports for this student
    reports = frappe.db.get_list(
        "School Term Result",
        filters={"student": student_id},
        fields=[
            "name", 
            "academic_year", 
            "assessment_group", 
            "program", 
            "academic_term", 
            "total_marks_obtained", 
            "total_max_marks", 
            "term_average", 
            "overall_grade", 
            "class_arm_position"
        ],
        order_by="academic_year desc, assessment_group desc"
    )
    
    return reports