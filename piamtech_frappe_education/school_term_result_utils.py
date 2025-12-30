# School Term Result Utilities
# Reusable functions for generating school term results
# Can be used in server scripts, API endpoints, or bulk operations

import frappe
from frappe.utils import nowdate


def generate_school_term_result(student, assessment_group, academic_year, academic_term):
    """
    Generate a complete School Term Result for a single student.
    
    Args:
        student: Student ID
        assessment_group: Assessment Group name
        academic_year: Academic Year name
        academic_term: Academic Term name
    
    Returns:
        frappe.Document: The created/updated School Term Result document
    """
    
    # Validate required fields
    if not (student and assessment_group and academic_year and academic_term):
        frappe.throw("Student, Assessment Group, Academic Year, and Academic Term are required.")
    
    # Create or get existing result
    existing_result = frappe.db.get_value(
        "School Term Result",
        {
            "student": student,
            "assessment_group": assessment_group,
            "academic_year": academic_year
        },
        "name"
    )
    
    if existing_result:
        doc = frappe.get_doc("School Term Result", existing_result)
    else:
        doc = frappe.new_doc("School Term Result")
        doc.student = student
        doc.assessment_group = assessment_group
        doc.academic_year = academic_year
        doc.academic_term = academic_term
    
    # Populate basic information
    _populate_student_info(doc)
    _populate_attendance(doc)
    _populate_subjects_and_assessment(doc)
    _calculate_overall_totals(doc)
    _calculate_overall_grade(doc)
    _calculate_class_positions(doc)
    
    # Save the document
    doc.save()
    frappe.db.commit()
    
    return doc


def _populate_student_info(doc):
    """Populate student profile information"""
    student_doc = frappe.get_doc("Student", doc.student)
    
    doc.gender = student_doc.gender
    doc.student_admission_id = student_doc.name
    
    # Get program from Program Enrollment
    program_enrollment = frappe.get_all(
        "Program Enrollment",
        filters={
            "student": doc.student,
            "academic_year": doc.academic_year,
            "docstatus": 1
        },
        fields=["program"]
    )
    
    doc.program = program_enrollment[0].program if program_enrollment else None
    
    # Get Academic Term dates
    term_doc = frappe.get_doc("Academic Term", doc.academic_term)
    doc.term_start_date = term_doc.term_start_date
    doc.term_end_date = term_doc.term_end_date
    
    # Set date of result issue
    if not doc.date_of_result_issue:
        doc.date_of_result_issue = nowdate()
    
    # Get Student Group
    sgs = frappe.db.sql("""
        SELECT sgs.parent
        FROM `tabStudent Group Student` sgs
        INNER JOIN `tabStudent Group` sg ON sgs.parent = sg.name
        WHERE sgs.student = %s 
        AND sg.academic_year = %s
    """, (doc.student, doc.academic_year), as_dict=True)
    
    if sgs:
        student_group_name = sgs[0].parent
        doc.student_group = student_group_name
        
        # Count students in Student Group (e.g. JSS 1A)
        doc.number_of_students_in_class_group = frappe.db.count(
            "Student Group Student",
            filters={"parent": student_group_name}
        )
        
        # Get the program from the Student Group
        program = frappe.db.get_value("Student Group", student_group_name, "program")
        
        # Count students in the Program (all groups e.g. JSS 1)
        doc.number_of_students_in_class = frappe.db.count(
            "Program Enrollment",
            filters={
                "program": program,
                "academic_year": doc.academic_year,
                "docstatus": 1
            }
        )


def _populate_attendance(doc):
    """Populate attendance information"""
    try:
        # Count distinct days school was open
        school_opened_days_sql = frappe.db.sql("""
            SELECT COUNT(DISTINCT DATE(sa.`date`)) as count
            FROM `tabStudent Attendance` sa
            WHERE sa.`date` BETWEEN %s AND %s
        """, (doc.term_start_date, doc.term_end_date))
        
        doc.number_of_times_school_opened = school_opened_days_sql[0][0] if school_opened_days_sql else 0
    except Exception as e:
        frappe.log_error(f"Error calculating school opened days: {str(e)}")
        doc.number_of_times_school_opened = 0
    
    # Count present days
    try:
        doc.number_of_times_present = frappe.db.count(
            "Student Attendance",
            filters={
                "student": doc.student,
                "status": "Present",
                "date": ["between", [doc.term_start_date, doc.term_end_date]]
            }
        )
    except Exception as e:
        frappe.log_error(f"Error counting present days: {str(e)}")
        doc.number_of_times_present = 0
    
    # Count absent days
    try:
        doc.number_of_times_absent = frappe.db.count(
            "Student Attendance",
            filters={
                "student": doc.student,
                "status": "Absent",
                "date": ["between", [doc.term_start_date, doc.term_end_date]]
            }
        )
    except Exception as e:
        frappe.log_error(f"Error counting absent days: {str(e)}")
        doc.number_of_times_absent = 0
    
    # Calculate attendance percentage
    doc.attendance_percentage = 0
    if doc.number_of_times_school_opened and doc.number_of_times_school_opened > 0:
        doc.attendance_percentage = round(
            (doc.number_of_times_present / doc.number_of_times_school_opened) * 100,
            2
        )


