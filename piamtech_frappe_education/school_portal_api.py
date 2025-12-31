"""
School Portal API
Provides utility functions for student portal operations including:
- Student fees/invoices management
- Payment history tracking
- Print format configuration
- Report generation
- Certificate management
"""

import frappe
from frappe import _


# ============================================================================
# SCHOOL SETTINGS & CONFIGURATION
# ============================================================================

@frappe.whitelist()
def get_school_print_format():
    """
    Get the configured print format from School Settings
    Returns both primary and secondary print formats
    
    Used for: Reports, certificates, documents
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


@frappe.whitelist()
def get_print_format_for_program(program, format_type="report"):
    """
    Get the appropriate print format based on program type
    Checks if program is in primary or secondary programs in School Settings
    
    Args:
        program: Program name (e.g., "JSS One", "Basic One")
        format_type: Type of format - "report", "bill", "receipt"
    
    Returns:
        Print format name (e.g., "Primary School Result", "Secondary School Result")
    
    Used by: Result reports, certificates, fee documents
    """
    try:
        settings = frappe.get_doc('School Settings')
        
        # Check if program is in primary programs
        primary_programs = [p.program for p in (settings.primary_programs or [])]
        secondary_programs = [p.program for p in (settings.secondary_programs or [])]
        
        if program in primary_programs:
            if format_type == "report":
                return settings.primary_school_print_format or "Standard"
            elif format_type == "bill":
                return settings.primary_school_fees_bill_format or "Standard"
            elif format_type == "receipt":
                return settings.primary_school_fees_receipt_format or "Standard"
        elif program in secondary_programs:
            if format_type == "report":
                return settings.secondary_school_print_format or "Standard"
            elif format_type == "bill":
                return settings.secondary_school_fees_bill_format or "Standard"
            elif format_type == "receipt":
                return settings.secondary_school_fees_receipt_format or "Standard"
        
        return "Standard"
    except Exception as e:
        frappe.log_error(f"Error getting print format for program {program}: {str(e)}")
        return "Standard"


@frappe.whitelist()
def get_print_format_for_program_whitelist(program, format_type="report"):
    """
    Whitelist wrapper for get_print_format_for_program
    Makes the function callable from frontend
    """
    return get_print_format_for_program(program, format_type)


# ============================================================================
# STUDENT REPORTS & RESULTS
# ============================================================================

@frappe.whitelist()
def get_student_reports_with_program():
    """
    Get all School Term Results for the current student
    
    Returns:
        List of school term results with academic year, term, grades, etc.
    
    Used by: Reports/Results page
    """
    
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


# ============================================================================
# CERTIFICATES & AWARDS
# ============================================================================

@frappe.whitelist()
def get_individual_awards():
    """
    Return all submitted individual certificates for the current logged-in student
    
    Returns:
        List of certificates with title, type, date, etc.
    
    Used by: Awards/Certificates page
    """
    try:
        # Get student record from current user
        student = frappe.db.get_value("Student", {"user": frappe.session.user}, "name")
        if not student:
            frappe.throw("No student record found for current user")

        awards = frappe.get_all(
            "Individual Certificate",
            filters={
                "awardee": student,
                "docstatus": 1  # Only submitted certificates
            },
            fields=[
                "name",
                "certificate_title",
                "certificate_type",
                "certificate_date",
                "description",
                "academic_year",
                "certificate_file"
            ],
            order_by="certificate_date desc"
        )
        return awards

    except Exception as e:
        frappe.log_error(f"Error in getting individual awards: {str(e)}")
        frappe.throw(f"Error loading awards: {str(e)}")


@frappe.whitelist()
def download_certificate(award_name):
    """
    Download certificate file for a submitted Individual Certificate
    
    Args:
        award_name: Name of the Individual Certificate document
    
    Returns:
        dict: {"file_url": "...", "file_name": "..."}
    
    Used by: Awards/Certificates page
    """
    try:
        # Get current student
        student = frappe.db.get_value("Student", {"user": frappe.session.user}, "name")
        if not student:
            frappe.throw("No student record found for current user")
        
        # Get the certificate
        certificate = frappe.get_doc("Individual Certificate", award_name)
        
        # Verify the current student is the awardee
        if certificate.awardee != student:
            frappe.throw("You don't have permission to download this certificate")
        
        # Verify it's submitted
        if certificate.docstatus != 1:
            frappe.throw("This certificate has not been issued yet")
        
        # Get the file
        if not certificate.certificate_file:
            frappe.throw("No certificate file attached")
        
        # Return the file URL
        return {
            "file_url": certificate.certificate_file,
            "file_name": certificate.certificate_file.split('/')[-1]
        }
        
    except Exception as e:
        frappe.log_error(f"Error downloading certificate {award_name}: {str(e)}")
        frappe.throw(f"Error downloading certificate: {str(e)}")


# ============================================================================
# STUDENT FEES & INVOICES
# ============================================================================

@frappe.whitelist()
def get_student_fees(student=None):
    """
    Get all fees for a student
    
    Args:
        student (str): Student ID (optional, uses current user's student if not provided)
    
    Returns:
        dict: {"fees": [list of fee documents]}
    
    Used by: Legacy fees tracking (if applicable)
    """
    try:
        # If student not provided, get from current user
        if not student:
            student = frappe.db.get_value("Student", {"user": frappe.session.user}, "name")
            if not student:
                frappe.throw(_("No student record found for current user"))
        
        # Get all fees for this student
        fees = frappe.db.get_list(
            "Fees",
            filters={
                "student": student,
                "docstatus": [">", -1]  # Include draft and submitted
            },
            fields=[
                "name",
                "student_name",
                "description",
                "amount",
                "outstanding_amount",
                "due_date",
                "status",
                "company",
                "posting_date"
            ],
            order_by="due_date desc"
        )
        
        return {
            "fees": fees
        }
    
    except Exception as e:
        frappe.log_error(f"Error getting student fees: {str(e)}")
        frappe.throw(_("Error loading fees. Please try again."))


@frappe.whitelist()
def get_student_invoices_with_details(student=None):
    """
    Get student invoices with complete payment breakdown
    Calculates from actual Payment Entry data
    
    Args:
        student (str): Student ID (optional, uses current user's student if not provided)
    
    Returns:
        dict: {
            "invoices": [
                {
                    "invoice": "ACC-SINV-2025-00001",
                    "status": "Paid",
                    "original_amount": 100000,
                    "total_paid": 100000,
                    "outstanding_amount": 0,
                    "payment_history": [...]
                }
            ],
            "print_format": "Standard"
        }
    
    Structure:
    - Original Amount: Sales Invoice grand_total
    - Total Paid: Sum of all Payment Entry allocated_amount for this invoice
    - Outstanding: original_amount - total_paid
    
    Used by: Fees/Invoices page
    """
    try:
        if not student:
            student = frappe.db.get_value("Student", {"user": frappe.session.user}, "name")
            if not student:
                frappe.throw(_("No student record found for current user"))
        
        # Store current user
        current_user = frappe.session.user
        
        # Get invoices from Frappe Education API
        from education.education.api import get_student_invoices
        result = get_student_invoices(student)
        invoices = result.get("invoices", []) or []
        
        # Enhance with complete details from Sales Invoice and Payment Entries
        enhanced_invoices = []
        for invoice in invoices:
            try:
                invoice_name = invoice.get("invoice")
                
                # Get Sales Invoice details
                sales_invoice = frappe.get_doc("Sales Invoice", invoice_name)
                original_amount = sales_invoice.grand_total or 0
                
                # Use Administrator context to query Payment Entries
                frappe.set_user("Administrator")
                
                # Get all Payment Entries (don't use Payment Entry Reference, query Payment Entry directly)
                all_payment_entries = frappe.db.get_list(
                    "Payment Entry",
                    filters={"docstatus": 1},
                    fields=["name"],
                    limit_page_length=None
                )
                
                # Switch back to current user
                frappe.set_user(current_user)
                
                # Calculate total paid by summing allocated amounts from each payment entry
                total_paid = 0
                payment_history = []
                
                for pe_item in all_payment_entries:
                    try:
                        parent_name = pe_item.get("name")
                        if not parent_name:
                            continue
                        
                        # Get the Payment Entry document
                        payment_entry = frappe.get_doc("Payment Entry", parent_name)
                        
                        if payment_entry.docstatus == 1:  # Only submitted
                            # Check if this payment entry has a reference to our invoice
                            for ref in payment_entry.references:
                                if ref.reference_name == invoice_name:
                                    allocated_amount = ref.allocated_amount or 0
                                    total_paid += allocated_amount
                                    
                                    payment_history.append({
                                        "payment_entry": parent_name,
                                        "date": payment_entry.posting_date,
                                        "amount": allocated_amount,
                                        "reference": payment_entry.reference_no
                                    })
                    except Exception as e:
                        frappe.log_error(f"Error processing payment entry {parent_name}: {str(e)}")
                        continue
                
                # Calculate outstanding
                outstanding_amount = original_amount - total_paid
                
                enhanced_invoice = {
                    **invoice,
                    "original_amount": original_amount,
                    "total_paid": total_paid,
                    "outstanding_amount": max(outstanding_amount, 0),
                    "payment_history": payment_history,
                }
                
                enhanced_invoices.append(enhanced_invoice)
            
            except Exception as e:
                frappe.log_error(f"Error processing invoice {invoice.get('invoice')}: {str(e)}")
                enhanced_invoices.append(invoice)
        
        return {
            "invoices": enhanced_invoices,
            "print_format": result.get("print_format", "Standard")
        }
    
    except Exception as e:
        frappe.log_error(f"Error getting student invoices with details: {str(e)}")
        frappe.throw(_("Error loading fees. Please try again."))
    
    finally:
        # Ensure we always restore the original user
        try:
            frappe.set_user(current_user)
        except Exception:
            pass


# ============================================================================
# FEES PRINT FORMATS & DOWNLOADS
# ============================================================================

@frappe.whitelist()
@frappe.whitelist()
def get_print_format_for_fees(program, format_type="bill"):
    """
    Get the appropriate print format for school fees based on program
    
    Args:
        program: Student's program name (e.g., "Basic One", "JSS One")
        format_type: "bill" or "receipt"
    
    Returns:
        str: Print format name to use
    
    Used by: Fees page (Bill/Receipt download buttons)
    
    Logic:
        1. Check if program is in primary_programs
        2. If yes, return primary_school_fees_bill/receipt_format
        3. If no, check secondary_programs
        4. If yes, return secondary_school_fees_bill/receipt_format
        5. Otherwise return "Standard"
    """
    return get_print_format_for_program(program, format_type)


@frappe.whitelist()
@frappe.whitelist()
def get_invoice_payment_history(invoice_name):
    """
    Get complete payment history for an invoice
    
    Args:
        invoice_name: Sales Invoice name
    
    Returns:
        dict: {
            "invoice": "ACC-SINV-2025-00001",
            "student": "STU-001",
            "program": "Basic One",
            "total_amount": 100000,
            "total_paid": 100000,
            "outstanding": 0,
            "payments": [
                {
                    "payment_entry": "ACC-PAY-2025-00001",
                    "date": "2025-12-25",
                    "amount": 100000,
                    "reference": "TXN123456"
                }
            ]
        }
    
    Used by: Receipt print format (to show payment history)
    """
    try:
        invoice = frappe.get_doc("Sales Invoice", invoice_name)
        
        # Store current user
        current_user = frappe.session.user
        
        # Use Administrator context to query Payment Entries
        frappe.set_user("Administrator")
        
        payment_entries = frappe.db.get_list(
            "Payment Entry",
            filters={"docstatus": 1},
            fields=["name", "paid_amount", "posting_date", "reference_no"],
            limit_page_length=None
        )
        
        # Switch back to current user
        frappe.set_user(current_user)
        
        # Filter for payments referencing this invoice
        invoice_payments = []
        for pe in payment_entries:
            doc = frappe.get_doc("Payment Entry", pe["name"])
            for ref in doc.references:
                if ref.reference_name == invoice_name:
                    invoice_payments.append({
                        "payment_entry": pe["name"],
                        "date": pe["posting_date"],
                        "amount": ref.allocated_amount,
                        "reference": pe["reference_no"]
                    })
        
        return {
            "invoice": invoice_name,
            "student": invoice.student if hasattr(invoice, 'student') else None,
            "program": invoice.program if hasattr(invoice, 'program') else None,
            "total_amount": invoice.grand_total,
            "total_paid": sum(p["amount"] for p in invoice_payments),
            "outstanding": invoice.outstanding_amount,
            "payments": invoice_payments
        }
    
    except Exception as e:
        frappe.log_error(f"Error getting payment history: {str(e)}")
        return {}
    
    finally:
        # Ensure we always restore the original user
        try:
            frappe.set_user(current_user)
        except Exception:
            pass