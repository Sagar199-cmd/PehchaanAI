import streamlit as st

import numpy as np

from src.database.config import supabase
from src.components.subject_card import subject_card
from src.components.header import header_dashboard
from src.ui.base_layout import style_background_dashboard

from src.database.db import check_teacher_exists , create_teacher,teacher_login,get_teacher_subjects,get_attendance_for_teacher

from src.pipelines.face_pipeline import predict_attendance

from src.components.dialog_create_subject import create_subject_dialog
from src.components.dialog_share_subject import share_subject_dialog

from src.components.dialog_add_photos import add_photos_dialog
from src.components.dialog_attendance_result import show_attendance_result,attendance_result_dialog
from src.components.dialog_voice_attendance import voice_attendance_dialog

import pandas as pd
from datetime import datetime

def teacher_screen():
    style_background_dashboard()

    if "teacher_data" in st.session_state:
        teacher_dashboard()
    elif 'teacher_login_type' not in st.session_state or st.session_state.teacher_login_type == "login":
        teacher_screen_login() 
    elif st.session_state.teacher_login_type == "register":
        teacher_screen_register()

def teacher_dashboard():
    teacher_data = st.session_state.teacher_data
    col1 , col2 = st.columns(2, vertical_alignment='center',gap = 'xxlarge')
    
    with col1:
        header_dashboard()
    
    with col2:
        st.subheader(f"Welcome , {teacher_data['name']}")
        if st.button('Logout',type='secondary' , key = 'loginbackbtn',  shortcut='ctrl+backspace'):
            st.session_state['login_type'] = None
            del st.session_state.teacher_data
            st.rerun()

    st.space()

    if "current_teacher_tab" not in st.session_state:
        st.session_state.current_teacher_tab = 'take_attendance'
    tab1,tab2,tab3 = st.columns(3)

    with tab1:
        type1= "primary" if st.session_state.current_teacher_tab == 'take_attendance' else "tertiary"
        if st.button('Take Attendance',type = type1 , width='stretch',icon=':material/ar_on_you:'):
            st.session_state.current_teacher_tab = 'take_attendance'
            st.rerun()

    with tab2:
        type2= "primary" if st.session_state.current_teacher_tab == 'manage_subjects' else "tertiary"
        if st.button('Manage Subjects',type = type2,width='stretch',icon=':material/book_ribbon:'):
            st.session_state.current_teacher_tab = 'manage_subjects'
            st.rerun()

    with tab3:
        type3= "primary" if st.session_state.current_teacher_tab == 'attendance_records' else "tertiary"
        if st.button('Attendance Record',type=type3 , width='stretch',icon=':material/cards_stack:'):
            st.session_state.current_teacher_tab = 'attendance_records'
            st.rerun()

    if st.session_state.current_teacher_tab =="take_attendance":
        teacher_tab_take_attendance()
    if st.session_state.current_teacher_tab =="manage_subjects":
        teacher_tab_manage_subjects()
    if st.session_state.current_teacher_tab =="attendance_records":
        teacher_tab_attendance_records()
    
    

