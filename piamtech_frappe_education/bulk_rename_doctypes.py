import frappe
import json

def bulk_rename_doctypes():
    """Bulk rename doctypes by creating/updating Property Setters"""
    
    renames = {
        'Program': 'Class',
        'Course': 'Subject',
        'Student Group': 'Class Arm',
        'Program Enrollment': 'Class Enrollment',
        'Course Enrollment': 'Subject Enrollment',
    }
    
    property_setters = []
    
    for doctype_name, new_label in renames.items():
        try:
            # Create or update Property Setter
            ps_name = f"{doctype_name}-label"
            
            if frappe.db.exists('Property Setter', ps_name):
                # Update existing
                ps = frappe.get_doc('Property Setter', ps_name)
                ps.value = new_label
                ps.save(ignore_permissions=True)
                print(f"✓ Updated Property Setter: {doctype_name} -> {new_label}")
            else:
                # Create new
                ps = frappe.get_doc({
                    'doctype': 'Property Setter',
                    'name': ps_name,
                    'doc_type': doctype_name,
                    'doctype_or_field': 'DocType',
                    'property': 'label',
                    'value': new_label,
                    'module': 'Piamtech Frappe Education'
                })
                ps.insert(ignore_permissions=True)
                print(f"✓ Created Property Setter: {doctype_name} -> {new_label}")
            
            # Add to export list
            property_setters.append({
                'doctype': 'Property Setter',
                'name': ps_name,
                'doc_type': doctype_name,
                'doctype_or_field': 'DocType',
                'property': 'label',
                'value': new_label,
                'module': 'Piamtech Frappe Education'
            })
        
        except Exception as e:
            print(f"✗ Error renaming {doctype_name}: {str(e)}")
    
    frappe.db.commit()
    
    # Print JSON for exporting
    print("\n" + "="*60)
    print("Copy this JSON to property_setter.json:")
    print("="*60)
    print(json.dumps(property_setters, indent=2))
    
    print(f"\n✓ Bulk rename complete! {len(property_setters)} Property Setters created/updated")
    
    return property_setters


# Run it
if __name__ == "__main__":
    bulk_rename_doctypes()