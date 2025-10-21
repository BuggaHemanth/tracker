#!/usr/bin/env python
# coding: utf-8

import os
import streamlit as st
import pandas as pd
import plotly.express as px
from fpdf import FPDF
from langchain_google_genai import ChatGoogleGenerativeAI
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Google Sheets imports
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False

# -----------------------------
# CONFIG & LOAD DATA
# -----------------------------
st.set_page_config(
    page_title="AI Maturity Assessment",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom CSS for navy blue theme
st.markdown("""
<style>
    /* Navy blue theme */
    .stApp {
        background-color: #f8f9fa;
    }
    .main .block-container {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
        margin-top: 0 !important;
        max-width: 100%;
    }

    /* Remove all empty space */
    div[data-testid="stVerticalBlock"] {
        gap: 0 !important;
    }

    div[data-testid="stVerticalBlock"] > div {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
    }

    /* Reduce title font size and spacing */
    h1 {
        color: #001f3f;
        font-size: 1.8rem !important;
        margin-top: 0 !important;
        padding-top: 0 !important;
        margin-bottom: 0.5rem !important;
    }
    h2 {
        color: #001f3f;
        font-size: 1.4rem !important;
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }
    h3 {
        color: #001f3f;
        font-size: 1.2rem !important;
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }

    /* Increase question font size and reduce gap */
    .stMarkdown p {
        font-size: 1.1rem !important;
        line-height: 1.4 !important;
    }

    /* Simple radio buttons - NO BOXES, NO SHADOWS, LEFT ALIGNED */
    .stRadio > div {
        gap: 0.2rem !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: flex-start !important;
    }
    .stRadio > div > label {
        background-color: transparent !important;
        padding: 4px 0px !important;
        padding-left: 0 !important;
        border-radius: 0 !important;
        border: none !important;
        margin-bottom: 0.15rem !important;
        cursor: pointer !important;
        display: flex !important;
        align-items: center !important;
        gap: 10px !important;
        box-shadow: none !important;
        -webkit-box-shadow: none !important;
        -moz-box-shadow: none !important;
        justify-content: flex-start !important;
        width: 100% !important;
    }
    .stRadio > div > label > div[data-testid="stMarkdownContainer"] {
        flex: 1 !important;
        text-align: left !important;
    }
    .stRadio > div > label > div[data-testid="stMarkdownContainer"] > p {
        color: #001f3f !important;
        font-size: 1.05rem !important;
        font-weight: 400 !important;
        margin: 0 !important;
        padding: 0 !important;
        text-align: left !important;
    }
    /* Selected radio button - make text bold and navy blue, NO SHADOWS */
    .stRadio > div > label:has(input[type="radio"]:checked) {
        background-color: transparent !important;
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
        -webkit-box-shadow: none !important;
        -moz-box-shadow: none !important;
    }
    .stRadio > div > label:has(input[type="radio"]:checked) p {
        color: #001f3f !important;
        font-weight: 400 !important;
    }
    /* Radio button circle - navy blue, NO SHADOWS */
    input[type="radio"] {
        accent-color: #001f3f !important;
        outline: none !important;
        width: 18px !important;
        height: 18px !important;
        cursor: pointer !important;
        flex-shrink: 0 !important;
        box-shadow: none !important;
        -webkit-box-shadow: none !important;
        -moz-box-shadow: none !important;
    }
    input[type="radio"]:checked {
        accent-color: #001f3f !important;
        outline: none !important;
        box-shadow: none !important;
        -webkit-box-shadow: none !important;
        -moz-box-shadow: none !important;
    }
    /* FORCE REMOVE ALL FOCUS OUTLINES, BOXES, AND SHADOWS - EVERYWHERE */
    .stRadio > div > label:focus,
    .stRadio > div > label:focus-within,
    .stRadio > div > label:active,
    input[type="radio"]:focus,
    input[type="radio"]:focus-visible,
    input[type="radio"]:active,
    *:focus,
    *:focus-visible {
        outline: none !important;
        outline-width: 0 !important;
        outline-style: none !important;
        outline-color: transparent !important;
        box-shadow: none !important;
        -webkit-box-shadow: none !important;
        -moz-box-shadow: none !important;
        border: none !important;
    }
    /* Hover state - subtle highlight, no box, NO SHADOWS */
    .stRadio > div > label:hover {
        background-color: rgba(0, 31, 63, 0.05) !important;
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
        -webkit-box-shadow: none !important;
        -moz-box-shadow: none !important;
        border-radius: 4px !important;
    }

    /* Text input focus - blue */
    .stTextInput > div > div > input:focus {
        border-color: #001f3f !important;
        box-shadow: 0 0 0 1px #001f3f !important;
    }

    /* All Buttons - Navy Blue - FORCE ALL BUTTONS */
    button, .stButton>button, .stDownloadButton>button, .stFormSubmitButton>button {
        background-color: #001f3f !important;
        color: white !important;
        border: none !important;
        border-color: #001f3f !important;
    }
    button:hover, .stButton>button:hover, .stDownloadButton>button:hover, .stFormSubmitButton>button:hover {
        background-color: #003d7a !important;
        border-color: #003d7a !important;
        color: white !important;
    }
    button[kind="primary"], button[kind="secondary"], button[kind="primaryFormSubmit"], button[kind="secondaryFormSubmit"] {
        background-color: #001f3f !important;
        color: white !important;
        border: none !important;
    }
    button[kind="primary"]:hover, button[kind="secondary"]:hover, button[kind="primaryFormSubmit"]:hover, button[kind="secondaryFormSubmit"]:hover {
        background-color: #003d7a !important;
        color: white !important;
    }
    /* Force all submit buttons */
    input[type="submit"], button[type="submit"] {
        background-color: #001f3f !important;
        color: white !important;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #001f3f;
        padding-top: 1rem;
    }
    /* Sidebar navigation buttons - Simple, no background highlighting */
    [data-testid="stSidebar"] .stButton>button {
        background-color: transparent !important;
        border: none !important;
        color: white !important;
        font-weight: 400 !important;
        text-align: left !important;
    }
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    /* CURRENT SECTION - Bold text with white border */
    section[data-testid="stSidebar"] button[data-testid="baseButton-primary"],
    section[data-testid="stSidebar"] button[data-testid="baseButton-primary"] *,
    [data-testid="stSidebar"] .stButton>button[kind="primary"],
    [data-testid="stSidebar"] .stButton>button[kind="primary"] *,
    [data-testid="stSidebar"] button[kind="primary"],
    [data-testid="stSidebar"] button[kind="primary"] * {
        background-color: transparent !important;
        color: white !important;
        font-weight: 700 !important;
    }
    [data-testid="stSidebar"] .stButton>button[kind="primary"],
    [data-testid="stSidebar"] button[kind="primary"] {
        border: 2px solid white !important;
        border-radius: 4px !important;
    }
    /* OTHER SECTIONS - Normal text, no border */
    [data-testid="stSidebar"] .stButton>button[kind="secondary"],
    [data-testid="stSidebar"] .stButton>button[kind="secondary"] * {
        background-color: transparent !important;
        color: white !important;
        font-weight: 400 !important;
        border: none !important;
    }
    /* Hover - subtle background */
    [data-testid="stSidebar"] .stButton>button:hover {
        background-color: rgba(255, 255, 255, 0.1) !important;
        border-radius: 4px !important;
    }

    /* Sidebar logo */
    .sidebar-logo {
        text-align: center;
        padding: 10px;
        margin-bottom: 20px;
        background-color: white;
        border-radius: 8px;
        margin: 0 10px 20px 10px;
    }
    .sidebar-logo img {
        width: 100%;
        max-width: 200px;
        height: auto;
    }

    /* Hide horizontal rules - just use spacing between questions */
    hr {
        margin-top: 2rem !important;
        margin-bottom: 0.5rem !important;
        border: none !important;
        visibility: hidden !important;
        height: 0 !important;
    }

    /* Remove borders from forms and questionnaire */
    [data-testid="stForm"] {
        border: none !important;
        padding: 0 !important;
    }
    .stForm {
        border: none !important;
    }
    form {
        border: none !important;
    }

    /* Hide Streamlit header and footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Large centered loading spinner - FORCE CENTER */
    div[data-testid="stSpinner"] {
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 100vw !important;
        height: 100vh !important;
        background-color: rgba(255, 255, 255, 0.95) !important;
        z-index: 9999 !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
    }

    div[data-testid="stSpinner"] > div {
        position: relative !important;
        top: auto !important;
        left: auto !important;
        transform: none !important;
    }

    /* Make spinner much larger */
    div[data-testid="stSpinner"] > div > div,
    div[data-testid="stSpinner"] svg,
    div[data-testid="stSpinner"] circle {
        width: 120px !important;
        height: 120px !important;
    }

    div[data-testid="stSpinner"] circle {
        stroke-width: 6 !important;
        stroke: #001f3f !important;
    }
</style>
""", unsafe_allow_html=True)

# Helper function to safely get secrets
def get_secret(key, default=None):
    """Safely get secret from environment or Streamlit secrets"""
    # Try environment variable first
    value = os.environ.get(key)
    if value:
        return value

    # Try Streamlit secrets
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError):
        return default

