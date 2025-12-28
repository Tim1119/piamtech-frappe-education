import frappe
import random
from datetime import datetime, timedelta

# Nigerian states
states = ["Abia", "Adamawa", "Akwa Ibom", "Anambra", "Bauchi", "Bayelsa", "Benue", "Borno", 
          "Cross River", "Delta", "Ebonyi", "Edo", "Ekiti", "Enugu", "FCT", "Gombe", "Imo", 
          "Jigawa", "Kaduna", "Kano", "Katsina", "Kebbi", "Kogi", "Kwara", "Lagos", "Nasarawa", 
          "Niger", "Ogun", "Ondo", "Osun", "Oyo", "Plateau", "Rivers", "Sokoto", "Taraba", 
          "Yobe", "Zamfara"]

religions = ["Christian", "Muslim", "African Traditional Religion", "Others"]

# Sample first names (Nigerian)
first_names = ["Chisom", "Amara", "Tunde", "Zainab", "Obinna", "Fatima", "Adeyemi", "Ngozi", 
               "Emeka", "Aisha", "Adekunle", "Chizoba", "Seun", "Nkemdilim", "Babajide", "Hauwa"]

# Sample last names (Nigerian)
last_names = ["Okafor", "Adebayo", "Nwosu", "Ibrahim", "Oluwaseun", "Ezeokafor", "Mohammed", 
              "Eze", "Adeleke", "Amin", "Usman", "Chidinma", "Okoro", "Hassan", "Bello", "Duru"]

def create_random_students(count=10):
    """Create random Nigerian students"""
    created_students = []
    
    for i in range(count):
        try:
            # Generate random data
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            religion = random.choice(religions)
            state = random.choice(states)
            
            # Generate random DOB (between 16-25 years old)
            days_ago = random.randint(365 * 16, 365 * 25)
            dob = datetime.now() - timedelta(days=days_ago)
            
            # Create student document
            student = frappe.get_doc({
                'doctype': 'Student',
                'first_name': first_name,
                'last_name': last_name,
                'date_of_birth': dob.date(),
                'gender': random.choice(['Male', 'Female']),
                'nationality': 'Nigerian',
                'religion': religion,
                'state_of_origin': state,
                'email': f"{first_name.lower()}.{last_name.lower()}{random.randint(100, 999)}@example.com"
            })
            
            student.insert(ignore_permissions=True)
            created_students.append(student.name)
            print(f"✓ Created Student: {student.name} - {first_name} {last_name}")
            
        except Exception as e:
            print(f"✗ Error creating student {i+1}: {str(e)}")
    
    frappe.db.commit()
    print(f"\n✓ Successfully created {len(created_students)} students!")
    return created_students

# Run the function
if __name__ == "__main__":
    create_random_students(10)