import frappe

@frappe.whitelist()
def get_policy_details(student_group):
    policy_name = frappe.db.get_value("Policy Student Group Link", 
        {"student_group": student_group}, "parent")
    
    if policy_name:
        policy = frappe.get_doc("School Level Policy", policy_name)
        return {
            "max_assessment_score": policy.max_assessment_score,
            "criteria": policy.policy_assessment_criteria
        }
    return None


import frappe

def sync_assessment_plan_with_policy(doc, method):
    """
    Triggered before_save on Assessment Plan.
    Fetches criteria from the Policy linked to the Student Group.
    """
    if not doc.student_group:
        return

    # 1. Fetch the Policy from the Student Group
    policy_name = frappe.db.get_value("Student Group", doc.student_group, "custom_school_policy")
    
    if not policy_name:
        # Optional: If not on Student Group, fallback to Program
        if doc.program:
            policy_name = frappe.db.get_value("Program", doc.program, "custom_school_policy")

    if not policy_name:
        return

    policy = frappe.get_doc("School Level Policy", policy_name)

    # 2. Logic: If Assessment Criteria table is empty, auto-populate
    if not doc.assessment_criteria and policy.policy_assessment_criteria:
        for row in policy.policy_assessment_criteria:
            doc.append("assessment_criteria", {
                "assessment_criteria": row.assessment_criteria,
                "maximum_score": row.weightage
            })
        frappe.msgprint(f"Criteria auto-filled from Policy: <b>{policy_name}</b>")

    # 3. Logic: Strict Enforcement (Weightage Check)
    # This prevents users from manually changing CA scores to values not in the policy
    policy_map = {r.assessment_criteria: r.weightage for r in policy.policy_assessment_criteria}
    
    for row in doc.assessment_criteria:
        if row.assessment_criteria in policy_map:
            if row.maximum_score != policy_map[row.assessment_criteria]:
                # Force correct the weightage from policy
                row.maximum_score = policy_map[row.assessment_criteria]