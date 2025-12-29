import frappe
from frappe import _

def validate_assessment_criteria(doc, method=None):

    if not doc.assessment_criteria:
        return

    valid_criteria = frappe.get_all("Assessment Criteria Item",pluck="criteria_name")

    if not valid_criteria:
        frappe.throw(_("No Assessment Criteria has been configured. Please define it in School Assessment Criteria first."))

    if doc.assessment_criteria not in valid_criteria:
        frappe.throw(
            _('Assessment Criteria "{0}" is not defined in School Assessment Criteria.')
            .format(doc.assessment_criteria)
        )