# Initialize Gemini LLM
try:
    gemini_key = get_secret("GEMINI_API_KEY")
    if not gemini_key:
        st.error("⚠️ GEMINI_API_KEY not found. Please configure it in Streamlit Cloud Secrets.")
        st.stop()

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0.0,
        google_api_key=gemini_key
    )
except Exception as e:
    st.error(f"⚠️ Error initializing Gemini: {str(e)}")
    st.stop()

# Google Sheets Configuration - Load from environment or secrets
SHEET_ID = get_secret("GOOGLE_SHEET_ID")
if not SHEET_ID:
    st.error("⚠️ GOOGLE_SHEET_ID not found. Please configure it in Streamlit Cloud Secrets.")
    st.stop()

# Load questions from Google Sheets - Cache for entire session
@st.cache_data(ttl=3600)
def load_questions_from_sheets():
    """Load questions from Google Sheets Raw tab - Cache for 1 hour for better performance"""
    try:
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']

        # Try to get credentials
        creds_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
        if creds_json:
            creds_dict = json.loads(creds_json)
        else:
            try:
                creds_dict = dict(st.secrets['google_sheets_creds'])
            except KeyError:
                st.error("⚠️ Google Sheets credentials not found. Please configure 'google_sheets_creds' in Streamlit Cloud Secrets.")
                st.info("📖 Check DEPLOYMENT_GUIDE.md for instructions on how to set up secrets.")
                st.stop()

        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID).worksheet('Raw')
        data = sheet.get_all_records()
        df = pd.DataFrame(data)

        if 'Segment' in df.columns:
            df['Segment'] = df['Segment'].replace('', pd.NA).ffill()
        if 'Weightage' in df.columns:
            df['Weightage'] = df['Weightage'].replace('', pd.NA).ffill()

        return df
    except Exception as e:
        st.error(f"⚠️ Error loading questions from Google Sheets: {str(e)}")
        st.info("💡 Make sure:\n- Google Sheets API is enabled\n- Service account has access to the sheet\n- Sheet ID is correct")
        # Return empty dataframe to prevent crash
        return pd.DataFrame()

