// Bulk School Term Class Result Generator - Client Script

frappe.ui.form.on('Bulk School Term Class Result Generator', {
    refresh: function(frm) {
        // Optional: Add custom button if you want
        if (!frm.is_new()) {
            frm.add_custom_button(__('View Generated Results'), function() {
                frappe.route_options = {
                    "assessment_group": frm.doc.assessment_group,
                    "academic_year": frm.doc.academic_year,
                    "student_group": frm.doc.student_group
                };
                frappe.set_route("List", "School Term Result");
            }, "View");
        }
    },
    
    validate: function(frm) {
        // Show confirmation before saving
        if (frm.is_new()) {
            frappe.msgprint({
                title: __('Bulk Generation'),
                message: __('This will generate School Term Results for all students in <b>' + frm.doc.student_group + '</b>. Continue?'),
                indicator: 'blue'
            });
        }
    }
});