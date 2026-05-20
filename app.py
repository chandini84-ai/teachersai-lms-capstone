import streamlit as st
import pandas as pd
import os
from datetime import date
from io import BytesIO

st.set_page_config(page_title="TeachersAI LMS", layout="wide")

STUDENT_FILE = "students.csv"
ASSESSMENT_FILE = "assessments.csv"
ANECDOTAL_FILE = "anecdotal_records.csv"
USER_FILE = "users.csv"

CLASSES = [
    "Pre-K Prep", "Pre-K Juniors", "Pre-K Seniors", "K1",
    "Junior Primary", "Class of 2027", "Class of 2028"
]

SUBJECTS = [
    "Mathematics", "E.L.A.", "Science", "Social Studies", "Spanish",
    "Phonics/Reading", "Comprehension", "Creative Writing",
    "Vocabulary", "Spelling"
]

TERMS = ["Term I", "Term II", "Term III"]


# ---------- EXCEL EXPORT ----------
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Data")
    return output.getvalue()


# ---------- CREATE FILES ----------
if not os.path.exists(USER_FILE):
    default_admin = pd.DataFrame(
        [["Administrator", "admin", "admin123", "Admin"]],
        columns=["Full Name", "Username", "Password", "Role"]
    )
    default_admin.to_csv(USER_FILE, index=False)

if not os.path.exists(STUDENT_FILE):
    pd.DataFrame(columns=["Student Name", "Class", "Teacher Name"]).to_csv(STUDENT_FILE, index=False)

if not os.path.exists(ASSESSMENT_FILE):
    pd.DataFrame(columns=[
        "Student Name", "Teacher Name", "Academic Term", "Week", "Date",
        "Subject", "Assessment Topic", "Score Earned", "Total Marks", "Percentage"
    ]).to_csv(ASSESSMENT_FILE, index=False)

if not os.path.exists(ANECDOTAL_FILE):
    pd.DataFrame(columns=[
        "Student Name", "Teacher Name", "Academic Term", "Week", "Date",
        "Observation Topic", "Anecdotal Notes", "General Comments"
    ]).to_csv(ANECDOTAL_FILE, index=False)


# ---------- SESSION ----------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "role" not in st.session_state:
    st.session_state.role = ""
if "full_name" not in st.session_state:
    st.session_state.full_name = ""


# ---------- WHISPER ----------
@st.cache_resource
def load_whisper_model():
    import whisper
    return whisper.load_model("base")


# ---------- LOAD FUNCTIONS ----------
def load_users():
    return pd.read_csv(USER_FILE)

def load_students():
    return pd.read_csv(STUDENT_FILE)

def load_assessments():
    df = pd.read_csv(ASSESSMENT_FILE)
    if "Teacher Name" not in df.columns:
        df["Teacher Name"] = ""
    return df

def load_anecdotal():
    df = pd.read_csv(ANECDOTAL_FILE)
    if "Teacher Name" not in df.columns:
        df["Teacher Name"] = ""
    return df


# ---------- SAVE FUNCTIONS ----------
def create_teacher_account(full_name, username, password):
    users = load_users()
    new_user = pd.DataFrame(
        [[full_name, username, password, "Teacher"]],
        columns=["Full Name", "Username", "Password", "Role"]
    )
    users = pd.concat([users, new_user], ignore_index=True)
    users.to_csv(USER_FILE, index=False)

def save_student(name, class_name, teacher):
    students = load_students()
    new_student = pd.DataFrame(
        [[name, class_name, teacher]],
        columns=["Student Name", "Class", "Teacher Name"]
    )
    students = pd.concat([students, new_student], ignore_index=True)
    students.to_csv(STUDENT_FILE, index=False)