# Load questions - cached for performance
df = load_questions_from_sheets()

# Check if questions loaded successfully
if df.empty:
    st.error("⚠️ No questions loaded from Google Sheets. Please check your configuration.")
    st.stop()

# [Include all the function definitions from the previous file here - calculate_score_for_answer, calculate_segment_scores, get_tag, generate_summary, generate_pdf, save_to_google_sheets_responses]

# Copy functions from previous file
def calculate_score_for_answer(answer, options_str):
    """Calculate score based on answer position"""
    answer = str(answer).strip()
    answer_lower = answer.lower()

    # Skip empty answers
    if not answer:
        return None

    # Check if this is a "1 to 5 Rating" question
    is_rating_question = "1 to 5 Rating" in str(options_str) if pd.notna(options_str) else False

    # For rating questions, handle specially
    if is_rating_question:
        try:
            rating_value = int(answer)
            # 1 = 0.0, 2 = 0.25, 3 = 0.5, 4 = 0.75, 5 = 1.0
            score = (rating_value - 1) / 4.0
            return score
        except ValueError:
            return None

    # Parse options for other question types
    if pd.notna(options_str):
        if '\n' in str(options_str):
            options = [opt.strip().lstrip('*').strip() for opt in str(options_str).split('\n') if opt.strip()]
        elif '/' in str(options_str):
            options_clean = str(options_str).strip('()').strip()
            options = [opt.strip() for opt in options_clean.split('/') if opt.strip()]
        else:
            options = [answer]
    else:
        options = [answer]

    # Check if this is a Yes/No question (binary)
    options_lower = [opt.lower() for opt in options]
    if 'yes' in options_lower and 'no' in options_lower and len(options) == 2:
        # Special handling for Yes/No questions
        if answer_lower == 'yes':
            return 1.0
        elif answer_lower == 'no':
            return 0.0
        else:
            return None

    # For other questions, use standard logic (first option = best)
    if not options:
        return None

    try:
        answer_index = options.index(answer)
    except ValueError:
        try:
            options_lower_list = [opt.lower() for opt in options]
            answer_index = options_lower_list.index(answer_lower)
        except ValueError:
            return None

    num_options = len(options)
    if num_options == 1:
        score = 1.0
    else:
        score = 1.0 - (answer_index / (num_options - 1))

    return score

def save_to_google_sheets_responses(user_data, all_responses, sheet_id, df, overall_score, segment_scores=None):
    """Save responses to Google Sheets - Responses tab and Calculations tab"""
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
        if creds_json:
            creds_dict = json.loads(creds_json)
        else:
            creds_dict = dict(st.secrets['google_sheets_creds'])

        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(sheet_id)

        # ===== RESPONSES TAB =====
        try:
            responses_sheet = spreadsheet.worksheet('Responses')
        except:
            responses_sheet = spreadsheet.add_worksheet(title='Responses', rows=1000, cols=100)

        row = [
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            user_data['name'],
            user_data['email'],
            user_data['phone'],
            user_data['organization']
        ]

        for key, value in all_responses.items():
            answer = value['answer']
            question_row = df[df['Question'] == value['question']]
            if not question_row.empty:
                options_str = question_row['Options'].iloc[0]
                score = calculate_score_for_answer(answer, options_str)
                if score is not None:
                    answer_with_score = f"{answer} ({score:.2f})"
                else:
                    answer_with_score = f"{answer} (N/A)"
            else:
                answer_with_score = answer
            row.append(answer_with_score)

        # Add overall score (0-100 scale) - NO segment scores in Responses tab
        overall_score_100 = round(overall_score * 100)
        row.append(f"{overall_score_100}")

        if responses_sheet.row_count == 0 or not responses_sheet.row_values(1):
            header = ['Timestamp', 'Name', 'Email', 'Phone', 'Organization']
            for key, value in all_responses.items():
                header.append(value['question'])
            header.append('Overall Score (0-100)')
            responses_sheet.append_row(header)

        responses_sheet.append_row(row)

        # ===== CALCULATIONS TAB =====
        if segment_scores:
            try:
                calc_sheet = spreadsheet.worksheet('Calculations')
            except:
                calc_sheet = spreadsheet.add_worksheet(title='Calculations', rows=1000, cols=20)

            # Build detailed calculation rows
            calc_rows = []

            # Header row
            calc_rows.append([
                'Timestamp',
                'Name',
                'Organization',
                'Segment',
                'Total Questions in Segment',
                'Total Score (Sum)',
                'Average Score (0-1)',
                'Segment Weightage',
                'Weighted Score',
                'Segment Score (0-100)',
                'Overall Score (0-100)'
            ])

            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # One row per segment with calculations
            for segment_name in sorted(segment_scores.keys()):
                seg_data = segment_scores[segment_name]
                calc_rows.append([
                    timestamp,
                    user_data['name'],
                    user_data['organization'],
                    segment_name,
                    seg_data['total_questions'],
                    f"{seg_data['score'] * seg_data['total_questions']:.2f}",  # Total score sum
                    f"{seg_data['score']:.4f}",  # Average score (0-1)
                    f"{seg_data['weightage']:.2%}",  # Weightage as percentage
                    f"{seg_data['weighted_score']:.4f}",  # Weighted score
                    f"{round(seg_data['score'] * 100)}",  # Segment score 0-100
                    ""  # Overall score only on first row
                ])

            # Add overall score to the first segment row
            if calc_rows and len(calc_rows) > 1:
                calc_rows[1][10] = f"{overall_score_100}"

            # Write to Calculations sheet
            if calc_sheet.row_count == 0 or not calc_sheet.row_values(1):
                calc_sheet.append_row(calc_rows[0])  # Header
                for row in calc_rows[1:]:
                    calc_sheet.append_row(row)
            else:
                for row in calc_rows[1:]:
                    calc_sheet.append_row(row)

        return True
    except Exception as e:
        # Log error for debugging but return False silently
        print(f"Error saving to Google Sheets: {e}")
        return False

