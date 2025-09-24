/* General App Styling */
body, .stApp {
    background-color: #F0F2F6; /* Matches config.toml backgroundColor */
}

/* App Header */
.app-header {
    background-color: #FFFFFF;
    padding: 1.5rem 2rem;
    border-radius: 10px;
    margin-bottom: 2rem;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.04);
}

.app-header h1 {
    color: #1E88E5; /* Matches config.toml primaryColor */
    font-size: 2.2rem;
    margin: 0;
    padding-bottom: 0.2rem;
}

.app-header p {
    color: #5A5A5A;
    font-size: 1.1rem;
    margin: 0;
}

/* Main Content Containers (Used in Python with st.container(border=True)) */
[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #FFFFFF;
    border-radius: 10px;
    padding: 1.5rem;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.04);
    border: none !important; /* Override default border */
}

/* --- Component Styling --- */

/* Buttons */
.stButton>button {
    background-color: #1E88E5;
    color: white;
    border-radius: 8px;
    font-weight: 600;
    padding: 0.6em 1.5em;
    font-size: 1em;
    border: none;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    transition: all 0.2s ease-in-out;
}

.stButton>button:hover {
    background-color: #1565C0; /* A darker blue for hover */
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.15);
}

/* Input Fields */
.stTextInput>div>input, .stSelectbox>div>div, .stTextArea textarea, .stNumberInput input, .stDateInput input {
    border-radius: 8px;
    background: #F0F2F6;
    border: 1px solid #D1D5DB;
    padding: 0.5em;
    font-size: 1em;
    transition: border-color 0.2s, box-shadow 0.2s;
}

.stTextInput>div>input:focus, .stSelectbox>div>div:focus-within, .stTextArea textarea:focus, .stNumberInput input:focus, .stDateInput input:focus {
    border-color: #1E88E5;
    box-shadow: 0 0 0 2px rgba(30, 136, 229, 0.2);
    outline: none;
}

/* Dataframe */
.stDataFrame {
    padding: 0;
    border: none;
    box-shadow: none;
}

/* Subheaders */
h2 {
    color: #31333F;
    font-weight: 600;
    border-bottom: 2px solid #E0E0E0;
    padding-bottom: 0.5rem;
    margin-bottom: 1.5rem;
}
