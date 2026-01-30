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

CREDS_FILE = "studentsapp-472017-461b21a048f8.json"
schoolYears = ["3m", "4m", "1s", "2s"]

@st.cache_resource
def get_gsheet():
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            if "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace('\\n', '\n')
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
            st.success("✅ Using Streamlit secrets for authentication")
        else:
            if os.path.exists(CREDS_FILE):
                creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPE)
                st.info("🔑 Using local credentials file")
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

@st.cache_data(ttl=30)
def get_students_df(_sheet):
    data = _sheet.get_all_records()
    return pd.DataFrame(data)

def add_student(sheet, familyName: str, firstName: str, schoolyear: int, subscriptionDate="", note="", status="A", payment: int=1500):
    # Find the first empty row
    all_values = sheet.get_all_values()
    first_empty_row = len(all_values) + 1
    
    # Check if there are empty rows between data
    for i, row in enumerate(all_values[1:], start=2):  # Skip header
        if not any(row):  # If row is completely empty
            first_empty_row = i
            break
    
    # Insert data in correct column order
    row_data = [note, familyName, firstName, schoolyear, status, payment, subscriptionDate]
    sheet.insert_row(row_data, first_empty_row)

def identify_student(sheet, last_name, first_name):
    """Return the row number (1-indexed) of the student with given last and first name, or None if not found."""
    df = get_students_df(sheet)
    idx = df.index[(df['Last Name'] == last_name) & (df['First Name'] == first_name)].tolist()
    if idx:
        return idx[0] + 2
    return None

def submit_payment(sheet, last_name, first_name, month):
    df = get_students_df(sheet)
    row = identify_student(sheet, last_name, first_name)
    if row:
        student = df[(df['Last Name'] == last_name) & (df['First Name'] == first_name)].iloc[0]
        amount = student['Payment']
        if month in df.columns:
            col_idx = df.columns.get_loc(month) + 1
            sheet.update_cell(row, col_idx, "P")

def change_status(sheet, last_name, first_name, status):
    row = identify_student(sheet, last_name, first_name)
    if row:
        sheet.update_cell(row, 5, status)

def collapse_sidebar():
    """Auto-collapse sidebar after selecting an option"""
    st.session_state.sidebar_state = 'collapsed'

def expand_sidebar():
    """Expand sidebar after successful operation"""
    st.session_state.sidebar_state = 'expanded'

