frappe.ui.form.on('Assessment Plan', {
    student_group: function(frm) {
        if (frm.doc.student_group) {
            frappe.call({
                method: "piamtech_frappe_education.piamtech_frappe_education.api.get_policy_details", // You'll create this Python function
                args: {
                    student_group: frm.doc.student_group
                },
                callback: function(r) {
                    if (r.message) {
                        let policy = r.message;
                        
                        // Set the Max Score
                        frm.set_value('maximum_assessment_score', policy.max_assessment_score);
                        
                        // Clear and Refresh the Assessment Criteria Table
                        frm.clear_table('assessment_criteria');
                        policy.criteria.forEach(row => {
                            let child = frm.add_child('assessment_criteria');
                            child.assessment_criteria = row.assessment_criteria;
                            child.weightage = row.weightage;
                        });
                        frm.refresh_field('assessment_criteria');
                    }
                }
            });
        }
    }
});