def _populate_subjects_and_assessment(doc):
    """Populate subjects and assessment components"""
    detailed_results = frappe.db.sql("""
        SELECT 
            ar.course,
            ar.total_score,
            ar.grade,
            ard.assessment_criteria,
            ard.score,
            ard.maximum_score
        FROM `tabAssessment Result` ar
        INNER JOIN `tabAssessment Result Detail` ard ON ar.name = ard.parent
        WHERE ar.student = %s
          AND ar.academic_year = %s
          AND ar.assessment_group = %s
          AND ar.docstatus IN (0, 1)
        ORDER BY ar.course, ard.idx
    """, (doc.student, doc.academic_year, doc.assessment_group), as_dict=True)
    
    if not detailed_results:
        frappe.throw(f"No Assessment Results found for student {doc.student} in {doc.assessment_group}")
    
    doc.subjects = []
    doc.assessment_components = []
    
    course_details = {}
    
    # Group results by course
    for row in detailed_results:
        course = row.course
        if course not in course_details:
            course_details[course] = {
                "details": [],
                "total_score": row.total_score,
                "grade": row.grade
            }
        
        course_details[course]["details"].append({
            "criteria": row.assessment_criteria,
            "score": row.score or 0,
            "max_score": row.maximum_score or 0
        })
    
    # Add subjects to the subjects table
    for course, data in course_details.items():
        doc.append("subjects", {
            "subject": course,
            "total_score": data["total_score"] or 0,
            "grade": data["grade"] or "",
            "subject_position": "",
            "class_highest_score": 0,
            "class_lowest_score": 0,
            "class_average_score": 0,
            "previous_total1": None,
            "previous_total2": None,
            "session_average": 0
        })
    
    # Add assessment components
    for row in detailed_results:
        doc.append("assessment_components", {
            "criteria": row.assessment_criteria,
            "score_obtained": row.score or 0,
            "max_score": row.maximum_score or 0,
            "subject": row.course
        })
    
    # Calculate class statistics for each subject
    _calculate_class_statistics(doc)


def _calculate_class_statistics(doc):
    """Calculate class statistics and positions for each subject"""
    for subject_row in doc.subjects:
        if doc.student_group and subject_row.subject:
            # Get class scores for current term
            class_scores = frappe.db.sql("""
                SELECT ar.total_score
                FROM `tabAssessment Result` ar
                INNER JOIN `tabStudent` s ON ar.student = s.name
                INNER JOIN `tabStudent Group Student` sgs ON s.name = sgs.student
                WHERE sgs.parent = %s
                  AND ar.course = %s
                  AND ar.assessment_group = %s
                  AND ar.academic_year = %s
                  AND ar.docstatus IN (0, 1)
                  AND ar.total_score IS NOT NULL
            """, (doc.student_group, subject_row.subject, doc.assessment_group, doc.academic_year))
            
            if class_scores:
                scores_list = [float(s[0]) for s in class_scores]
                current_student_score = float(subject_row.total_score or 0)
                
                subject_row.class_highest_score = max(scores_list)
                subject_row.class_lowest_score = min(scores_list)
                subject_row.class_average_score = round(sum(scores_list) / len(scores_list), 2)
                
                # Calculate student's position in subject
                position = 1
                for score_value in scores_list:
                    if score_value > current_student_score:
                        position = position + 1
                
                subject_row.subject_position = str(position)


def _calculate_overall_totals(doc):
    """Calculate overall totals and percentages"""
    total_marks = sum([subject.total_score or 0 for subject in doc.subjects])
    doc.total_marks_obtained = total_marks
    
    max_marks = sum([component.max_score or 0 for component in doc.assessment_components])
    doc.total_max_marks = max_marks
    
    if max_marks > 0:
        doc.term_average = round((total_marks / max_marks) * 100, 2)


