import frappe
from frappe.model.document import Document
from frappe.utils import nowdate


class SchoolTermResult(Document):
    """
    School Term Result Document
    Automatically calculates all student performance data when saved
    """
    
    def before_insert(self):
        """Calculate all data before inserting document"""
        self.validate()
        self.populate_all_data()
    
    def before_update(self):
        """Recalculate all data before updating document"""
        self.validate()
        self.populate_all_data()
    
    def validate(self):
        """Validate required fields"""
        if not (self.student and self.assessment_group and self.academic_year and self.academic_term):
            frappe.throw("Student, Assessment Group, Academic Year, and Academic Term are required.")
    
    def populate_all_data(self):
        """Main function - populates all result data"""
        try:
            self.populate_student_info()
            self.populate_attendance()
            self.populate_subjects_and_assessment()
            self.calculate_overall_totals()
            self.calculate_overall_grade()
            self.calculate_class_positions()
        except Exception as e:
            frappe.log_error(f"Error populating School Term Result: {str(e)}")
            raise
    
    def populate_student_info(self):
        """Populate student profile information"""
        student_doc = frappe.get_doc("Student", self.student)
        
        self.gender = student_doc.gender
        self.student_admission_id = student_doc.name
        
        # Get program from Program Enrollment
        program_enrollment = frappe.get_all(
            "Program Enrollment",
            filters={
                "student": self.student,
                "academic_year": self.academic_year,
                "docstatus": 1
            },
            fields=["program"]
        )
        
        self.program = program_enrollment[0].program if program_enrollment else None
        
        # Get Academic Term dates
        term_doc = frappe.get_doc("Academic Term", self.academic_term)
        self.term_start_date = term_doc.term_start_date
        self.term_end_date = term_doc.term_end_date
        
        # Set date of result issue
        if not self.date_of_result_issue:
            self.date_of_result_issue = nowdate()
        
        # Get Student Group
        sgs = frappe.db.sql("""
            SELECT sgs.parent
            FROM `tabStudent Group Student` sgs
            INNER JOIN `tabStudent Group` sg ON sgs.parent = sg.name
            WHERE sgs.student = %s 
            AND sg.academic_year = %s
        """, (self.student, self.academic_year), as_dict=True)
        
        if sgs:
            student_group_name = sgs[0].parent
            self.student_group = student_group_name
            
            # Count students in Student Group (e.g. JSS 1A)
            self.number_of_students_in_class_group = frappe.db.count(
                "Student Group Student",
                filters={"parent": student_group_name}
            )
            
            # Get the program from the Student Group
            program = frappe.db.get_value("Student Group", student_group_name, "program")
            
            # Count students in the Program (all groups e.g. JSS 1)
            self.number_of_students_in_class = frappe.db.count(
                "Program Enrollment",
                filters={
                    "program": program,
                    "academic_year": self.academic_year,
                    "docstatus": 1
                }
            )
    
    def populate_attendance(self):
        """Populate attendance information"""
        try:
            # Count distinct days school was open
            school_opened_days_sql = frappe.db.sql("""
                SELECT COUNT(DISTINCT DATE(sa.`date`)) as count
                FROM `tabStudent Attendance` sa
                WHERE sa.`date` BETWEEN %s AND %s
            """, (self.term_start_date, self.term_end_date))
            
            self.number_of_times_school_opened = school_opened_days_sql[0][0] if school_opened_days_sql else 0
        except Exception as e:
            frappe.log_error(f"Error calculating school opened days: {str(e)}")
            self.number_of_times_school_opened = 0
        
        # Count present days
        try:
            self.number_of_times_present = frappe.db.count(
                "Student Attendance",
                filters={
                    "student": self.student,
                    "status": "Present",
                    "date": ["between", [self.term_start_date, self.term_end_date]]
                }
            )
        except Exception as e:
            frappe.log_error(f"Error counting present days: {str(e)}")
            self.number_of_times_present = 0
        
        # Count absent days
        try:
            self.number_of_times_absent = frappe.db.count(
                "Student Attendance",
                filters={
                    "student": self.student,
                    "status": "Absent",
                    "date": ["between", [self.term_start_date, self.term_end_date]]
                }
            )
        except Exception as e:
            frappe.log_error(f"Error counting absent days: {str(e)}")
            self.number_of_times_absent = 0
        
        # Calculate attendance percentage
        self.attendance_percentage = 0
        if self.number_of_times_school_opened and self.number_of_times_school_opened > 0:
            self.attendance_percentage = round(
                (self.number_of_times_present / self.number_of_times_school_opened) * 100,
                2
            )
    
    def populate_subjects_and_assessment(self):
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
        """, (self.student, self.academic_year, self.assessment_group), as_dict=True)
        
        if not detailed_results:
            frappe.throw(f"No Assessment Results found for student {self.student} in {self.assessment_group}")
        
        # Clear existing rows
        self.subjects = []
        self.assessment_components = []
        
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
            self.append("subjects", {
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
            self.append("assessment_components", {
                "criteria": row.assessment_criteria,
                "score_obtained": row.score or 0,
                "max_score": row.maximum_score or 0,
                "subject": row.course
            })
        
        # Calculate class statistics for each subject
        self.calculate_class_statistics()
    
    def calculate_class_statistics(self):
        """Calculate class statistics and positions for each subject"""
        for subject_row in self.subjects:
            if self.student_group and subject_row.subject:
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
                """, (self.student_group, subject_row.subject, self.assessment_group, self.academic_year))
                
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
    
    def calculate_overall_totals(self):
        """Calculate overall totals and percentages"""
        total_marks = sum([subject.total_score or 0 for subject in self.subjects])
        self.total_marks_obtained = total_marks
        
        max_marks = sum([component.max_score or 0 for component in self.assessment_components])
        self.total_max_marks = max_marks
        
        if max_marks > 0:
            self.term_average = round((total_marks / max_marks) * 100, 2)
    
    def calculate_overall_grade(self):
        """Calculate overall grade based on term average"""
        if not self.term_average:
            self.overall_grade = "N/A"
            return
        
        try:
            school_settings = frappe.get_doc("School Settings")
            
            # Determine school level
            program = self.program
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
                    
                    if min_score <= self.term_average <= max_score:
                        overall_grade = grade_row.grade_symbol
                        break
            else:
                # Fallback grading
                if self.term_average >= 80:
                    overall_grade = "A"
                elif self.term_average >= 70:
                    overall_grade = "B"
                elif self.term_average >= 60:
                    overall_grade = "C"
                elif self.term_average >= 50:
                    overall_grade = "D"
                else:
                    overall_grade = "F"
            
            self.overall_grade = overall_grade
            
        except Exception as e:
            frappe.log_error(f"Error calculating overall grade: {str(e)}")
            self.overall_grade = "N/A"
    
    def calculate_class_positions(self):
        """Calculate class positions (within arm and overall)"""
        if not self.student_group:
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
        """, (self.student_group, self.assessment_group, self.academic_year))
        
        if class_arm_totals:
            student_total_marks = self.total_marks_obtained or 0
            arm_position = 1
            for total_row in class_arm_totals:
                if total_row[1] > student_total_marks:
                    arm_position = arm_position + 1
            self.class_arm_position = arm_position
        
        # 2. Overall Class Position (across entire program)
        program_enrollment = frappe.get_all(
            "Program Enrollment",
            filters={
                "student": self.student,
                "academic_year": self.academic_year,
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
            """, (program, self.academic_year, self.assessment_group, self.academic_year))
            
            if class_totals:
                student_total_marks = self.total_marks_obtained or 0
                overall_position = 1
                for total_row in class_totals:
                    if total_row[1] > student_total_marks:
                        overall_position = overall_position + 1
                self.class_position = overall_position