def calculate_segment_scores(all_responses, df):
    """Calculate weighted scores"""
    segments_list = df['Segment'].unique().tolist()
    segment_scores = {}

    for segment in segments_list:
        segment_responses = {k: v for k, v in all_responses.items() if v['segment'] == segment}
        if not segment_responses:
            continue

        weightage_str = str(df[df['Segment'] == segment]['Weightage'].iloc[0])
        if '%' in weightage_str:
            segment_weightage = float(weightage_str.strip('%')) / 100
        else:
            segment_weightage = float(weightage_str)

        total_score = 0
        question_count = 0

        for resp_data in segment_responses.values():
            answer = resp_data['answer']
            question_row = df[df['Question'] == resp_data['question']]
            if not question_row.empty:
                options = question_row['Options'].iloc[0]
                score = calculate_score_for_answer(answer, options)
                if score is not None:
                    total_score += score
                    question_count += 1

        avg_score = total_score / question_count if question_count > 0 else 0
        segment_scores[segment] = {
            'score': avg_score,
            'weightage': segment_weightage,
            'weighted_score': avg_score * segment_weightage,
            'total_questions': question_count
        }

    return segment_scores

def get_tag(score):
    """Get maturity tag based on score (0-1 scale)"""
    if score < 0.25:
        return "Novice"
    elif score < 0.5:
        return "Explorer"
    elif score < 0.75:
        return "PaceSetter"
    else:
        return "Trailblazer"

def generate_summary(segment_scores, overall_score, overall_tag):
    prompt = f"""
You are an AI maturity assessment expert. Generate a professional assessment report.

STRICT FORMATTING RULES:
- DO NOT include conversational phrases like "Okay, here's", "Here is", "Let me", etc.
- DO NOT use bold (**text**), italics, or any markdown formatting
- DO NOT use asterisks (*) anywhere - use hyphens (-) for bullets only
- Keep consistent plain text formatting throughout
- Start directly with section 1

Generate exactly 4 sections with this structure:

1. Executive Summary:
[Write 3 sentences in a single paragraph about the organization's AI maturity]

2. Key Strengths:
- [Strength 1]
- [Strength 2]
- [Strength 3]
- [Strength 4]

3. Improvement Opportunities:
- [Improvement 1]
- [Improvement 2]
{"- [Improvement 3]" if overall_score <= 0.8 else ""}

4. Recommended Next Steps:
- [Step 1]
- [Step 2]
{"- [Step 3]" if overall_score <= 0.8 else ""}

Assessment Data:
Overall Score: {round(overall_score * 100)}/100 ({overall_tag})

Segment Performance:
{chr(10).join([f"- {seg}: {round(data['score'] * 100)}/100 ({get_tag(data['score'])})" for seg, data in sorted(segment_scores.items())])}

Keep tone professional and direct. No conversational language. Use consistent plain text only.
    """
    try:
        return llm.invoke(prompt)
    except Exception as e:
        return f"Error generating summary: {e}"

