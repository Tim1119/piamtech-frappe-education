"""
Add this function to your student_portal_api.py to enhance get_student_invoices
or create a new API endpoint that enriches invoice data with payment breakdown
"""
import frappe 
@frappe.whitelist()
def get_student_invoices_with_breakdown(student=None):
    """
    Get student invoices with payment breakdown (paid vs remaining)
    Enhanced version of education.education.api.get_student_invoices
    """
    try:
        if not student:
            student = frappe.db.get_value("Student", {"user": frappe.session.user}, "name")
            if not student:
                frappe.throw(_("No student record found for current user"))
        
        # Get invoices from Frappe Education API
        from apps.education.education.api import get_student_invoices
        result = get_student_invoices(student)
        invoices = result.get("invoices", [])
        
        # Enhance with payment breakdown
        enhanced_invoices = []
        for invoice in invoices:
            # Get full invoice details for accurate payment info
            invoice_doc = frappe.get_doc("Sales Invoice", invoice.get("invoice"))
            
            total_amount = invoice_doc.grand_total or 0
            outstanding_amount = invoice_doc.outstanding_amount or 0
            amount_paid = total_amount - outstanding_amount
            
            enhanced_invoice = {
                **invoice,
                "total_amount": total_amount,
                "amount_paid": amount_paid,
                "amount_remaining": outstanding_amount,
                "payment_percentage": (amount_paid / total_amount * 100) if total_amount > 0 else 0,
            }
            
            enhanced_invoices.append(enhanced_invoice)
        
        return {
            "invoices": enhanced_invoices,
            "print_format": result.get("print_format", "Standard")
        }
    
    except Exception as e:
        frappe.log_error(f"Error getting student invoices with breakdown: {str(e)}")
        frappe.throw(_("Error loading fees. Please try again."))


@frappe.whitelist()
def get_invoice_payment_breakdown(invoice_name):
    """
    Get detailed payment breakdown for a specific invoice
    Shows all batch payments made against it
    """
    try:
        invoice = frappe.get_doc("Sales Invoice", invoice_name)
        
        # Get total paid via Payment Entries
        total_paid = 0
        payment_entries = frappe.db.get_list(
            "Payment Entry",
            filters={
                "docstatus": 1
            },
            fields=["name", "posting_date", "paid_amount"]
        )
        
        # Check which payments reference this invoice
        payments = []
        for pe in payment_entries:
            if frappe.db.exists("Payment Entry Reference", {
                "parent": pe.name,
                "reference_doctype": "Sales Invoice",
                "reference_name": invoice_name
            }):
                total_paid += pe.paid_amount
                payments.append({
                    "payment_entry": pe.name,
                    "date": pe.posting_date,
                    "amount": pe.paid_amount
                })
        
        # Also check Batch Payments
        batch_payments = frappe.db.get_list(
            "Batch Payment",
            filters={
                "sales_invoice": invoice_name,
                "docstatus": 1
            },
            fields=["name", "payment_date", "payment_amount"]
        )
        
        return {
            "invoice": invoice_name,
            "total_amount": invoice.grand_total,
            "amount_paid": total_paid,
            "amount_remaining": invoice.outstanding_amount,
            "payment_percentage": (total_paid / invoice.grand_total * 100) if invoice.grand_total > 0 else 0,
            "payments": payments,
            "batch_payments": batch_payments,
            "status": invoice.status
        }
    
    except Exception as e:
        frappe.log_error(f"Error getting payment breakdown: {str(e)}")
        frappe.throw(_("Error loading payment details."))