// School Term Result - Client script
// Auto-populates psychomotor and affective skills based on program
// Triggers when ANY of these fields change: student, academic_term, academic_year, assessment_group

frappe.ui.form.on('School Term Result', {
    // Trigger skill population when any of these fields change
    student: populate_skills,
    academic_term: populate_skills,
    academic_year: populate_skills,
    assessment_group: populate_skills
});

// Function to populate skills
function populate_skills(frm) {
    console.log('===== populate_skills triggered =====');
    console.log('Assessment Group:', frm.doc.assessment_group);
    console.log('Student:', frm.doc.student);
    console.log('Academic Term:', frm.doc.academic_term);
    console.log('Academic Year:', frm.doc.academic_year);
    
    // Check if all required fields are filled
    if (!frm.doc.assessment_group || !frm.doc.student || !frm.doc.academic_year) {
        console.log('Waiting for all required fields: assessment_group, student, academic_year');
        return;
    }
    
    // If assessment_group is missing, don't proceed
    if (!frm.doc.assessment_group) {
        console.log('Assessment Group not selected yet');
        return;
    }
    
    console.log('All required fields present - proceeding with skill population');
    
    // Get the program from Program Enrollment
    console.log('Fetching Program Enrollment...');
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Program Enrollment',
            filters: {
                'student': frm.doc.student,
                'academic_year': frm.doc.academic_year,
                'docstatus': 1
            },
            fields: ['program'],
            limit_page_length: 1
        },
        callback: function(r) {
            console.log('Program Enrollment response:', r);
            
            if (r.message && r.message.length > 0) {
                let program = r.message[0].program;
                console.log('Found program:', program);
                
                // Fetch School Settings (Single DocType)
                console.log('Fetching School Settings...');
                frappe.call({
                    method: 'frappe.client.get',
                    args: {
                        doctype: 'School Settings',
                        name: 'School Settings'
                    },
                    callback: function(r) {
                        console.log('School Settings response:', r);
                        
                        if (r.message) {
                            let settings = r.message;
                            let school_level = null;
                            let psychomotor_field = null;
                            let affective_field = null;
                            
                            // Check if program is in Primary or Secondary
                            let primary_programs = (settings.primary_programs || []).map(p => p.program);
                            let secondary_programs = (settings.secondary_programs || []).map(p => p.program);
                            
                            console.log('Primary Programs:', primary_programs);
                            console.log('Secondary Programs:', secondary_programs);
                            console.log('Looking for program:', program);
                            
                            // Determine school level
                            if (primary_programs.includes(program)) {
                                school_level = 'Primary';
                                psychomotor_field = 'primary_psychomotor_skills';
                                affective_field = 'primary_affective_skills';
                                console.log('Found in PRIMARY');
                            } else if (secondary_programs.includes(program)) {
                                school_level = 'Secondary';
                                psychomotor_field = 'secondary_psychomotor_skills';
                                affective_field = 'secondary_affective_skills';
                                console.log('Found in SECONDARY');
                            }
                            
                            console.log('Detected School Level:', school_level);
                            
                            // Populate skills if school level determined
                            if (school_level && psychomotor_field && affective_field) {
                                console.log('Clearing tables...');
                                // Clear existing rows
                                frm.clear_table('psychomotor_skills');
                                frm.clear_table('affective_skills');
                                
                                // Populate psychomotor skills
                                console.log('Psychomotor field:', psychomotor_field);
                                console.log('Psychomotor skills data:', settings[psychomotor_field]);
                                
                                if (settings[psychomotor_field] && settings[psychomotor_field].length > 0) {
                                    settings[psychomotor_field].forEach(skill => {
                                        console.log('Adding psychomotor skill:', skill.skill_name);
                                        let row = frm.add_child('psychomotor_skills');
                                        row.skill = skill.skill_name;
                                    });
                                    console.log('Added', settings[psychomotor_field].length, 'psychomotor skills');
                                } else {
                                    console.log('No psychomotor skills found');
                                }
                                
                                // Populate affective skills
                                console.log('Affective field:', affective_field);
                                console.log('Affective skills data:', settings[affective_field]);
                                
                                if (settings[affective_field] && settings[affective_field].length > 0) {
                                    settings[affective_field].forEach(skill => {
                                        console.log('Adding affective skill:', skill.skill_name);
                                        let row = frm.add_child('affective_skills');
                                        row.skill = skill.skill_name;
                                    });
                                    console.log('Added', settings[affective_field].length, 'affective skills');
                                } else {
                                    console.log('No affective skills found');
                                }
                                
                                console.log('Refreshing fields...');
                                frm.refresh_field('psychomotor_skills');
                                frm.refresh_field('affective_skills');
                                
                                let skill_count = (settings[psychomotor_field] || []).length + (settings[affective_field] || []).length;
                                frappe.msgprint(`✓ Skills populated for ${school_level} School (${program}) - ${skill_count} skills added`);
                            } else {
                                console.log('School level not determined');
                                frappe.msgprint(`✗ Program "${program}" not found in Primary or Secondary School Programs`);
                            }
                        } else {
                            console.log('Could not fetch School Settings');
                            frappe.msgprint('Could not fetch School Settings');
                        }
                    }
                });
            } else {
                console.log('No Program Enrollment found');
                frappe.msgprint('No Program Enrollment found for this student');
            }
        }
    });
}