def generate_pdf(summary, segment_scores, overall_score, overall_tag, user_data, all_responses, df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Helper function to clean text for PDF (remove unicode characters)
    def clean_text(text):
        """Replace unicode characters that can't be encoded in latin-1"""
        text = str(text)
        # Replace common unicode quotes and apostrophes
        text = text.replace('\u2019', "'")  # Right single quotation mark
        text = text.replace('\u2018', "'")  # Left single quotation mark
        text = text.replace('\u201c', '"')  # Left double quotation mark
        text = text.replace('\u201d', '"')  # Right double quotation mark
        text = text.replace('\u2013', '-')  # En dash
        text = text.replace('\u2014', '-')  # Em dash
        text = text.replace('\u2026', '...')  # Ellipsis
        # Remove any remaining non-latin1 characters
        text = text.encode('latin-1', 'ignore').decode('latin-1')
        return text

    # Navy blue color (RGB: 0, 31, 63)
    navy_blue = (0, 31, 63)
    light_gray = (240, 240, 240)

    # HEADER - Title with background
    pdf.set_fill_color(navy_blue[0], navy_blue[1], navy_blue[2])
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 20)
    pdf.cell(0, 15, "AI Maturity Assessment Report", ln=True, align="C", fill=True)
    pdf.ln(8)

    # User Info Section - Light gray box
    pdf.set_fill_color(light_gray[0], light_gray[1], light_gray[2])
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "Assessment Details", ln=True, fill=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 6, clean_text(f"Name: {user_data['name']}"), ln=True)
    pdf.cell(0, 6, clean_text(f"Organization: {user_data['organization']}"), ln=True)
    pdf.cell(0, 6, f"Date: {datetime.now().strftime('%B %d, %Y')}", ln=True)
    pdf.ln(10)

    # Overall Score - Prominent display with scaled score (0-100)
    overall_score_100 = round(overall_score * 100)
    pdf.set_fill_color(navy_blue[0], navy_blue[1], navy_blue[2])
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 12, f"Overall Score: {overall_score_100}/100 - {overall_tag}", ln=True, align="C", fill=True)
    pdf.ln(10)

    # Segment Scores Section
    pdf.set_text_color(navy_blue[0], navy_blue[1], navy_blue[2])
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Segment Performance", ln=True)
    pdf.ln(2)

    # Segment scores in a table format
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(light_gray[0], light_gray[1], light_gray[2])
    pdf.cell(100, 7, "Segment", border=1, fill=True)
    pdf.cell(45, 7, "Score", border=1, align="C", fill=True)
    pdf.cell(45, 7, "Level", border=1, align="C", fill=True, ln=True)

    pdf.set_font("Arial", "", 10)
    for segment, data in segment_scores.items():
        segment_score_100 = round(data['score'] * 100)
        pdf.cell(100, 7, clean_text(segment), border=1)
        pdf.cell(45, 7, f"{segment_score_100}/100", border=1, align="C")
        pdf.cell(45, 7, clean_text(get_tag(data['score'])), border=1, align="C", ln=True)
    pdf.ln(10)

    # Executive Summary Section
    pdf.set_text_color(navy_blue[0], navy_blue[1], navy_blue[2])
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Executive Summary", ln=True)
    pdf.ln(2)

    # Parse and beautify summary content
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "", 10)

    lines = summary.split('\n')
    in_list = False

    for line in lines:
        line = line.strip()
        if not line:
            pdf.ln(3)
            in_list = False
            continue

        # Remove ALL asterisks from the line
        line_clean = line.replace('**', '').replace('*', '').strip()
        # Clean unicode characters
        line_clean = clean_text(line_clean)

        # Check for numbered headings (1., 2., 3., etc.)
        if line_clean and line_clean[0].isdigit() and '. ' in line_clean[:5]:
            # This is a main heading
            pdf.ln(5)
            pdf.set_text_color(navy_blue[0], navy_blue[1], navy_blue[2])
            pdf.set_font("Arial", "B", 12)
            pdf.multi_cell(0, 6, line_clean)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", "", 10)
            pdf.ln(2)
            in_list = False
        # Check for bullet points (starting with -)
        elif line_clean.startswith('-'):
            bullet_text = line_clean[1:].strip()
            pdf.set_font("Arial", "", 10)
            # Indent bullet points - use simple dash instead of Unicode bullet
            pdf.cell(10)
            pdf.multi_cell(0, 5, f"- {bullet_text}")
            in_list = True
        else:
            # Regular paragraph text
            if in_list:
                pdf.ln(2)
                in_list = False
            pdf.set_font("Arial", "", 10)
            pdf.multi_cell(0, 5, line_clean)

    # Add new page for user responses
    pdf.add_page()

    # Your Responses Section
    pdf.set_text_color(navy_blue[0], navy_blue[1], navy_blue[2])
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Your Responses", ln=True)
    pdf.ln(5)

    # Group responses by segment
    for segment in df['Segment'].unique().tolist():
        # Segment header
        pdf.set_fill_color(light_gray[0], light_gray[1], light_gray[2])
        pdf.set_text_color(navy_blue[0], navy_blue[1], navy_blue[2])
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, clean_text(segment), ln=True, fill=True)
        pdf.ln(3)

        # Get responses for this segment
        segment_responses = {k: v for k, v in all_responses.items() if v['segment'] == segment}

        pdf.set_text_color(0, 0, 0)
        for key, resp_data in segment_responses.items():
            question = clean_text(resp_data['question'])
            answer = clean_text(resp_data['answer'])

            # Question in smaller font
            pdf.set_font("Arial", "B", 8)
            pdf.multi_cell(0, 4, f"Q: {question}")

            # Answer in even smaller font, indented
            pdf.set_font("Arial", "", 7)
            pdf.cell(10)  # Indent
            pdf.multi_cell(0, 4, f"A: {answer}")
            pdf.ln(2)

        pdf.ln(3)

    # Footer
    pdf.ln(10)
    pdf.set_text_color(128, 128, 128)
    pdf.set_font("Arial", "I", 8)
    pdf.cell(0, 5, "This report was generated by the AI Maturity Assessment Tool", ln=True, align="C")

    file_path = "AI_Maturity_Report.pdf"
    pdf.output(file_path)
    return file_path

