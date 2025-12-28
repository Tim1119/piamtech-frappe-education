import frappe
from frappe.model.document import Document

class PolicyAssessmentCriteria(Document):
    def validate(self):
        if self.weightage > 100:
            frappe.throw("Weightage for a single criteria cannot exceed 100%")
        if self.maximum_score <= 0:
            frappe.throw("Maximum score must be greater than 0")