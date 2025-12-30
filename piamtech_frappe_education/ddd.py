

# Add these functions to your education/education/api.py file

import frappe
from frappe import _
from frappe.utils.print_format import download_pdf
import json

@frappe.whitelist()
def get_individual_awards():
    """Return all individual certificates for the current logged-in student"""
    try:
        # Get student record from current user
        student = frappe.db.get_value("Student", {"user": frappe.session.user}, "name")
        if not student:
            frappe.throw("No student record found for current user")

        awards = frappe.get_all(
            "Individual Certificate",
            filters={"awardee": student},
            fields=[
                "name",
                "certificate_title",
                "certificate_type",
                "certificate_date",
                "description",
                "academic_year",
                "certificate_file"
            ]
        )
        return awards

    except Exception as e:
        frappe.log_error(f"Error in getting individual awards: {str(e)}")
        frappe.throw(f"Error loading awards: {str(e)}")


@frappe.whitelist()
def get_general_awards():
    """Return all general certificates for the current student's groups"""
    try:
        # Get student record from current user
        student = frappe.db.get_value("Student", {"user": frappe.session.user}, "name")
        
        if not student:
            return []  # Return empty list instead of throwing error

        # First get student groups
        student_groups = frappe.db.sql("""
            SELECT DISTINCT parent
            FROM `tabStudent Group Student`
            WHERE student = %s
        """, (student,), as_list=True)

        if not student_groups:
            return []

        # Flatten the list
        group_list = [g[0] for g in student_groups]

        # Then get certificates using frappe.get_all (safer than raw SQL)
        awards = frappe.get_all(
            "General Certificate",
            filters={
                "student_group": ["in", group_list]
            },
            fields=[
                "name",
                "certificate_title",
                "certificate_type",
                "certificate_date",
                "student_group",
                "description",
                "academic_year",
                "certificate_file"
            ],
            order_by="certificate_date desc"
        )

        return awards

    except Exception as e:
        frappe.log_error(f"Error in getting general awards: {str(e)}", "General Awards Error")
        return []  # Return empty list instead of throwing


@frappe.whitelist()
def get_student_reports_with_program():
    """
    Get existing School Term Result reports for the current student,
    including program field
    """
    try:
        student = frappe.db.get_value("Student", {"user": frappe.session.user}, "name")
        if not student:
            frappe.throw("No student record found for current user")

        reports = frappe.get_all(
            "School Term Result",
            filters={"student": student},
            fields=[
                "name", "academic_year", "assessment_group", "academic_term", "program",
                "total_marks_obtained", "total_max_marks", "term_average", 
                "overall_grade", "class_position", "class_arm_position",
                "creation", "modified"
            ],
            order_by="academic_year desc, assessment_group"
        )
        return reports

    except Exception as e:
        frappe.log_error(f"Error in get_student_reports_with_program: {str(e)}")
        frappe.throw(f"Error loading reports: {str(e)}")


# @frappe.whitelist()
# def get_school_print_format():
#     """Get the configured print format from School Settings"""
#     settings = frappe.get_doc('School Settings', 'School Settings')
#     return {"print_format": settings.print_format}


def has_academic_permission():
    """
    Check if current user has academic permissions
    """
    user_roles = frappe.get_roles(frappe.session.user)
    academic_roles = [
        "Academics User", "Education Manager", "Student", 
        "Instructor", "Academic Admin", "School Admin"
    ]
    
    return any(role in academic_roles for role in user_roles)




@frappe.whitelist()
def get_student_bulk_certificates():
    """
    Get all bulk certificates that include the current logged-in student
    Returns certificates from Bulk Certificate Generator where the student is listed
    """
    try:
        # Get student record from current user
        student = frappe.db.get_value("Student", {"user": frappe.session.user}, "name")
        
        if not student:
            return []

        # Get all Bulk Certificate Generator documents where this student appears
        # and the certificate was generated for them
        certificates = frappe.db.sql("""
            SELECT DISTINCT
                bcg.name,
                bcg.certificate_title,
                bcg.certificate_type,
                bcg.certificate_date,
                bcg.description,
                bcg.certificate_file,
                bcg.class_arm as student_group,
                bcg.creation
            FROM 
                `tabBulk Certificate Generator` bcg
            INNER JOIN 
                `tabBulk Certificate Student` bcs ON bcg.name = bcs.parent
            WHERE 
                bcs.student = %(student)s
                AND bcs.select = 1
                AND bcs.certificate_generated = 1
                AND bcg.docstatus = 1
            ORDER BY 
                bcg.certificate_date DESC, bcg.creation DESC
        """, {"student": student}, as_dict=True)

        return certificates

    except Exception as e:
        frappe.log_error(f"Error in get_student_bulk_certificates: {str(e)}", "Bulk Certificates Error")
        return []