def save_assessment(student, teacher, term, week, assessment_date, subject, topic, score, total_marks):
    assessments = load_assessments()
    percentage = round((score / total_marks) * 100, 1)

    new_assessment = pd.DataFrame(
        [[student, teacher, term, week, assessment_date, subject, topic, score, total_marks, percentage]],
        columns=[
            "Student Name", "Teacher Name", "Academic Term", "Week", "Date",
            "Subject", "Assessment Topic", "Score Earned", "Total Marks", "Percentage"
        ]
    )

    assessments = pd.concat([assessments, new_assessment], ignore_index=True)
    assessments.to_csv(ASSESSMENT_FILE, index=False)

def save_anecdotal(student, teacher, term, week, record_date, topic, notes, comments):
    records = load_anecdotal()

    new_record = pd.DataFrame(
        [[student, teacher, term, week, record_date, topic, notes, comments]],
        columns=[
            "Student Name", "Teacher Name", "Academic Term", "Week", "Date",
            "Observation Topic", "Anecdotal Notes", "General Comments"
        ]
    )

    records = pd.concat([records, new_record], ignore_index=True)
    records.to_csv(ANECDOTAL_FILE, index=False)


# ---------- HELPERS ----------
def get_visible_students():
    students = load_students()
    if st.session_state.role == "Teacher":
        students = students[students["Teacher Name"] == st.session_state.username]
    return students

def get_visible_assessments():
    assessments = load_assessments()
    if st.session_state.role == "Teacher":
        assessments = assessments[assessments["Teacher Name"] == st.session_state.username]
    return assessments

def get_visible_anecdotal():
    records = load_anecdotal()
    if st.session_state.role == "Teacher":
        records = records[records["Teacher Name"] == st.session_state.username]
    return records

def filter_dataframe(df, search_text="", class_filter="All", term_filter="All", subject_filter="All"):
    filtered = df.copy()

    if search_text:
        search_text = search_text.lower()
        filtered = filtered[
            filtered.astype(str).apply(
                lambda row: row.str.lower().str.contains(search_text).any(),
                axis=1
            )
        ]

    if class_filter != "All" and "Class" in filtered.columns:
        filtered = filtered[filtered["Class"] == class_filter]

    if term_filter != "All" and "Academic Term" in filtered.columns:
        filtered = filtered[filtered["Academic Term"] == term_filter]

    if subject_filter != "All" and "Subject" in filtered.columns:
        filtered = filtered[filtered["Subject"] == subject_filter]

    return filtered

def generate_ai_comment(student, average_score, strongest_subject, weakest_subject, notes_text):
    if average_score >= 85:
        opening = f"{student} is demonstrating excellent academic progress and shows strong understanding across assessed areas."
        status = "The student works confidently and consistently produces work of a high standard."
    elif average_score >= 70:
        opening = f"{student} is making satisfactory academic progress and continues to develop important skills."
        status = "The student shows a good level of understanding but should continue practising to strengthen accuracy and confidence."
    elif average_score >= 50:
        opening = f"{student} is showing some academic progress but requires continued monitoring and support."
        status = "The student would benefit from guided practice, revision, and targeted reinforcement in weaker areas."
    else:
        opening = f"{student} is currently experiencing academic difficulty and requires immediate intervention."
        status = "The student needs consistent teacher support, simplified practice tasks, and close monitoring to rebuild foundational skills."

    comment = (
        f"{opening} {status} "
        f"Based on the assessment records, {student}'s strongest area appears to be {strongest_subject}, "
        f"while additional support is needed in {weakest_subject}. "
    )

    if notes_text.strip():
        comment += f"Classroom observations also indicate the following: {notes_text}. "

    comment += (
        f"Moving forward, {student} should be encouraged through regular feedback, short practice activities, "
        f"teacher-guided correction, and opportunities to review key concepts before new work is introduced."
    )

    return comment


