import streamlit as st
import pandas as pd
import gspread
import datetime
from google.oauth2.service_account import Credentials

# Google Sheets setup
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
SHEET_ID = "1mRJvSe6hU9GZzoFh6JxSWu9llLfMOrKy6tGS4nkVBb0"  # Replace with your Google Sheet ID
SHEET_NAME = "Main"            # Replace with your sheet name

# Load credentials from a JSON file you download from Google Cloud Console
CREDS_FILE = "studentsapp-472017-461b21a048f8.json"  # Place this file in your project directory

schoolYears = ["2m", "3m", "4m", "1S"]

@st.cache_resource
def get_gsheet():
    creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPE)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
    return sheet

def get_students_df(sheet):
    data = sheet.get_all_records()
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
    initial_sidebar_state="expanded"
)
    st.title("Student Management App")
    st.write("Made by MA Barka")
    sheet = get_gsheet()
    menu_emojis = ["🔍", "➕", "💰", "🟢"]
    menu_options = [" View Students", "Add Student", "Submit Payment", "Change Status"]
    for emoji, option in zip(menu_emojis, menu_options):
        menu_options[menu_options.index(option)] = f"{emoji} {option}"
    menu = st.sidebar.selectbox("Menu", menu_options, key="menu_select")
   
    if menu == menu_options[0]:  # "🔍 View Students"
        st.header(" Student List")
        with st.spinner("Loading data..."):
            df = get_students_df(sheet)
            st.dataframe(df.astype(str))  # Convert to string only for display

    elif menu == menu_options[1]:  # "➕ Add Student"
        st.header("Add New Student")

        col1, col2 = st.columns(2)
        with col1:
            lastName = st.text_input("Last Name")
        with col2:
            firstName = st.text_input("First Name")
        schoolyear = st.selectbox("School Year", schoolYears)
        note = st.text_area("Note")
        payment = st.number_input("Payment Amount", min_value=1000, value=1500, step=100)
        # set subscription date with today's date as default
        today = st.date_input("Subscription Date", datetime.datetime.now()).strftime("%b %d")
        if st.button("(+) Add"):
            if not lastName or not firstName:
                st.error("Last Name and First Name are required.")
            else:
                add_student(sheet, lastName, firstName, schoolyear, subscriptionDate= today, note=note, payment= payment)
                st.success("Student added!")
                menu = "View Students"

    elif menu == menu_options[2]:  # "💰 Submit Payment"
        st.header("Submit Payment")
        df = get_students_df(sheet)
        student_options = df['Last Name'] + ", " + df['First Name']
        selected = st.selectbox("Select Student", student_options)
        last_name, first_name = [s.strip() for s in selected.split(",", 1)]
        # Read amount from the student's Payment column
        student = df[(df['Last Name'] == last_name) & (df['First Name'] == first_name)].iloc[0]
        amount = student['Payment']
        st.info(f"Payment amount for this student: {amount}")
        # Payment date input (for display/logging, and to set default month)
        payment_date = datetime.datetime.now()

        study_months = ["October", "November", "December", "January", "February", "March", "April", "May", "June"]
        # Map Python month to your sheet's month columns (correct spelling)
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
            "Select Month",
            study_months,
            index=study_months.index(default_month))
        
        if st.button("($) Submit Payment"):
            submit_payment(sheet, last_name, first_name, month)
            st.success(f"Payment submitted for {month}!")

    elif menu == menu_options[3]:  # "🟢 Change Status"

        df = get_students_df(sheet)
        student_options = df['Last Name'] + ", " + df['First Name']
        selected = st.selectbox("Select Student", student_options)
        last_name, first_name = [s.strip() for s in selected.split(",", 1)]
        status = st.selectbox("New Status", ["A", "N"])
        if st.button("Change Status"):
            change_status(sheet, last_name, first_name, status)
            st.success("Status updated!")

if __name__ == "__main__":
    main()