def teacher_tab_take_attendance():
    teacher_id = st.session_state.teacher_data['teacher_id']

    st.header("Take AI Attendance")

    if 'attendance_images' not in st.session_state:
        st.session_state.attendance_images=[]

    subjects = get_teacher_subjects(teacher_id)

    if not subjects:
        st.warning("You haven't created any subjects yet! Please create one to begin")
        return
    subject_options = {f"{s['name']} - {s['subject_code']}": s['subject_id'] for s in subjects}

    # columns size in 3:1 ratio
    col1, col2 = st.columns([3,1], vertical_alignment='bottom')

    with col1:
        selected_subject_label = st.selectbox('Select Subject', options=list(subject_options.keys()))

    with col2:
        if st.button('Add Photos', type='primary', icon=':material/photo_prints:', width='stretch'):
            add_photos_dialog()

    selected_subject_id = subject_options[selected_subject_label]
    # selected course by teacher to take attendance

    st.divider()

    # if images hai agar attendance images state mein to
    if st.session_state.attendance_images:
        st.header('Added Photos')
        gallery_cols = st.columns(4)
        # 4 images in a row to display

        for idx, img in enumerate(st.session_state.attendance_images): #fetching idx and image
            with gallery_cols[idx % 4 ]:
                st.image(img, width='stretch', caption=f'Photo {idx+1}')

    has_photos = bool(st.session_state.attendance_images)
    c1, c2, c3 = st.columns(3)

    #remove all photos
    with c1:
        if st.button('Clear all photos', width='stretch', type='tertiary', icon=':material/delete:', disabled=not has_photos):
            # using disabled in above button if no photos are there
            st.session_state.attendance_images = []
            st.rerun()

    #Face Analysis
    with c2:
        
        if st.button('Run Face Analysis', width='stretch', type='secondary', icon=':material/analytics:', disabled=not has_photos):
            with st.spinner('Deep scanning classroom photos...'):
                all_detected_ids = {}
                # detect student id from photos

                for idx, img in enumerate(st.session_state.attendance_images):
                    img_np = np.array(img.convert('RGB'))
                    # convert image into RGB and then into np array before predict attendance
                    detected, _, _ = predict_attendance(img_np)
                    # it return 3 values but we need only detected so we can left rest as _

                    # detected will contain data like {'101':True, '102':True} '101' - student_id
                    if detected:
                        for sid in detected.keys():
                            student_id = sid

                            all_detected_ids.setdefault(student_id, []).append(f"Photo {idx+1}")
                            # if student id is present in all_detected_id dict then it will append photo [idx+1] like {101 : [Photo1]}
                            # if not it will insert id as key and empty list like {101:[]}

                 
                else:

                    results, attendance_to_log  = [], []
                    # create result table to display and attendance to log to insert in supabase

                    current_timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                    # create timestamp in specific format

                    enrolled_res = supabase.table('subject_students').select("*, students(*)").eq('subject_id',selected_subject_id ).execute()
                    enrolled_students = enrolled_res.data
                          
                    if not enrolled_students:
                        st.warning('No students enrolled in this course')
                        return


                    for node in enrolled_students:
                        student = node['students']
                        sources = all_detected_ids.get(student['student_id'], [])
                        # fetching photo source for each student in which photo they present if they are absent then empty array
                        is_present= len(sources) > 0
                        # if they present in any photo then len(source) > 0

                        #create result table
                        results.append({
                            "Name": student['name'],
                            "ID": student['student_id'],
                            "Source": ", ".join(sources) if is_present else "-", # show all photo sources as comma seperated
                            "Status": "✅ Present" if is_present else "❌ Absent"
                        })

                        attendance_to_log.append({
                            'student_id': student['student_id'],
                            'subject_id': selected_subject_id,
                            'timestamp': current_timestamp,
                            'is_present': bool(is_present)
                        })

                # show attendance and update in db too
                attendance_result_dialog(pd.DataFrame(results), attendance_to_log)

    # Voice Analysis
    with c3:
        if st.button('Use Voice Attendance', type='primary', width='stretch', icon=':material/mic:'):
            voice_attendance_dialog(selected_subject_id)





def teacher_tab_manage_subjects():
    teacher_id = st.session_state.teacher_data['teacher_id']
    col1, col2 = st.columns(2)
    with col1:
        st.header('Manage Subjects', width='stretch')

    with col2:
        if st.button('Create New Subject', width='stretch'):
            create_subject_dialog(teacher_id)


    # LIST all SUBJECTS
    subjects = get_teacher_subjects(teacher_id)
    if subjects:
        for sub in subjects:
            stats = [
                ("🫂", "Students", sub['total_students']),
                ("🕰️", "Classes", sub['total_classes']),
            ]
            
            def share_btn(current_name=sub['name'], current_code=sub['subject_code']):
                if st.button(f"Share Code: {current_name}", key=f"share_{current_code}", icon=":material/share:"):
                    share_subject_dialog(current_name, current_code)
                st.space()

            subject_card(
                name = sub['name'],
                code = sub['subject_code'],
                section = sub['section'],
                stats=stats,
                footer_callback=share_btn
            )
    else:
        st.info("NO SUBJECTS FOUND. CREATE ONE ABOVE")




def teacher_tab_attendance_records():
    st.header("Attendance Record")
    teacher_id = st.session_state.teacher_data['teacher_id']

    records = get_attendance_for_teacher(teacher_id)

    if not records:
        return

    # cleaning attendance record
    data = []

    for r in records:
        ts = r.get("timestamp")

        data.append({
            "ts_group": ts.split(".")[0] if ts else None,
            # eg ts = "2026-10-18 10:30:25.456789"
            # fetching timestamp while excluding milisec because we want to group on the basis of timestamp

            "Time" : datetime.fromisoformat(ts).strftime("%Y-%m-%d %I:%M %p") if ts else "N'A",
            #fetch time in specific format

            "Subject" : r['subjects']['name'],

            "Subject_Code" : r['subjects']['subject_code'],

            "Student_Name" : r['students']['name'],

            "is_present" :bool(r.get("is_present",False))
        })

    df = pd.DataFrame(data)

    summary = (
        df.groupby(['ts_group','Time','Subject','Subject_Code']).agg(
            Present_Count = ('is_present','sum'),
            #sum the ispresent col value eg(0+1+1+1+0) 1-true , 0-false
            Total_Count = ('is_present' , 'count')
            # count
        ).reset_index()
        #After grouping, Pandas uses the grouping columns as the index. reset_index() converts them back into regular columns.
    )

    summary["Attendance Stats"] = (
        "✅️" + summary['Present_Count'].astype(str) + " /" + summary["Total_Count"].astype(str) + ' Students'
    )

    display_df = (summary.sort_values(by='ts_group',ascending=False))[['Time' , 'Subject' , 'Subject_Code' , 'Attendance Stats']]
    # sort cleaned data by ts_group in descending order so latest display on top and choose col to display

    st.dataframe(display_df,width='stretch',hide_index = True)
    st.divider()
    st.subheader('Subject-wise Detailed Attendance')
    
    unique_subjects = df['Subject'].unique()
    selected_subject = st.selectbox('Select Subject for Details', unique_subjects)
    
    if selected_subject:
        subject_df = df[df['Subject'] == selected_subject]
        
        stu_summary = (
            subject_df.groupby('Student_Name')
            .agg(
                Present = ('is_present', 'sum'),
                Total_Classes = ('is_present', 'count')
            ).reset_index()
        )
        
        stu_summary['Attendance %'] = (stu_summary['Present'] / stu_summary['Total_Classes'] * 100).round(1).astype(str) + '%'
        
        st.dataframe(stu_summary, width='stretch', hide_index=True)
  