# ---------- LOGIN ----------
if not st.session_state.logged_in:
    st.title("TeachersAI LMS")
    st.caption("Teacher Login • Account Creation • Student Tracking")

    choice = st.radio("Choose an option", ["Login", "Create Teacher Account"], horizontal=True)

    if choice == "Login":
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            users = load_users()
            user_match = users[
                (users["Username"] == username) &
                (users["Password"] == password)
            ]

            if not user_match.empty:
                st.session_state.logged_in = True
                st.session_state.username = user_match.iloc[0]["Username"]
                st.session_state.role = user_match.iloc[0]["Role"]
                st.session_state.full_name = user_match.iloc[0]["Full Name"]
                st.rerun()
            else:
                st.error("Invalid username or password.")

        st.info("Default Admin Login: admin / admin123")

    else:
        st.subheader("Create Teacher Account")
        full_name = st.text_input("Full Name")
        new_username = st.text_input("Create Username")
        new_password = st.text_input("Create Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")

        if st.button("Create Account"):
            users = load_users()

            if full_name.strip() == "":
                st.error("Please enter your full name.")
            elif new_username.strip() == "":
                st.error("Please enter a username.")
            elif new_password.strip() == "":
                st.error("Please enter a password.")
            elif new_password != confirm_password:
                st.error("Passwords do not match.")
            elif new_username in users["Username"].astype(str).tolist():
                st.error("This username already exists.")
            else:
                create_teacher_account(full_name, new_username, new_password)
                st.success("Teacher account created successfully. You can now log in.")

    st.stop()


# ---------- MAIN APP ----------
st.title("TeachersAI LMS")
st.caption("Student Assessment • Anecdotal Records • Reports • Academic Alerts")

with st.sidebar:
    st.write(f"Logged in as: {st.session_state.full_name}")
    st.write(f"Username: {st.session_state.username}")
    st.write(f"Role: {st.session_state.role}")

    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.role = ""
        st.session_state.full_name = ""
        st.rerun()

    menu = st.selectbox(
        "Navigation",
        [
            "Dashboard",
            "Student Profiles",
            "Assessment Records",
            "Anecdotal Records",
            "Academic Alerts",
            "Reports",
            "User Accounts"
        ]
    )

students_df = get_visible_students()
assessments_df = get_visible_assessments()
anecdotal_df = get_visible_anecdotal()
student_list = students_df["Student Name"].dropna().tolist()