@frappe.whitelist()
def get_bulk_certificate_filters():
    """
    Get available filter options for bulk certificates for the current student
    """
    try:
        # Get student record from current user
        student = frappe.db.get_value("Student", {"user": frappe.session.user}, "name")
        
        if not student:
            return {
                "years": [],
                "categories": [],
                "student_groups": []
            }

        # Get distinct years
        years = frappe.db.sql("""
            SELECT DISTINCT YEAR(bcg.certificate_date) as year
            FROM `tabBulk Certificate Generator` bcg
            INNER JOIN `tabBulk Certificate Student` bcs ON bcg.name = bcs.parent
            WHERE bcs.student = %(student)s
                AND bcs.select = 1
                AND bcs.certificate_generated = 1
                AND bcg.docstatus = 1
            ORDER BY year DESC
        """, {"student": student}, as_dict=True)

        # Get distinct categories (certificate types)
        categories = frappe.db.sql("""
            SELECT DISTINCT bcg.certificate_type as category
            FROM `tabBulk Certificate Generator` bcg
            INNER JOIN `tabBulk Certificate Student` bcs ON bcg.name = bcs.parent
            WHERE bcs.student = %(student)s
                AND bcs.select = 1
                AND bcs.certificate_generated = 1
                AND bcg.docstatus = 1
                AND bcg.certificate_type IS NOT NULL
            ORDER BY category
        """, {"student": student}, as_dict=True)

        # Get distinct student groups
        student_groups = frappe.db.sql("""
            SELECT DISTINCT bcg.class_arm as student_group
            FROM `tabBulk Certificate Generator` bcg
            INNER JOIN `tabBulk Certificate Student` bcs ON bcg.name = bcs.parent
            WHERE bcs.student = %(student)s
                AND bcs.select = 1
                AND bcs.certificate_generated = 1
                AND bcg.docstatus = 1
                AND bcg.class_arm IS NOT NULL
            ORDER BY student_group
        """, {"student": student}, as_dict=True)

        return {
            "years": [str(y.year) for y in years if y.year],
            "categories": [c.category for c in categories if c.category],
            "student_groups": [sg.student_group for sg in student_groups if sg.student_group]
        }

    except Exception as e:
        frappe.log_error(f"Error in get_bulk_certificate_filters: {str(e)}", "Bulk Certificates Filters Error")
        return {
            "years": [],
            "categories": [],
            "student_groups": []
        }


















# Add these updated functions to your education/education/api.py file

@frappe.whitelist()
def get_school_print_format():
    """
    Get the configured print format from School Settings based on program type
    Returns both primary and secondary print formats
    """
    try:
        settings = frappe.get_doc('School Settings', 'School Settings')
        return {
            "primary_print_format": settings.primary_school_print_format,
            "secondary_print_format": settings.secondary_school_print_format
        }
    except Exception as e:
        frappe.log_error(f"Error getting school print format: {str(e)}")
        return {
            "primary_print_format": "Standard",
            "secondary_print_format": "Standard"
        }


def is_secondary_program(program):
    """
    Check if a program is a secondary/high school program
    Returns True if program contains keywords indicating secondary education
    """
    if not program:
        return False
    
    program_lower = program.lower()
    secondary_keywords = [
        'jss',  # Junior Secondary School
        'ss',   # Senior Secondary
        'secondary',
        'high school',
        'senior',
        'junior secondary'
    ]
    
    return any(keyword in program_lower for keyword in secondary_keywords)


def get_print_format_for_program(program):
    """
    Get the appropriate print format based on program type
    Returns the print format string to use for the given program
    """
    try:
        settings = frappe.get_doc('School Settings', 'School Settings')
        
        if is_secondary_program(program):
            print_format = settings.secondary_school_print_format or "Standard"
        else:
            print_format = settings.primary_school_print_format or "Standard"
        
        return print_format
    except Exception as e:
        frappe.log_error(f"Error getting print format for program {program}: {str(e)}")
        return "Standard"