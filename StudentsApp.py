import streamlit as st
import pandas as pd
import gspread
import datetime
from google.oauth2.service_account import Credentials
import os
from streamlit_option_menu import option_menu # NEW: Import for the new menu

# --- CONFIGURATION ---
st.set_page_config(
    page_title="Student Management App",
    page_icon="🎓",
    layout="centered",
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
@st.cache_data(ttl=60) # Cache data for 1 minute to avoid frequent API calls
def get_students_df(_sheet):
    data = _sheet.get_all_records()
    df = pd.DataFrame(data)
    # Ensure all columns exist, fill missing with empty strings or defaults
    all_cols = ['Note', 'Last Name', 'First Name', 'School Year', 'Status', 'Payment'] + STUDY_MONTHS
    for col in all_cols:
        if col not in df.columns:
            df[col] = ''
    return df

# CHANGED: Streamlined the function
def add_student(sheet, family_name: str, first_name: str, school_year: str, note="", status="A", payment=1500, subscription_date=None):
    if subscription_date is None:
        subscription_date = datetime.datetime.now().strftime("%Y-%m-%d")
    sheet.append_row([note, family_name, first_name, school_year, status, payment, subscription_date])

def identify_student_row(df, last_name, first_name):
    idx = df.index[(df['Last Name'] == last_name) & (df['First Name'] == first_name)].tolist()
    if idx:
        return idx[0] + 2  # +1 for header, +1 for 0-indexing -> 1-indexing
    return None

def submit_payment(sheet, df, last_name, first_name, month):
    row = identify_student_row(df, last_name, first_name)
    if row and month in df.columns:
        col_idx = df.columns.get_loc(month) + 1
        sheet.update_cell(row, col_idx, "P")

def change_status(sheet, df, last_name, first_name, status):
    row = identify_student_row(df, last_name, first_name)
    if row:
        sheet.update_cell(row, 5, status) # Column 5 is 'Status'

# --- UI & APP LOGIC ---
def main():
    # --- LOAD CSS ---
    css_path = os.path.join(os.path.dirname(__file__), ".streamlit", "style.css")
    if os.path.exists(css_path):
        with open(css_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
            
    sheet = get_gsheet()
    
    # --- HEADER ---
    st.markdown("""
        <div class="app-header">
            <h1>🎓 Student Management Dashboard</h1>
            <p>Easily manage students, payments, and status.</p>
        </div>
    """, unsafe_allow_html=True)

    # --- SIDEBAR NAVIGATION ---
    with st.sidebar:
        selected = option_menu(
            "Main Menu",
            ["View Students", "Add Student", "Submit Payment", "Change Status"],
            icons=["search", "person-plus-fill", "credit-card-fill", "toggles"],
            menu_icon="cast",
            default_index=0,
        )
    
    df = get_students_df(sheet)

    # --- PAGE 1: VIEW STUDENTS ---
    if selected == "View Students":
        st.subheader("🔎 Student List")
        with st.container(border=True):
            # NEW: Search/Filter functionality
            search_query = st.text_input("Search by name...", placeholder="Type a name to filter")
            if search_query:
                filtered_df = df[
                    df['Last Name'].str.contains(search_query, case=False, na=False) |
                    df['First Name'].str.contains(search_query, case=False, na=False)
                ]
            else:
                filtered_df = df
            
            st.dataframe(filtered_df.astype(str), use_container_width=True)

    # --- PAGE 2: ADD STUDENT ---
    elif selected == "Add Student":
        st.subheader("➕ Add New Student")
        with st.form("add_student_form"):
            col1, col2 = st.columns(2)
            with col1:
                last_name = st.text_input("Last Name", key="last_name")
            with col2:
                first_name = st.text_input("First Name", key="first_name")
            
            school_year = st.selectbox("School Year", SCHOOL_YEARS, key="school_year")
            payment = st.number_input("Payment Amount (DZD)", min_value=1000, value=1500, step=100)
            
            with st.expander("Optional Details"):
                note = st.text_area("Notes")
                sub_date = st.date_input("Subscription Date", datetime.datetime.now())

            submitted = st.form_submit_button("✓ Add Student", use_container_width=True)
            if submitted:
                if not last_name or not first_name:
                    st.error("First and Last Name are required.")
                else:
                    add_student(sheet, last_name, first_name, school_year, note=note, payment=payment, subscription_date=sub_date.strftime("%Y-%m-%d"))
                    st.success("✅ Student added successfully!")
                    st.cache_data.clear() # Clear cache to show new student immediately

    # --- PAGE 3: SUBMIT PAYMENT ---
    elif selected == "Submit Payment":
        st.subheader("💰 Submit Payment")
        with st.container(border=True):
            if df.empty:
                st.warning("No students found. Please add a student first.")
            else:
                student_options = (df['Last Name'] + ", " + df['First Name']).tolist()
                selected_student = st.selectbox("Select Student", student_options)
                
                last_name, first_name = [s.strip() for s in selected_student.split(",", 1)]
                
                student_info = df[(df['Last Name'] == last_name) & (df['First Name'] == first_name)].iloc[0]
                amount = student_info['Payment']
                st.info(f"**Payment Amount:** {amount} DZD")

                month_map = {
                    10: "October", 11: "November", 12: "December", 1: "January",
                    2: "February", 3: "March", 4: "April", 5: "May", 6: "June"
                }
                current_month_name = month_map.get(datetime.datetime.now().month, "October")
                
                month = st.selectbox(
                    "Select Month",
                    STUDY_MONTHS,
                    index=STUDY_MONTHS.index(current_month_name) if current_month_name in STUDY_MONTHS else 0
                )
                
                if st.button("💵 Submit Payment", use_container_width=True):
                    submit_payment(sheet, df, last_name, first_name, month)
                    st.success(f"✅ Payment for {month} submitted for {first_name} {last_name}!")
                    st.cache_data.clear()

    # --- PAGE 4: CHANGE STATUS ---
    elif selected == "Change Status":
        st.subheader("🔄 Change Student Status")
        with st.container(border=True):
            if df.empty:
                st.warning("No students found. Please add a student first.")
            else:
                student_options = (df['Last Name'] + ", " + df['First Name']).tolist()
                selected_student = st.selectbox("Select Student", student_options)
                
                last_name, first_name = [s.strip() for s in selected_student.split(",", 1)]
                
                status = st.selectbox("New Status", ["A", "N"], help="A: Active, N: Not Active")
                
                if st.button("Update Status", use_container_width=True):
                    change_status(sheet, df, last_name, first_name, status)
                    st.success(f"✅ Status updated for {first_name} {last_name}!")
                    st.cache_data.clear()

if __name__ == "__main__":
    main()