def login_teacher(username,password):
    if not username or not password:
        st.error("Please fill all the fields")
        return None

    teacher = teacher_login(username,password)
    if teacher:
        st.session_state.teacher_data = teacher
        st.session_state.user_role = "teacher"
        st.session_state.is_logged_in = True
        return True
    else:
        st.error("Invalid username or password")
        return None
    
def register_teacher(username,name,password,password_confirm):
    if not username or not password or not name:
        return False , "Please fill all the fields"
    if check_teacher_exists(username):
        return False , "Username already exists"
    if password != password_confirm:
        return False , "Passwords do not match"

    try:
        create_teacher(username,password,name)
        return True , "Teacher account created successfully"
    except Exception as e:
        return False , "Unexpected error occurred while creating teacher account"

def teacher_screen_register():

    col1 , col2 = st.columns(2, vertical_alignment='center',gap = 'xxlarge')
    
    with col1:
        header_dashboard()
    
    with col2:
        if st.button('Go Back',type='secondary' , key = 'go_back_teacher', icon=':material/arrow_back:', icon_position='left' , shortcut='ctrl+backspace'):
            st.session_state['login_type'] = None
            st.rerun()
    
    st.header("Register your teacher account" , text_alignment='center')

    st.space()
    teacher_username = st.text_input("Enter Username", placeholder='sagarawasthi')
    teacher_name = st.text_input("Enter Name" , placeholder='Sagar Awasthi')
    teacher_pass = st.text_input("Enter Password" , type= 'password', placeholder='password')
    teacher_pass_confirm = st.text_input("Confirm Password" , type= 'password', placeholder='password')


    st.divider()

    btn1,btn2 = st.columns(2 , gap='small' , vertical_alignment='center')

    with btn1:
        if st.button('Register Now' , type='primary' , key = 'register_teacher', icon=':material/passkey:', icon_position='left'   , width='stretch'):
            success,message = register_teacher(teacher_username,teacher_name,teacher_pass,teacher_pass_confirm)
            if success:
                st.success(message)
                import time
                time.sleep(2)
                st.session_state.teacher_login_type = 'login'
                st.rerun()
            else:
                st.error(message)

        

    with btn2:
          if st.button('Login Instead' , type='secondary' , key = 'login_teacher', icon=':material/passkey:', icon_position='left' , width='stretch',shortcut='ctrl+enter'):
              st.session_state["teacher_login_type"] = 'login'
              st.rerun()
              
                                  


def teacher_screen_login():
    
    col1 , col2 = st.columns(2, vertical_alignment='center',gap = 'xxlarge')
    
    with col1:
        header_dashboard()
    
    with col2:
        if st.button('Go Back',type='secondary' , key = 'go_back_teacher', icon=':material/arrow_back:', icon_position='left' , shortcut='ctrl+backspace'):
            st.session_state.teacher_login_type = 'register'
            st.rerun()
    
    st.header("Login using password" , text_alignment='center')

    st.space()
    teacher_username = st.text_input("Enter Username", placeholder='sagarawasthi')
    teacher_pass = st.text_input("Enter Password" , type= 'password', placeholder='password')

    st.divider()

    btn1,btn2 = st.columns(2 , gap='small' , vertical_alignment='center')

    with btn1:
        if st.button('Login Now' , type='secondary' , key = 'login_teacher', icon=':material/passkey:', icon_position='left' , shortcut='ctrl+enter' , width='stretch'):
            if login_teacher(teacher_username,teacher_pass):
                    st.toast("Welcome back, " + teacher_username , icon="👋" )
                    import time
                    time.sleep(2)
                    st.rerun()
            else:
                st.error("Invalid username or password")

    with btn2:
        if st.button('Register Instead' , type='primary' , key = 'register_teacher', icon=':material/passkey:', icon_position='left'   , width='stretch'):
            st.session_state.teacher_login_type = 'register'
            st.rerun()
            