def main():
    # Initialize sidebar state
    if 'sidebar_state' not in st.session_state:
        st.session_state.sidebar_state = 'expanded'
    
    st.set_page_config(
        page_title="Student Management App",
        page_icon="🎓",
        layout="centered",
        initial_sidebar_state=st.session_state.sidebar_state,
    )
    
    # Load custom CSS
    css_path = os.path.join(os.path.dirname(__file__), ".streamlit", "style.css")
    if os.path.exists(css_path):
        with open(css_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    st.markdown("""
    <div class="main-header" style="background: linear-gradient(90deg, #4CAF50 0%, #81C784 100%); padding: 1.2em 1em; border-radius: 12px; margin-bottom: 1.5em;">
        <h1 style="color: white; margin-bottom: 0.2em;">🎓 Student Management App</h1>
        <p style="color: #f5f5f5; font-size: 1.1em;">Easily manage students, payments, and status            Made by MA.Barka.</p>
    </div>
    """, unsafe_allow_html=True)

    sheet = get_gsheet()
    
    # Initialize session state for current page
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'welcome'
    
    # Sidebar menu
    st.sidebar.markdown("### 📋 Choose an Action")
    st.sidebar.markdown("---")
    
    if st.sidebar.button(
        "📊 View Students",
        use_container_width=True,
        help="View all registered students and their information"
    ):
        st.session_state.current_page = 'view'
        collapse_sidebar()
        st.rerun()
    
    if st.sidebar.button(
        "➕ Add Student",
        use_container_width=True,
        help="Register a new student"
    ):
        st.session_state.current_page = 'add'
        collapse_sidebar()
        st.rerun()
    
    if st.sidebar.button(
        "💰 Submit Payment",
        use_container_width=True,
        help="Record a payment for a student"
    ):
        st.session_state.current_page = 'payment'
        collapse_sidebar()
        st.rerun()
    
    if st.sidebar.button(
        "🟢 Change Status",
        use_container_width=True,
        help="Update student status (Active/Non-active)"
    ):
        st.session_state.current_page = 'status'
        collapse_sidebar()
        st.rerun()
    
    # Handle menu selections based on session state
    if st.session_state.current_page == 'view':
        st.header("📊 Student List")
        with st.spinner("Loading data..."):
            df = get_students_df(sheet)
            df.index = df.index + 1
            st.dataframe(df.astype(str), use_container_width=True)

    elif st.session_state.current_page == 'add':
        st.header("➕ Add New Student")

        col1, col2 = st.columns(2)
        with col1:
            lastName = st.text_input("👤 Last Name", key="last_name", help="Enter the student's last name")
        with col2:
            firstName = st.text_input("👤 First Name", key="first_name", help="Enter the student's first name")
        schoolyear = st.selectbox("📢 School Year", schoolYears, key="school_year")
        note = st.text_area("📝 Note")
        payment = st.number_input("💲 Payment Amount", min_value=1000, value=1500, step=100)
        today = st.date_input("🗓️ Subscription Date", datetime.datetime.now()).strftime("%b %d")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("➕ Add Student", use_container_width=True):
                if not lastName or not firstName:
                    st.error("Last Name and First Name are required.")
                else:
                    add_student(sheet, lastName, firstName, schoolyear, subscriptionDate=today, note=note, payment=payment)
                    st.success("✅ Student added successfully!")
                    expand_sidebar()
                    st.cache_data.clear()
                    st.rerun()

    elif st.session_state.current_page == 'payment':
        st.header("💰 Submit Payment")
        df = get_students_df(sheet)
        student_options = df['Last Name'] + ", " + df['First Name']
        selected = st.selectbox("👤 Select Student", student_options)
        last_name, first_name = [s.strip() for s in selected.split(",", 1)]
        student = df[(df['Last Name'] == last_name) & (df['First Name'] == first_name)].iloc[0]
        amount = student['Payment']
        st.info(f"💵 Payment amount: {amount}")
        payment_date = datetime.datetime.now()

        study_months = ["October", "November", "December", "January", "February", "March", "April", "May", "June"]
        month_map = {
            10: "October",
            11: "November",
            12: "December",
            1: "January",
            2: "February",
            3: "March",
            4: "April",
            5: "May",
            6: "June"
        }
        default_month = month_map.get(payment_date.month, "October")
        month = st.selectbox(
            "📅 Select Month",
            study_months,
            index=study_months.index(default_month))
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("💵 Submit Payment", use_container_width=True):
                submit_payment(sheet, last_name, first_name, month)
                st.success(f"✅ Payment submitted for {month}!")
                expand_sidebar()
                st.rerun()

    elif st.session_state.current_page == 'status':
        st.header("🟢 Change Student Status")
        df = get_students_df(sheet)
        student_options = df['Last Name'] + ", " + df['First Name']
        selected = st.selectbox("👤 Select Student", student_options)
        last_name, first_name = [s.strip() for s in selected.split(",", 1)]
        status = st.selectbox("📊 New Status", ["A", "N"], format_func=lambda x: "Active" if x == "A" else "Non-active")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔄 Update Status", use_container_width=True):
                change_status(sheet, last_name, first_name, status)
                st.success("✅ Status updated successfully!")
                expand_sidebar()
                st.rerun()

    else:
        st.markdown("""
        <div style="text-align: center; padding: 2em; background: #f8f9fa; border-radius: 12px; margin-top: 2em;">
            <h3 style="color: #4CAF50;">👋 Welcome to Student Management</h3>
            <p style="color: #666; font-size: 1.1em;">Select an action from the sidebar to get started</p>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
