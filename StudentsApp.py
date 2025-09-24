import streamlit as st
import pandas as pd
import gspread
import datetime
from google.oauth2.service_account import Credentials
import os
from streamlit_option_menu import option_menu

# --- CONFIGURATION ---
st.set_page_config(
    page_title="Student Management App",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- GOOGLE SHEETS SETUP ---
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
SHEET_ID = "1mRJvSe6hU9GZzoFh6JxSWu9llLfMOrKy6tGS4nkVBb0" # Your Sheet ID
SHEET_NAME = "Main" # Your Sheet Name
SCHOOL_YEARS = ["2m", "3m", "4m", "1S"]
STUDY_MONTHS = ["October", "November", "December", "January", "February", "March", "April", "May", "June"]

# --- AUTHENTICATION ---
@st.cache_resource
def get_gsheet():
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            if "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace('\\n', '\n')
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
        else:
            creds_file = ".streamlit/secrets.toml" # Or your local JSON file path
            if os.path.exists(creds_file):
                creds = Credentials.from_service_account_file(creds_file, scopes=SCOPE)
            else:
                st.error("❌ Credentials not found. Configure secrets or add a local credentials file.")
                st.stop()
        
        client = gspread.authorize(creds)
        return client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
        
    except Exception as e:
        st.error(f"❌ Authentication Error: {str(e)}")
        st.stop()

# --- DATA FUNCTIONS ---
@st.cache_data(ttl=60)
def get_students_df(_sheet):
    data = _sheet.get_all_records()
    df = pd.DataFrame(data)
    all_cols = ['Note', 'Last Name', 'First Name', 'School Year', 'Status', 'Payment'] + STUDY_MONTHS
    for col in all_cols:
        if col not in df.columns:
            df[col] = ''
    return df

def add_student(sheet, family_name: str, first_name: str, school_year: str, note="", status="A", payment=1500, subscription_date=None):
    if subscription_date is None:
        subscription_date = datetime.datetime.now().strftime("%Y-%m-%d")
    sheet.append_row([note, family_name, first_name, school_year, status, payment, subscription_date])

def identify_student_row(df, last_name, first_name):
    idx = df.index[(df['Last Name'] == last_name) & (df['First Name'] == first_name)].tolist()
    if idx:
        return idx[0] + 2
    return None

def submit_payment(sheet, df, last_name, first_name, month):
    row = identify_student_row(df, last_name, first_name)
    if row and month in df.columns:
        col_idx = df.columns.get_loc(month) + 1
        sheet.update_cell(row, col_idx, "P")

def change_status(sheet, df, last_name, first_name, status):
    row = identify_student_row(df, last_name, first_name)
    if row:
        sheet.update_cell(row, 5, status)

# --- UI & APP LOGIC ---
def main():
    # --- LOAD CSS ---
    css_path = os.path.join(os.path.dirname(__file__), ".streamlit", "style.css")
    if os.path.exists(css_path):
        with open(css_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
            
    sheet = get_gsheet()
    
    # --- SIDEBAR NAVIGATION ---
    with st.sidebar:
        st.markdown("## 🎓 Student Hub")
        selected = option_menu(
            None,
            ["Dashboard", "Add Student", "Log Payment", "Manage Status"],
            icons=["table", "person-plus", "cash-coin", "gear"],
            menu_icon="cast",
            default_index=0,
        )
    
    df = get_students_df(sheet)

    # --- PAGE 1: VIEW STUDENTS ---
    if selected == "Dashboard":
        st.header("Student Dashboard")
        with st.container():
            search_query = st.text_input("Search Students...", placeholder="Search by name...")
            if search_query:
                filtered_df = df[
                    df['Last Name'].str.contains(search_query, case=False, na=False) |
                    df['First Name'].str.contains(search_query, case=False, na=False)
                ]
            else:
                filtered_df = df
            
            # FIX 3: Change the index to start from 1 instead of 0 for display
            display_df = filtered_df.copy()
            display_df.index = range(1, len(display_df) + 1)
            
            st.dataframe(display_df.astype(str), use_container_width=True)

    # --- PAGE 2: ADD STUDENT ---
    elif selected == "Add Student":
        st.header("Add a New Student")
        with st.form("add_student_form"):
            st.markdown("##### Student Information")
            col1, col2 = st.columns(2)
            with col1:
                last_name = st.text_input("Last Name", key="last_name")
            with col2:
                first_name = st.text_input("First Name", key="first_name")
            
            st.markdown("##### Enrollment Details")
            col3, col4 = st.columns(2)
            with col3:
                school_year = st.selectbox("School Year", SCHOOL_YEARS, key="school_year")
            with col4:
                payment = st.number_input("Payment Amount (DZD)", min_value=1000, value=1500, step=100)
            
            note = st.text_area("Notes (Optional)")

            submitted = st.form_submit_button("✓ Add Student", use_container_width=True)
            if submitted:
                if not last_name or not first_name:
                    st.error("First and Last Name are required.")
                else:
                    add_student(sheet, last_name, first_name, school_year, note=note, payment=payment)
                    st.success("✅ Student added successfully!")
                    st.cache_data.clear()

    # --- PAGE 3: SUBMIT PAYMENT ---
    elif selected == "Log Payment":
        st.header("Log a Payment")
        if df.empty:
            st.warning("No students found. Please add a student first.")
        else:
            col1, col2 = st.columns([2, 1])
            with col1:
                student_options = (df['Last Name'] + ", " + df['First Name']).tolist()
                selected_student = st.selectbox("Select Student", student_options)
                last_name, first_name = [s.strip() for s in selected_student.split(",", 1)]
                
                month_map = { 10: "October", 11: "November", 12: "December", 1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June" }
                current_month_name = month_map.get(datetime.datetime.now().month, "October")
                month = st.selectbox("For Month", STUDY_MONTHS, index=STUDY_MONTHS.index(current_month_name) if current_month_name in STUDY_MONTHS else 0)

            if st.button("Submit Payment", use_container_width=True, type="primary"):
                submit_payment(sheet, df, last_name, first_name, month)
                st.success(f"✅ Payment for {month} submitted for {first_name} {last_name}!")
                st.cache_data.clear()

    # --- PAGE 4: CHANGE STATUS ---
    elif selected == "Manage Status":
        st.header("Manage Student Status")
        if df.empty:
            st.warning("No students found. Please add a student first.")
        else:
            col1, col2 = st.columns([2, 1])
            with col1:
                student_options = (df['Last Name'] + ", " + df['First Name']).tolist()
                selected_student = st.selectbox("Select Student", student_options)
                last_name, first_name = [s.strip() for s in selected_student.split(",", 1)]
            with col2:
                status = st.selectbox("Set New Status", ["A", "N"], help="A: Active, N: Not Active")

            if st.button("Update Status", use_container_width=True, type="primary"):
                change_status(sheet, df, last_name, first_name, status)
                st.success(f"✅ Status updated for {first_name} {last_name}!")
                st.cache_data.clear()

if __name__ == "__main__":
    main()