def _calculate_overall_grade(doc):
    """Calculate overall grade based on term average"""
    if not doc.term_average:
        doc.overall_grade = "N/A"
        return
    
    try:
        school_settings = frappe.get_doc("School Settings")
        
        # Determine school level
        program = doc.program
        primary_programs = [p.program for p in (school_settings.primary_programs or [])]
        
        # Get the appropriate grading scale
        if program in primary_programs:
            grade_scale = school_settings.primary_overall_performance_grades
        else:
            grade_scale = school_settings.secondary_overall_performance_grades
        
        overall_grade = "N/A"
        
        if grade_scale:
            for grade_row in grade_scale:
                min_score = grade_row.min_avg_score or 0
                max_score = grade_row.max_avg_score or 100
                
                if min_score <= doc.term_average <= max_score:
                    overall_grade = grade_row.grade_symbol
                    break
        else:
            # Fallback grading
            if doc.term_average >= 80:
                overall_grade = "A"
            elif doc.term_average >= 70:
                overall_grade = "B"
            elif doc.term_average >= 60:
                overall_grade = "C"
            elif doc.term_average >= 50:
                overall_grade = "D"
            else:
                overall_grade = "F"
        
        doc.overall_grade = overall_grade
        
    except Exception as e:
        frappe.log_error(f"Error calculating overall grade: {str(e)}")
        doc.overall_grade = "N/A"


def _calculate_class_positions(doc):
    """Calculate class positions (within arm and overall)"""
    if not doc.student_group:
        return
    
    # 1. Class Arm Position (within student group)
    class_arm_totals = frappe.db.sql("""
        SELECT 
            ar.student,
            SUM(ar.total_score) as total
        FROM `tabAssessment Result` ar
        INNER JOIN `tabStudent` s ON ar.student = s.name
        INNER JOIN `tabStudent Group Student` sgs ON s.name = sgs.student
        WHERE sgs.parent = %s
          AND ar.assessment_group = %s
          AND ar.academic_year = %s
          AND ar.docstatus IN (0, 1)
        GROUP BY ar.student
        ORDER BY total DESC
    """, (doc.student_group, doc.assessment_group, doc.academic_year))
    
    if class_arm_totals:
        student_total_marks = doc.total_marks_obtained or 0
        arm_position = 1
        for total_row in class_arm_totals:
            if total_row[1] > student_total_marks:
                arm_position = arm_position + 1
        doc.class_arm_position = arm_position
    
    # 2. Overall Class Position (across entire program)
    program_enrollment = frappe.get_all(
        "Program Enrollment",
        filters={
            "student": doc.student,
            "academic_year": doc.academic_year,
            "docstatus": 1
        },
        fields=["program"]
    )
    
    program = program_enrollment[0].program if program_enrollment else None
    
    if program:
        class_totals = frappe.db.sql("""
            SELECT 
                ar.student,
                SUM(ar.total_score) as total
            FROM `tabAssessment Result` ar
            INNER JOIN `tabStudent` s ON ar.student = s.name
            INNER JOIN `tabProgram Enrollment` pe ON s.name = pe.student
            WHERE pe.program = %s
              AND pe.academic_year = %s
              AND pe.docstatus = 1
              AND ar.assessment_group = %s
              AND ar.academic_year = %s
              AND ar.docstatus IN (0, 1)
            GROUP BY ar.student
            ORDER BY total DESC
        """, (program, doc.academic_year, doc.assessment_group, doc.academic_year))
        
        if class_totals:
            student_total_marks = doc.total_marks_obtained or 0
            overall_position = 1
            for total_row in class_totals:
                if total_row[1] > student_total_marks:
                    overall_position = overall_position + 1
            doc.class_position = overall_position


def generate_bulk_results(students, assessment_group, academic_year, academic_term):
    """
    Generate School Term Results for multiple students.
    
    Args:
        students: List of student IDs
        assessment_group: Assessment Group name
        academic_year: Academic Year name
        academic_term: Academic Term name
    
    Returns:
        dict: Summary of generated results
    """
    
    results = {
        "success": [],
        "failed": [],
        "total": len(students)
    }
    
    for student in students:
        try:
            doc = generate_school_term_result(student, assessment_group, academic_year, academic_term)
            results["success"].append({
                "student": student,
                "result_id": doc.name,
                "status": "Created"
            })
        except Exception as e:
            frappe.log_error(f"Error generating result for {student}: {str(e)}")
            results["failed"].append({
                "student": student,
                "error": str(e)
            })
    
    return results