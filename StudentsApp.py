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
SHEET_ID = "1mRJvSe6hU9GZzoFh6JxSWu9llLfMOrKy6tGS4nkVBb0"  # Replace with your Google Sheet ID
SHEET_NAME = "Main"            # Replace with your sheet name

# Load credentials from a JSON file you download from Google Cloud Console
CREDS_FILE = "studentsapp-472017-461b21a048f8.json"  # Place this file in your project directory
#CREDS_FILE = ".streamlit/secrets.toml"
#CREDS_FILE = st.secrets
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
            st.success("✅ Using Streamlit secrets for authentication")
        else:
            # Fallback to local file (for local development)
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

@st.cache_data(ttl=30)  # Cache for 30 seconds
def get_students_df(_sheet):
    data = _sheet.get_all_records()
    return pd.DataFrame(data)

# Need to add subscriptionDate automatically as today's date
def add_student(sheet,familyName: str, firstName: str,schoolyear: int,subscriptionDate="", note="", status="A",payment:int=1500):
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
        # Optionally, you can log the payment date or amount elsewhere if needed

def change_status(sheet, last_name, first_name, status):
    row = identify_student(sheet, last_name, first_name)
    if row:
        # Update the status column (adjust column index as needed)
        sheet.update_cell(row, 5, status)  # Assuming Status is column 5



def main():
    st.set_page_config(
        page_title="Student Management App",
        page_icon="🎓",
        layout="centered",
        initial_sidebar_state="expanded",  # Expand sidebar for the menu
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
        st.rerun()
    
    if st.sidebar.button(
        "➕ Add Student",
        use_container_width=True,
        help="Register a new student"
    ):
        st.session_state.current_page = 'add'
        st.rerun()
    
    if st.sidebar.button(
        "💰 Submit Payment",
        use_container_width=True,
        help="Record a payment for a student"
    ):
        st.session_state.current_page = 'payment'
        st.rerun()
    
    if st.sidebar.button(
        "🟢 Change Status",
        use_container_width=True,
        help="Update student status (Active/Non-active)"
    ):
        st.session_state.current_page = 'status'
        st.rerun()
    
    # Handle menu selections based on session state
    if st.session_state.current_page == 'view':
        st.header("📊 Student List")
        with st.spinner("Loading data..."):
            df = get_students_df(sheet)
            # Reset index to start from 1 instead of 0
            df.index = df.index + 1
            st.dataframe(df.astype(str), use_container_width=True)  # Convert to string only for display

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
        # set subscription date with today's date as default
        today = st.date_input("🗓️ Subscription Date", datetime.datetime.now()).strftime("%b %d")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("➕ Add Student", use_container_width=True):
                if not lastName or not firstName:
                    st.error("Last Name and First Name are required.")
                else:
                    add_student(sheet, lastName, firstName, schoolyear, subscriptionDate= today, note=note, payment= payment)
                    st.success("✅ Student added successfully!")
                    st.session_state.current_page = 'add'  # Stay on add page after success
                    st.cache_data.clear()

    elif st.session_state.current_page == 'payment':
        st.header("💰 Submit Payment")
        df = get_students_df(sheet)
        student_options = df['Last Name'] + ", " + df['First Name']
        selected = st.selectbox("👤 Select Student", student_options)
        last_name, first_name = [s.strip() for s in selected.split(",", 1)]
        # Read amount from the student's Payment column
        student = df[(df['Last Name'] == last_name) & (df['First Name'] == first_name)].iloc[0]
        amount = student['Payment']
        st.info(f"💵 Payment amount: {amount}")
        # Payment date input , and to set default month)
        payment_date = datetime.datetime.now()

        study_months = ["October", "November", "December", "January", "February", "March", "April", "May", "June"]
        # Map Python month to my sheet's month columns
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

    else:
        # Show welcome message when no menu is selected
        st.markdown("""
        <div style="text-align: center; padding: 2em; background: #f8f9fa; border-radius: 12px; margin-top: 2em;">
            <h3 style="color: #4CAF50;">👋 Welcome to Student Management</h3>
            <p style="color: #666; font-size: 1.1em;">Select an action from the sidebar to get started</p>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