# ---------- DASHBOARD ----------
if menu == "Dashboard":
    st.header("Teacher Dashboard")
    st.success(f"Welcome, {st.session_state.full_name}.")

    col1, col2, col3 = st.columns(3)
    col1.metric("Visible Students", len(students_df))
    col2.metric("Visible Assessment Records", len(assessments_df))
    col3.metric("Visible Anecdotal Records", len(anecdotal_df))

    st.subheader("Download Visible Data")

    d1, d2, d3 = st.columns(3)

    with d1:
        st.download_button(
            "Download Students Excel",
            data=to_excel(students_df),
            file_name="students.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    with d2:
        st.download_button(
            "Download Assessments Excel",
            data=to_excel(assessments_df),
            file_name="assessments.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    with d3:
        st.download_button(
            "Download Anecdotal Excel",
            data=to_excel(anecdotal_df),
            file_name="anecdotal_records.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    if st.session_state.role == "Admin":
        st.subheader("Admin Overview")

        users_df = load_users()
        teachers_df = users_df[users_df["Role"] == "Teacher"]

        st.write("Teacher Accounts")
        st.dataframe(teachers_df[["Full Name", "Username", "Role"]], use_container_width=True)

        st.write("Students and Assigned Classes")
        st.dataframe(students_df[["Student Name", "Class", "Teacher Name"]], use_container_width=True)

        st.write("Classes Assigned to Teachers")

        if not students_df.empty:
            teacher_classes = students_df.groupby("Teacher Name")["Class"].unique().reset_index()
            teacher_classes["Class"] = teacher_classes["Class"].apply(lambda x: ", ".join(x))
            st.dataframe(teacher_classes, use_container_width=True)
        else:
            st.info("No students have been assigned yet.")

    if st.session_state.role == "Teacher":
        st.info("Teacher access is active. You can only view students and records assigned to your username.")

    st.subheader("Search All Visible Records")
    dashboard_search = st.text_input("Search")

    st.subheader("Students")
    st.dataframe(filter_dataframe(students_df, dashboard_search), use_container_width=True)

    st.subheader("Assessments")
    st.dataframe(filter_dataframe(assessments_df, dashboard_search), use_container_width=True)

    st.subheader("Anecdotal Records")
    st.dataframe(filter_dataframe(anecdotal_df, dashboard_search), use_container_width=True)


# ---------- STUDENT PROFILES ----------
elif menu == "Student Profiles":
    st.header("Student Profiles")

    with st.form("student_form"):
        student_name = st.text_input("Student Name")
        class_name = st.selectbox("Class", CLASSES)

        if st.session_state.role == "Admin":
            users = load_users()
            teachers = users[users["Role"] == "Teacher"]["Username"].tolist()

            if teachers:
                teacher_name = st.selectbox("Assign Teacher", teachers)
            else:
                teacher_name = ""
                st.warning("No teacher accounts created yet.")
        else:
            teacher_name = st.session_state.username
            st.info(f"Assigned Teacher: {st.session_state.full_name}")

        submitted = st.form_submit_button("Save Student Profile")

        if submitted:
            if student_name.strip() == "":
                st.error("Please enter a student name.")
            elif teacher_name == "":
                st.error("Please create a teacher account first.")
            else:
                save_student(student_name, class_name, teacher_name)
                st.success(f"{student_name} has been saved successfully.")

    st.subheader("Search and Filter Students")

    col1, col2 = st.columns(2)
    with col1:
        student_search = st.text_input("Search Students")
    with col2:
        class_filter = st.selectbox("Filter by Class", ["All"] + CLASSES)

    filtered_students = filter_dataframe(students_df, student_search, class_filter)
    st.dataframe(filtered_students, use_container_width=True)

    st.download_button(
        "Download Filtered Students Excel",
        data=to_excel(filtered_students),
        file_name="filtered_students.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# ---------- ASSESSMENT RECORDS ----------
elif menu == "Assessment Records":
    st.header("Assessment Records")

    if not student_list:
        st.warning("No students available for this account.")
    else:
        with st.form("assessment_form"):
            student = st.selectbox("Select Student", student_list)

            selected_student_row = students_df[students_df["Student Name"] == student]
            teacher_name = selected_student_row.iloc[0]["Teacher Name"]

            term = st.selectbox("Academic Term", TERMS)
            week = st.text_input("Week")
            assessment_date = st.date_input("Date", date.today())
            subject = st.selectbox("Subject", SUBJECTS)
            topic = st.text_input("Assessment Topic")

            score = st.number_input("Score Earned", min_value=0.0)
            total_marks = st.number_input("Total Marks", min_value=1.0)

            percentage = round((score / total_marks) * 100, 1)
            st.info(f"Calculated Percentage: {percentage}%")

            submitted = st.form_submit_button("Save Assessment")

            if submitted:
                if topic.strip() == "":
                    st.error("Please enter the assessment topic.")
                elif score > total_marks:
                    st.error("Score earned cannot be greater than total marks.")
                else:
                    save_assessment(
                        student, teacher_name, term, week,
                        assessment_date, subject, topic, score, total_marks
                    )
                    st.success("Assessment saved successfully.")

    st.subheader("Search and Filter Assessment Records")

    col1, col2, col3 = st.columns(3)
    with col1:
        assessment_search = st.text_input("Search Assessments")
    with col2:
        assessment_term_filter = st.selectbox("Filter by Term", ["All"] + TERMS)
    with col3:
        assessment_subject_filter = st.selectbox("Filter by Subject", ["All"] + SUBJECTS)

    filtered_assessments = filter_dataframe(
        assessments_df,
        search_text=assessment_search,
        term_filter=assessment_term_filter,
        subject_filter=assessment_subject_filter
    )

    st.dataframe(filtered_assessments, use_container_width=True)

    st.download_button(
        "Download Filtered Assessments Excel",
        data=to_excel(filtered_assessments),
        file_name="filtered_assessments.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# ---------- ANECDOTAL RECORDS ----------
elif menu == "Anecdotal Records":
    st.header("Anecdotal Records")

    if not student_list:
        st.warning("No students available for this account.")
    else:
        with st.form("anecdotal_form"):
            student = st.selectbox("Select Student", student_list)

            selected_student_row = students_df[students_df["Student Name"] == student]
            teacher_name = selected_student_row.iloc[0]["Teacher Name"]

            term = st.selectbox("Academic Term", TERMS)
            week = st.text_input("Week")
            record_date = st.date_input("Date", date.today())
            topic = st.text_input("Observation / Topic")

            st.markdown("### Voice-to-Text Note")
            audio_file = st.audio_input("Record Voice Note")

            transcript = ""

            if audio_file:
                st.audio(audio_file)

                with open("temp_audio.wav", "wb") as f:
                    f.write(audio_file.read())

                try:
                    with st.spinner("Loading speech-to-text model..."):
                        model = load_whisper_model()

                    with st.spinner("Transcribing voice note..."):
                        result = model.transcribe("temp_audio.wav")
                        transcript = result["text"]

                    st.success("Voice note transcribed successfully.")

                except Exception as e:
                    st.error("Voice transcription could not run.")
                    st.warning("Check openai-whisper, torch, and FFmpeg.")
                    st.code(str(e))

            notes = st.text_area("Anecdotal Notes", value=transcript, height=150)
            comments = st.text_area("General Comments")

            submitted = st.form_submit_button("Save Anecdotal Record")

            if submitted:
                if notes.strip() == "":
                    st.error("Please enter anecdotal notes.")
                else:
                    save_anecdotal(
                        student, teacher_name, term, week,
                        record_date, topic, notes, comments
                    )
                    st.success("Anecdotal record saved successfully.")

    st.subheader("Search and Filter Anecdotal Records")

    col1, col2 = st.columns(2)
    with col1:
        anecdotal_search = st.text_input("Search Anecdotal Records")
    with col2:
        anecdotal_term_filter = st.selectbox("Filter by Term", ["All"] + TERMS)

    filtered_anecdotal = filter_dataframe(
        anecdotal_df,
        search_text=anecdotal_search,
        term_filter=anecdotal_term_filter
    )

    st.dataframe(filtered_anecdotal, use_container_width=True)

    st.download_button(
        "Download Filtered Anecdotal Records Excel",
        data=to_excel(filtered_anecdotal),
        file_name="filtered_anecdotal_records.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# ---------- ACADEMIC ALERTS ----------
elif menu == "Academic Alerts":
    st.header("Academic Warning System")

    if assessments_df.empty:
        st.warning("No assessment records saved yet.")
    elif not student_list:
        st.warning("No students available for this account.")
    else:
        student = st.selectbox("Select Student", student_list)

        student_records = assessments_df[assessments_df["Student Name"] == student]

        if student_records.empty:
            st.info("No assessment records found for this student.")
        else:
            average_score = student_records["Percentage"].mean()
            latest_score = student_records.iloc[-1]["Percentage"]

            col1, col2 = st.columns(2)
            col1.metric("Average Percentage", f"{average_score:.1f}%")
            col2.metric("Latest Percentage", f"{latest_score:.1f}%")

            if average_score < 50:
                st.error(f"{student} may be falling behind academically. Immediate intervention is recommended.")
            elif average_score < 70:
                st.warning(f"{student} should be monitored closely.")
            else:
                st.success(f"{student} is performing satisfactorily.")

            st.subheader("Assessment History")
            st.dataframe(student_records, use_container_width=True)

            st.download_button(
                "Download Student Alert Report Excel",
                data=to_excel(student_records),
                file_name=f"{student}_alert_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )


# ---------- REPORTS ----------
elif menu == "Reports":
    st.header("Reports")

    if not student_list:
        st.warning("No students available for this account.")
    else:
        student = st.selectbox("Select Student", student_list)

        report_type = st.selectbox(
            "Report Type",
            ["Academic Report", "Anecdotal Report", "Intervention Report", "AI Report Comment"]
        )

        student_assessments = assessments_df[assessments_df["Student Name"] == student]
        student_notes = anecdotal_df[anecdotal_df["Student Name"] == student]

        st.subheader(f"Report for {student}")

        if not student_assessments.empty:
            average_score = student_assessments["Percentage"].mean()
            st.write(f"Average Assessment Percentage: {average_score:.1f}%")

            subject_average = student_assessments.groupby("Subject")["Percentage"].mean()
            strongest_subject = subject_average.idxmax()
            weakest_subject = subject_average.idxmin()

            if average_score < 50:
                st.error("Academic Status: Intervention Required")
            elif average_score < 70:
                st.warning("Academic Status: Monitor Closely")
            else:
                st.success("Academic Status: Satisfactory")

            st.write(f"Strongest Area: {strongest_subject}")
            st.write(f"Area for Support: {weakest_subject}")

        else:
            average_score = 0
            strongest_subject = "Not enough assessment data"
            weakest_subject = "Not enough assessment data"
            st.info("No assessment records found.")

        st.subheader("Assessment Records")
        st.dataframe(student_assessments, use_container_width=True)

        st.subheader("Anecdotal Records")
        st.dataframe(student_notes, use_container_width=True)

        report_summary = pd.DataFrame({
            "Student Name": [student],
            "Average Percentage": [average_score],
            "Strongest Area": [strongest_subject],
            "Area for Support": [weakest_subject],
            "Report Type": [report_type]
        })

        st.download_button(
            "Download Student Report Summary Excel",
            data=to_excel(report_summary),
            file_name=f"{student}_report_summary.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.download_button(
            "Download Student Assessment Records Excel",
            data=to_excel(student_assessments),
            file_name=f"{student}_assessment_records.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.download_button(
            "Download Student Anecdotal Records Excel",
            data=to_excel(student_notes),
            file_name=f"{student}_anecdotal_records.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.divider()
        st.header("AI Report Comment Generator")

        teacher_strength = st.text_input("Optional: Add a strength you noticed")
        teacher_challenge = st.text_input("Optional: Add an area of concern")
        teacher_strategy = st.text_input("Optional: Add a strategy or recommendation")

        notes_text = ""

        if not student_notes.empty:
            notes_text = " ".join(
                student_notes["Anecdotal Notes"].dropna().astype(str).tail(3).tolist()
            )

        if teacher_strength:
            notes_text += f" Strength observed: {teacher_strength}."
        if teacher_challenge:
            notes_text += f" Area of concern: {teacher_challenge}."
        if teacher_strategy:
            notes_text += f" Recommended strategy: {teacher_strategy}."

        if st.button("Generate AI Comment"):
            if student_assessments.empty:
                st.warning("Add assessment records first to generate a stronger AI comment.")
            else:
                ai_comment = generate_ai_comment(
                    student,
                    average_score,
                    strongest_subject,
                    weakest_subject,
                    notes_text
                )

                st.text_area("Generated Report Comment", ai_comment, height=220)


# ---------- USER ACCOUNTS ----------
elif menu == "User Accounts":
    st.header("User Accounts")

    if st.session_state.role != "Admin":
        st.warning("Only the admin can view user accounts.")
    else:
        users = load_users()

        st.subheader("Registered Users")
        visible_users = users[["Full Name", "Username", "Role"]]
        st.dataframe(visible_users, use_container_width=True)

        st.download_button(
            "Download User Accounts Excel",
            data=to_excel(visible_users),
            file_name="user_accounts.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.info("For this prototype, passwords are stored in users.csv. For real school use, passwords must be encrypted.")
