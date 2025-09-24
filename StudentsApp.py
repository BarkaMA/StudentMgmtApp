import streamlit as st
import pandas as pd
import gspread
import datetime
from google.oauth2.service_account import Credentials
import os

# Google Sheets setup
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
SHEET_ID = "1mRJvSe6hU9GZzoFh6JxSWu9llLfMOrKy6tGS4nkVBb0"
SHEET_NAME = "Main"
CREDS_FILE = ".streamlit/secrets.toml"
schoolYears = ["2m", "3m", "4m", "1S"]

@st.cache_resource
def get_gsheet():
    try:
        # Try to load from Streamlit secrets (for deployment)
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            # Ensure private_key has proper line breaks
            if "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace('\\n', '\n')
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
        else:
            # Fallback to local file (for local development)
            if os.path.exists(CREDS_FILE):
                creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPE)
                st.info("📁 Using local credentials file")
            else:
                st.error("❌ No credentials found. Please configure secrets in Streamlit Cloud or add the JSON file locally.")
                st.stop()
        
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
        return sheet
        
    except Exception as e:
        st.error(f"❌ Authentication error: {str(e)}")
        st.error("Please check your Google service account credentials configuration.")
        st.stop()

def get_students_df(sheet):
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def add_student(sheet, familyName: str, firstName: str, schoolyear: str, subscriptionDate="", note="", status="A", payment: int=1500):
    sheet.append_row([note, familyName, firstName, schoolyear, status, payment, subscriptionDate])

def identify_student(sheet, last_name, first_name):
    """Return the row number (1-indexed) of the student with given last and first name, or None if not found."""
    df = get_students_df(sheet)
    idx = df.index[(df['Last Name'] == last_name) & (df['First Name'] == first_name)].tolist()
    if idx:
        return idx[0] + 2  # +2: pandas is 0-indexed, gspread is 1-indexed and header is row 1
    return None

def submit_payment(sheet, last_name, first_name, month):
    df = get_students_df(sheet)
    row = identify_student(sheet, last_name, first_name)
    if row:
        # Get the amount from the student's row (not used here, but kept for reference)
        student = df[(df['Last Name'] == last_name) & (df['First Name'] == first_name)].iloc[0]
        amount = student['Payment']
        # Use the month directly as the column name
        if month in df.columns:
            col_idx = df.columns.get_loc(month) + 1  # gspread is 1-indexed
            sheet.update_cell(row, col_idx, "P")

def change_status(sheet, last_name, first_name, status):
    row = identify_student(sheet, last_name, first_name)
    if row:
        # Update the status column (adjust column index as needed)
        sheet.update_cell(row, 5, status)  # Assuming Status is column 5

def main():
    st.set_page_config(
        page_title="Student Management System",
        page_icon="🎓",
        layout="wide",  # Changed to wide for better space utilization
        initial_sidebar_state="expanded",
    )
    
    # Load custom CSS (your existing styling will be applied)
    css_path = os.path.join(os.path.dirname(__file__), ".streamlit", "style.css")
    if os.path.exists(css_path):
        with open(css_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    # Enhanced header with your existing styling
    st.markdown("""
    <div class="main-header" style="background: linear-gradient(135deg, #4CAF50 0%, #81C784 100%); padding: 1.5em 1em; border-radius: 12px; margin-bottom: 1.5em; box-shadow: 0 4px 15px rgba(76,175,80,0.2);">
        <h1 style="color: white; margin-bottom: 0.3em;">🎓 Student Management System</h1>
        <p style="color: #f5f5f5; font-size: 1.1em;">Streamline student enrollment, payments, and status tracking • Made by MA.Barka</p>
    </div>
    """, unsafe_allow_html=True)

    sheet = get_gsheet()
    
    # Enhanced sidebar with statistics
    st.sidebar.markdown("### 📋 Navigation")
    menu_emojis = ["🔍", "➕", "💰", "🔄"]
    menu_options = ["View Students", "Add Student", "Submit Payment", "Change Status"]
    menu_labels = [f"{emoji} {option}" for emoji, option in zip(menu_emojis, menu_options)]
    
    menu = st.sidebar.selectbox("Select Action", menu_labels, key="menu_select")
    
    # Add quick stats in sidebar
    try:
        df = get_students_df(sheet)
        if not df.empty:
            st.sidebar.markdown("---")
            st.sidebar.markdown("### 📊 Quick Stats")
            
            total_students = len(df)
            active_students = len(df[df['Status'] == 'A']) if 'Status' in df.columns else 0
            
            col1, col2 = st.sidebar.columns(2)
            with col1:
                st.metric("Total", total_students)
            with col2:
                st.metric("Active", active_students)
                
            # Show recent additions
            if 'Subscription Date' in df.columns:
                st.sidebar.markdown("### 📅 Recent Additions")
                recent = df.head(3)
                for _, student in recent.iterrows():
                    st.sidebar.text(f"• {student['First Name']} {student['Last Name']}")
    except:
        df = pd.DataFrame()  # Fallback for empty sheets

    if menu == menu_labels[0]:  # "🔍 View Students"
        st.markdown("## 👥 Student Directory")
        
        if df.empty:
            st.warning("📭 No students found. Add some students to get started!")
        else:
            # Enhanced search and filters
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                search_term = st.text_input("🔍 Search students", placeholder="Enter name to search...")
            
            with col2:
                status_options = ["All"] + (["Active", "Inactive"] if 'Status' in df.columns else [])
                status_filter = st.selectbox("📊 Status", status_options)
            
            with col3:
                year_options = ["All"] + schoolYears
                year_filter = st.selectbox("🎓 Year", year_options)
            
            # Apply filters
            filtered_df = df.copy()
            
            if search_term:
                mask = (filtered_df['Last Name'].str.contains(search_term, case=False, na=False) | 
                       filtered_df['First Name'].str.contains(search_term, case=False, na=False))
                filtered_df = filtered_df[mask]
            
            if status_filter != "All" and 'Status' in df.columns:
                status_code = "A" if status_filter == "Active" else "N"
                filtered_df = filtered_df[filtered_df['Status'] == status_code]
            
            if year_filter != "All":
                filtered_df = filtered_df[filtered_df['School Year'] == year_filter]
            
            # Results info
            st.info(f"📋 Showing {len(filtered_df)} of {len(df)} students")
            
            # Enhanced dataframe display
            if not filtered_df.empty:
                st.dataframe(
                    filtered_df.astype(str), 
                    use_container_width=True,
                    height=450
                )
            else:
                st.warning("🔍 No students match your search criteria.")

    elif menu == menu_labels[1]:  # "➕ Add Student"
        st.markdown("## ➕ Student Registration")
        
        # Use form for better UX
        with st.form("add_student_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                lastName = st.text_input("👤 Last Name *", help="Student's family name")
                schoolyear = st.selectbox("🎓 School Year *", schoolYears)
                payment = st.number_input("💵 Payment Amount (DA)", min_value=1000, value=1500, step=100)
            
            with col2:
                firstName = st.text_input("👤 First Name *", help="Student's given name")
                today = st.date_input("📅 Subscription Date", datetime.datetime.now())
            
            note = st.text_area("📝 Additional Notes", placeholder="Any special notes about the student...")
            
            submitted = st.form_submit_button("➕ Register Student", use_container_width=True)
            
            if submitted:
                if not lastName or not firstName:
                    st.error("❌ Last Name and First Name are required fields.")
                else:
                    # Check for duplicates
                    if not df.empty:
                        duplicate = df[(df['Last Name'].str.lower() == lastName.lower()) & 
                                     (df['First Name'].str.lower() == firstName.lower())]
                        if not duplicate.empty:
                            st.warning("⚠️ A student with this name already exists!")
                            st.dataframe(duplicate[['Last Name', 'First Name', 'School Year', 'Status']])
                        else:
                            add_student(sheet, lastName, firstName, schoolyear, 
                                      subscriptionDate=today.strftime("%b %d"), 
                                      note=note, payment=payment)
                            st.success(f"✅ {firstName} {lastName} has been registered successfully!")
                            st.balloons()
                    else:
                        add_student(sheet, lastName, firstName, schoolyear, 
                                  subscriptionDate=today.strftime("%b %d"), 
                                  note=note, payment=payment)
                        st.success(f"✅ {firstName} {lastName} has been registered successfully!")
                        st.balloons()

    elif menu == menu_labels[2]:  # "💰 Submit Payment"
        st.markdown("## 💰 Payment Processing")
        
        if df.empty:
            st.warning("📭 No students available. Please add students first.")
        else:
            with st.form("payment_form"):
                # Enhanced student selection
                student_options = [f"{row['Last Name']}, {row['First Name']} ({row['School Year']})" 
                                 for _, row in df.iterrows()]
                selected = st.selectbox("👤 Select Student", student_options)
                
                # Extract student info
                parts = selected.split(" (")
                name_part = parts[0]
                year_part = parts[1].rstrip(")")
                last_name, first_name = [s.strip() for s in name_part.split(",", 1)]
                
                # Show student details
                student_info = df[(df['Last Name'] == last_name) & (df['First Name'] == first_name)].iloc[0]
                
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"💵 Payment Amount: {student_info['Payment']} DA")
                with col2:
                    status_text = 'Active' if student_info.get('Status') == 'A' else 'Inactive'
                    st.info(f"📊 Status: {status_text}")
                
                # Smart month selection
                study_months = ["October", "November", "December", "January", "February", "March", "April", "May", "June"]
                month_map = {10: "October", 11: "November", 12: "December", 1: "January", 
                           2: "February", 3: "March", 4: "April", 5: "May", 6: "June"}
                
                current_month = datetime.datetime.now().month
                default_month = month_map.get(current_month, "October")
                default_index = study_months.index(default_month) if default_month in study_months else 0
                
                month = st.selectbox("📅 Payment Month", study_months, index=default_index)
                
                # Show payment status
                if month in df.columns:
                    payment_status = student_info.get(month, "")
                    if payment_status == "P":
                        st.warning(f"⚠️ Payment for {month} is already recorded!")
                    else:
                        st.success(f"✅ Ready to record payment for {month}")
                
                submitted = st.form_submit_button("💵 Process Payment", use_container_width=True)
                
                if submitted:
                    submit_payment(sheet, last_name, first_name, month)
                    st.success(f"✅ Payment recorded for {first_name} {last_name} - {month}!")
                    st.balloons()

    elif menu == menu_labels[3]:  # "🔄 Change Status"
        st.markdown("## 🔄 Status Management")
        
        if df.empty:
            st.warning("📭 No students available. Please add students first.")
        else:
            with st.form("status_form"):
                student_options = [f"{row['Last Name']}, {row['First Name']} ({row['School Year']})" 
                                 for _, row in df.iterrows()]
                selected = st.selectbox("👤 Select Student", student_options)
                
                # Extract student info
                parts = selected.split(" (")
                name_part = parts[0]
                last_name, first_name = [s.strip() for s in name_part.split(",", 1)]
                
                # Show current status
                current_student = df[(df['Last Name'] == last_name) & (df['First Name'] == first_name)].iloc[0]
                current_status = current_student.get('Status', 'Unknown')
                current_status_text = 'Active' if current_status == 'A' else 'Inactive'
                
                st.info(f"📊 Current Status: {current_status_text}")
                
                status_options = ["Active", "Inactive"]
                new_status_text = st.selectbox("🔄 New Status", status_options)
                new_status = "A" if new_status_text == "Active" else "N"
                
                submitted = st.form_submit_button("🔄 Update Status", use_container_width=True)
                
                if submitted:
                    if new_status == current_status:
                        st.warning(f"⚠️ Status is already {new_status_text}")
                    else:
                        change_status(sheet, last_name, first_name, new_status)
                        st.success(f"✅ Status updated to {new_status_text} for {first_name} {last_name}!")

if __name__ == "__main__":
    main()
