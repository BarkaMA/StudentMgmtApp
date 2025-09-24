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

schoolYears = ["2m", "3m", "4m", "1S"]

@st.cache_resource
def get_gsheet():
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            if "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace('\\n', '\n')
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
        else:
            creds = Credentials.from_service_account_file("studentsapp-472017-461b21a048f8.json", scopes=SCOPE)
        
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
        return sheet
        
    except Exception as e:
        st.error(f"❌ Authentication error: {str(e)}")
        st.stop()

@st.cache_data(ttl=30)  # Cache for 30 seconds to improve performance
def get_students_df(sheet):
    try:
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"❌ Error reading sheet data: {str(e)}")
        return pd.DataFrame()

def add_student(sheet, familyName: str, firstName: str, schoolyear: str, subscriptionDate="", note="", status="A", payment: int=1500):
    sheet.append_row([note, familyName, firstName, schoolyear, status, payment, subscriptionDate])
    st.cache_data.clear()  # Clear cache to refresh data

def identify_student(sheet, last_name, first_name):
    df = get_students_df(sheet)
    idx = df.index[(df['Last Name'] == last_name) & (df['First Name'] == first_name)].tolist()
    if idx:
        return idx[0] + 2
    return None

def submit_payment(sheet, last_name, first_name, month):
    df = get_students_df(sheet)
    row = identify_student(sheet, last_name, first_name)
    if row:
        if month in df.columns:
            col_idx = df.columns.get_loc(month) + 1
            sheet.update_cell(row, col_idx, "P")
            st.cache_data.clear()  # Clear cache to refresh data

def change_status(sheet, last_name, first_name, status):
    row = identify_student(sheet, last_name, first_name)
    if row:
        sheet.update_cell(row, 5, status)
        st.cache_data.clear()  # Clear cache to refresh data

def main():
    st.set_page_config(
        page_title="Student Management System",
        page_icon="🎓",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Enhanced CSS styling
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem 1.5rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
    }
    .stSelectbox > div > div > select {
        border-radius: 8px;
    }
    .stButton > button {
        border-radius: 8px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border: none;
        color: white;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    </style>
    """, unsafe_allow_html=True)

    # Modern header
    st.markdown("""
    <div class="main-header">
        <h1 style="color: white; margin-bottom: 0.3em; font-size: 2.5rem;">🎓 Student Management System</h1>
        <p style="color: rgba(255,255,255,0.9); font-size: 1.2em; margin-bottom: 0;">Streamline student enrollment, payments, and status tracking</p>
        <small style="color: rgba(255,255,255,0.7);">Developed by MA.Barka</small>
    </div>
    """, unsafe_allow_html=True)

    # Initialize sheet
    sheet = get_gsheet()
    df = get_students_df(sheet)

    # Sidebar with improved styling
    st.sidebar.markdown("### 📋 Navigation")
    menu_options = [
        ("🔍", "View Students", "Browse all enrolled students"),
        ("➕", "Add Student", "Register new student"),
        ("💰", "Submit Payment", "Record monthly payments"),
        ("🔄", "Change Status", "Update student status")
    ]
    
    menu_labels = [f"{emoji} {label}" for emoji, label, _ in menu_options]
    menu = st.sidebar.selectbox("Select Action", menu_labels, key="menu_select")
    
    # Show description in sidebar
    selected_idx = menu_labels.index(menu)
    st.sidebar.info(f"📝 {menu_options[selected_idx][2]}")

    # Dashboard metrics in sidebar
    if not df.empty:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📊 Quick Stats")
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            total_students = len(df)
            active_students = len(df[df['Status'] == 'A']) if 'Status' in df.columns else 0
            st.metric("Total Students", total_students)
        with col2:
            st.metric("Active", active_students)

    # Main content area
    if menu == menu_labels[0]:  # View Students
        st.markdown("## 👥 Student Directory")
        
        if df.empty:
            st.warning("📭 No students found. Add some students to get started!")
        else:
            # Search and filter options
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                search_term = st.text_input("🔍 Search students", placeholder="Enter name...")
            with col2:
                if 'Status' in df.columns:
                    status_filter = st.selectbox("Filter by Status", ["All", "Active", "Inactive"])
            with col3:
                if len(schoolYears) > 0:
                    year_filter = st.selectbox("Filter by Year", ["All"] + schoolYears)
            
            # Apply filters
            filtered_df = df.copy()
            
            if search_term:
                mask = (filtered_df['Last Name'].str.contains(search_term, case=False, na=False) | 
                       filtered_df['First Name'].str.contains(search_term, case=False, na=False))
                filtered_df = filtered_df[mask]
            
            if 'Status' in df.columns and status_filter != "All":
                status_code = "A" if status_filter == "Active" else "N"
                filtered_df = filtered_df[filtered_df['Status'] == status_code]
            
            if year_filter != "All":
                filtered_df = filtered_df[filtered_df['School Year'] == year_filter]
            
            st.info(f"📋 Showing {len(filtered_df)} of {len(df)} students")
            
            # Enhanced dataframe display
            if not filtered_df.empty:
                st.dataframe(
                    filtered_df.astype(str), 
                    use_container_width=True,
                    height=400
                )
            else:
                st.warning("🔍 No students match your search criteria.")

    elif menu == menu_labels[1]:  # Add Student
        st.markdown("## ➕ Student Registration")
        
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
                    else:
                        add_student(sheet, lastName, firstName, schoolyear, 
                                  subscriptionDate=today.strftime("%b %d"), 
                                  note=note, payment=payment)
                        st.success(f"✅ {firstName} {lastName} has been registered successfully!")

    elif menu == menu_labels[2]:  # Submit Payment
        st.markdown("## 💰 Payment Processing")
        
        if df.empty:
            st.warning("📭 No students available. Please add students first.")
        else:
            with st.form("payment_form"):
                # Student selection with better formatting
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
                    st.info(f"📊 Status: {'Active' if student_info.get('Status') == 'A' else 'Inactive'}")
                
                # Month selection with smart default
                study_months = ["October", "November", "December", "January", "February", "March", "April", "May", "June"]
                month_map = {10: "October", 11: "November", 12: "December", 1: "January", 
                           2: "February", 3: "March", 4: "April", 5: "May", 6: "June"}
                
                current_month = datetime.datetime.now().month
                default_month = month_map.get(current_month, "October")
                default_index = study_months.index(default_month) if default_month in study_months else 0
                
                month = st.selectbox("📅 Payment Month", study_months, index=default_index)
                
                # Show payment status for this month if available
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

    elif menu == menu_labels[3]:  # Change Status
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