# -----------------------------
# STREAMLIT UI
# -----------------------------
st.title("AI Maturity & Readiness Assessment Tool")

# Initialize session state
if 'user_info_submitted' not in st.session_state:
    st.session_state.user_info_submitted = False
if 'user_data' not in st.session_state:
    st.session_state.user_data = {}
if 'current_section' not in st.session_state:
    st.session_state.current_section = 0
if 'all_responses' not in st.session_state:
    st.session_state.all_responses = {}
if 'assessment_completed' not in st.session_state:
    st.session_state.assessment_completed = False
if 'report_generated' not in st.session_state:
    st.session_state.report_generated = False
if 'segment_scores' not in st.session_state:
    st.session_state.segment_scores = None
if 'overall_score' not in st.session_state:
    st.session_state.overall_score = None
if 'overall_tag' not in st.session_state:
    st.session_state.overall_tag = None
if 'summary' not in st.session_state:
    st.session_state.summary = None
if 'validation_error' not in st.session_state:
    st.session_state.validation_error = None
if 'generating_report' not in st.session_state:
    st.session_state.generating_report = False

# Step 1: User Information
if not st.session_state.user_info_submitted:

    with st.form("user_info_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            user_name = st.text_input("Full Name *", placeholder="Enter your full name", key="user_name_input")
            user_email = st.text_input("Email *", placeholder="Enter your email", key="user_email_input")
        with col2:
            user_org = st.text_input("Organization *", placeholder="Enter your organization", key="user_org_input")
            user_phone = st.text_input("Phone Number (Optional)", placeholder="Enter your phone number", key="user_phone_input")

        # Hardcoded spacing before the button - fixed gap
        st.markdown("<div style='margin-top: 80px;'></div>", unsafe_allow_html=True)

        submit_info = st.form_submit_button("Continue to Assessment", type="primary", use_container_width=True)

        if submit_info:
            if not user_name or not user_email or not user_org:
                st.error("Please provide Full Name, Email, and Organization to continue.")
            else:
                with st.spinner(''):
                    st.session_state.user_info_submitted = True
                    st.session_state.user_data = {
                        'name': user_name,
                        'email': user_email,
                        'phone': user_phone if user_phone else "N/A",
                        'organization': user_org
                    }
                    st.session_state.current_section = 0  # Reset to first section
                    st.rerun()

# Step 2: Questionnaire with Sidebar Navigation
elif st.session_state.user_info_submitted and not st.session_state.assessment_completed:
    # Get segments
    segments_list = df['Segment'].unique().tolist()

    # Sidebar with logo and navigation
    with st.sidebar:
        # Databeat Logo - with white background container (80% size)
        st.markdown("""
        <div style="background-color: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; margin-left: auto; margin-right: auto; width: 80%;">
            <img src="https://databeat.io/wp-content/uploads/2025/05/DataBeat-Mediamint-Logo-1-1.png"
                 style="width: 100%; height: auto; display: block;">
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### Navigate Sections")
        for idx, segment in enumerate(segments_list):
            # Determine button type based on current section
            is_current = (idx == st.session_state.current_section)
            button_type = "primary" if is_current else "secondary"

            if st.button(segment, key=f"nav_{idx}", use_container_width=True, type=button_type):
                # When clicking on a new section, reset to that section's first question
                st.session_state.current_section = idx
                st.rerun()

        # Add Submit Assessment button in sidebar
        st.markdown("---")
        if st.button("📊 Submit Assessment & Generate Report", key="sidebar_submit_btn", use_container_width=True, type="primary"):
            # Validate all questions are answered before submitting
            segments_list_all = df['Segment'].unique().tolist()
            unanswered_sections = []

            for seg_idx, seg_name in enumerate(segments_list_all):
                seg_df = df[df['Segment'] == seg_name].reset_index(drop=True)
                for q_idx, q_row in seg_df.iterrows():
                    q_key = f"{seg_name}_{q_idx}"
                    answer = st.session_state.all_responses.get(q_key, {}).get('answer', '')
                    if not answer or answer.strip() == '':
                        if seg_name not in unanswered_sections:
                            unanswered_sections.append(seg_name)
                        break

            if unanswered_sections:
                # Store error in session state to display near button
                st.session_state.validation_error = unanswered_sections
                st.rerun()
            else:
                # Clear any previous errors
                st.session_state.validation_error = None
                st.session_state.generating_report = True
                st.session_state.assessment_completed = True
                st.rerun()

        # Display validation error below sidebar button if exists
        if st.session_state.validation_error:
            error_message = "⚠️ **Please answer all questions before submitting.**\n\nUnanswered sections:"
            for section in st.session_state.validation_error:
                error_message += f"\n- {section}"
            st.error(error_message)
        elif st.session_state.generating_report and st.session_state.assessment_completed and not st.session_state.report_generated:
            st.info("🔄 Generating report... Please wait")

    # Display current section
    current_idx = st.session_state.current_section
    segment = segments_list[current_idx]

    # Scroll to top - using multiple methods for better compatibility
    st.markdown(f'<div id="section-top-{current_idx}"></div>', unsafe_allow_html=True)
    st.markdown("""
    <script>
        // Multiple scroll methods for better browser compatibility
        setTimeout(function() {
            // Method 1: Scroll parent window
            window.parent.scrollTo(0, 0);

            // Method 2: Scroll main section
            var mainSection = window.parent.document.querySelector('section.main');
            if (mainSection) {
                mainSection.scrollTop = 0;
            }

            // Method 3: Scroll body
            window.parent.document.body.scrollTop = 0;
            window.parent.document.documentElement.scrollTop = 0;

            // Method 4: Scroll to element
            var appView = window.parent.document.querySelector('.main .block-container');
            if (appView) {
                appView.scrollIntoView({ behavior: 'instant', block: 'start' });
            }
        }, 10);
    </script>
    """, unsafe_allow_html=True)

    st.header(f"Section {current_idx + 1}/{len(segments_list)}: {segment}")

    segment_df = df[df['Segment'] == segment].reset_index(drop=True)

    # Main content area - display questions without form for immediate state saving
    # Display questions for current section
    for i, row in segment_df.iterrows():
        question = row['Question']
        options_str = row['Options']

        # Parse options
        if pd.notna(options_str):
            if '\n' in str(options_str):
                options = [opt.strip().lstrip('*').strip() for opt in str(options_str).split('\n') if opt.strip()]
            elif '/' in str(options_str):
                options_clean = str(options_str).strip('()').strip()
                options = [opt.strip() for opt in options_clean.split('/') if opt.strip()]
            else:
                options = ["Yes", "No", "Not Sure"]
        else:
            options = ["Yes", "No", "Not Sure"]

        question_key = f"{segment}_{i}"
        st.markdown(f"**{question}**")

        # Get existing response if any
        default_answer = st.session_state.all_responses.get(question_key, {}).get('answer', '')
        default_index = None

        # Check if this is a "1 to 5 Rating" question
        if "1 to 5 Rating" in str(options_str) or options == ['1', '2', '3', '4', '5']:
            # Display horizontally for rating questions ONLY with Lowest/Highest labels
            display_options = ["1 (Lowest)", '2', '3', '4', "5 (Highest)"]

            # Map stored answer to display option for rating questions
            if default_answer:
                rating_map = {'1': 0, '2': 1, '3': 2, '4': 3, '5': 4}
                default_index = rating_map.get(default_answer, None)

            response = st.radio(
                "Select your answer:",
                display_options,
                key=f"radio_{question_key}",
                index=default_index,
                label_visibility="collapsed",
                horizontal=True
            )
            # Extract just the number from the response for storage
            if response:
                response = response.split()[0]  # Gets '1', '2', '3', '4', or '5'
        else:
            # Display vertically for ALL other questions
            # Set default index for non-rating questions
            if default_answer and default_answer in options:
                default_index = options.index(default_answer)

            response = st.radio(
                "Select your answer:",
                options,
                key=f"radio_{question_key}",
                index=default_index,
                label_visibility="collapsed",
                horizontal=False
            )

        # Store response in session state - always store to maintain state
        st.session_state.all_responses[question_key] = {
            'segment': segment,
            'sub_segment': row['Sub Segment'] if 'Sub Segment' in row else '',
            'question': question,
            'answer': response if response else '',
            'weightage': row['Weightage']
        }

        # Clear validation error when user answers a question
        if response and st.session_state.validation_error:
            st.session_state.validation_error = None

        # Increased gap between questions - larger spacing
        st.markdown("<div style='margin-bottom: 40px;'></div>", unsafe_allow_html=True)

    # Navigation buttons - outside of form for immediate updates
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if current_idx > 0:
            if st.button("← Previous Section", use_container_width=True, key="prev_section_btn"):
                st.session_state.current_section = current_idx - 1
                st.rerun()
        else:
            st.write("")
    with col3:
        if current_idx < len(segments_list) - 1:
            if st.button("Next Section →", use_container_width=True, key="next_section_btn"):
                st.session_state.current_section = current_idx + 1
                st.rerun()
        else:
            if st.button("Submit Assessment & Generate Report", type="primary", use_container_width=True, key="submit_assessment_btn"):
                # Validate all questions are answered before submitting
                segments_list_all = df['Segment'].unique().tolist()
                unanswered_sections = []

                for seg_idx, seg_name in enumerate(segments_list_all):
                    seg_df = df[df['Segment'] == seg_name].reset_index(drop=True)
                    for q_idx, q_row in seg_df.iterrows():
                        q_key = f"{seg_name}_{q_idx}"
                        answer = st.session_state.all_responses.get(q_key, {}).get('answer', '')
                        if not answer or answer.strip() == '':
                            if seg_name not in unanswered_sections:
                                unanswered_sections.append(seg_name)
                            break

                if unanswered_sections:
                    # Store error in session state to display near button
                    st.session_state.validation_error = unanswered_sections
                    st.rerun()
                else:
                    # Clear any previous errors
                    st.session_state.validation_error = None
                    st.session_state.generating_report = True
                    st.session_state.assessment_completed = True
                    st.rerun()

    # Display validation error or loading status below the submit button
    if st.session_state.validation_error:
        error_message = "⚠️ **Please answer all questions before submitting.**\n\nUnanswered sections:"
        for section in st.session_state.validation_error:
            error_message += f"\n- {section}"
        st.error(error_message)
    elif st.session_state.assessment_completed and not st.session_state.report_generated:
        # Show loading animation near the button
        with st.spinner("Generating the report..."):
            pass  # The actual processing happens in Step 2.5

# Step 2.5: Report Generation (happens after assessment_completed but before showing results)
elif st.session_state.assessment_completed and not st.session_state.report_generated:
    # Show loading status
    with st.spinner("Generating the report..."):
        segment_scores = calculate_segment_scores(st.session_state.all_responses, df)
        total_weighted_score = sum(data['weighted_score'] for data in segment_scores.values())
        total_weight = sum(data['weightage'] for data in segment_scores.values())
        overall_score = total_weighted_score / total_weight if total_weight > 0 else 0
        overall_tag = get_tag(overall_score)

        if GOOGLE_SHEETS_AVAILABLE:
            save_to_google_sheets_responses(st.session_state.user_data, st.session_state.all_responses, SHEET_ID, df, overall_score, segment_scores)

        summary = generate_summary(segment_scores, overall_score, overall_tag)

        # Store in session state
        st.session_state.segment_scores = segment_scores
        st.session_state.overall_score = overall_score
        st.session_state.overall_tag = overall_tag
        st.session_state.summary = summary
        st.session_state.report_generated = True
        st.session_state.generating_report = False

    # Rerun to show results
    st.rerun()

# Step 3: Display results
elif st.session_state.assessment_completed and st.session_state.report_generated:
    all_responses = st.session_state.all_responses

    # Use stored results
    if st.session_state.report_generated:
        segment_scores = st.session_state.segment_scores
        overall_score = st.session_state.overall_score
        overall_tag = st.session_state.overall_tag
        summary = st.session_state.summary

        # Display overall score and tag (scaled 0-100) - show as integer
        overall_score_100 = round(overall_score * 100)
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Overall AI Maturity Score", f"{overall_score_100}/100")
        with col2:
            st.metric("Maturity Level", overall_tag)

        st.subheader("Segment Scores")

        # Create DataFrame with scaled scores (0-100)
        viz_df = pd.DataFrame([
            {
                'Segment': seg,
                'Score (0-100)': data['score'] * 100,
                'Score': data['score'],  # Keep 0-1 score for radar chart
                'Tag': get_tag(data['score']),
                'Weightage': data['weightage']
            }
            for seg, data in segment_scores.items()
        ])

        # Display segment scores with tags in a nice format - show as integers
        st.markdown("### Individual Segment Performance")
        for seg, data in segment_scores.items():
            score_100 = round(data['score'] * 100)
            tag = get_tag(data['score'])
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"**{seg}**")
            with col2:
                st.markdown(f"**{score_100}/100**")
            with col3:
                st.markdown(f"**{tag}**")

        st.markdown("---")

        # Create Radar Chart
        st.subheader("AI Maturity Radar Chart")
        radar_fig = px.line_polar(
            viz_df,
            r='Score (0-100)',
            theta='Segment',
            line_close=True,
            range_r=[0, 100],
            title="AI Maturity Assessment - Segment Analysis"
        )
        radar_fig.update_traces(
            fill='toself',
            fillcolor='rgba(0, 31, 63, 0.3)',
            line=dict(color='#001f3f', width=3)
        )
        radar_fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100],
                    showticklabels=True,
                    ticks='outside',
                    tickfont=dict(size=12)
                ),
                angularaxis=dict(
                    tickfont=dict(size=12)
                )
            ),
            showlegend=False,
            height=600
        )
        st.plotly_chart(radar_fig, use_container_width=True)

        # Bar Chart with scaled scores
        st.subheader("Segment Comparison")
        bar_fig = px.bar(
            viz_df,
            x="Segment",
            y="Score (0-100)",
            color="Tag",
            range_y=[0, 100],
            color_discrete_map={
                "Novice": "#ff4b4b",
                "Explorer": "#ffa600",
                "PaceSetter": "#00cc96",
                "Trailblazer": "#636efa"
            },
            title="AI Maturity Scores by Segment (0-100 Scale)",
            text="Score (0-100)"
        )
        bar_fig.update_traces(texttemplate='%{text:.0f}', textposition='outside')
        st.plotly_chart(bar_fig, use_container_width=True)

        st.subheader("Executive Summary")
        st.markdown(summary)

        # Display user responses
        st.markdown("---")
        st.subheader("Your Responses")

        # Group responses by segment
        for segment in df['Segment'].unique().tolist():
            with st.expander(f"📋 {segment}", expanded=False):
                segment_responses = {k: v for k, v in all_responses.items() if v['segment'] == segment}

                for key, resp_data in segment_responses.items():
                    question = resp_data['question']
                    answer = resp_data['answer']

                    # Display question and answer with small font
                    st.markdown(f"""
                    <div style="margin-bottom: 15px;">
                        <p style="font-size: 0.85rem; margin-bottom: 3px; color: #333;"><strong>Q:</strong> {question}</p>
                        <p style="font-size: 0.75rem; color: #666; margin-left: 15px;"><strong>A:</strong> {answer}</p>
                    </div>
                    """, unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("Download Report")
        # Generate PDF with spinner animation
        with st.spinner('Generating PDF...'):
            file_path = generate_pdf(summary, segment_scores, overall_score, overall_tag, st.session_state.user_data, all_responses, df)

        with open(file_path, "rb") as f:
            st.download_button(
                "Download Full PDF Report",
                f,
                file_name=f"AI_Maturity_Report_{st.session_state.user_data['name'].replace(' ', '_')}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )
