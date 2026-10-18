import streamlit as st

from src.components.header import header_dashboard
from src.ui.base_layout import style_background_dashboard

from src.database.db import get_all_students,create_student,get_student_subjects, get_student_attendance,unenroll_student_to_subject

from PIL import Image #Pillow
import numpy as np

from src.pipelines.face_pipeline import predict_attendance,get_face_embeddings,train_classifier

from src.pipelines.voice_pipeline import get_voice_embedding

from src.components.dialog_enroll import enroll_dialog

from src.components.subject_card import subject_card


def student_dashboard():
    student_data = st.session_state.student_data
    student_id = student_data['student_id']
    col1 , col2 = st.columns(2, vertical_alignment='center',gap = 'xxlarge')
    
    with col1:
        header_dashboard()
    
    with col2:
        st.subheader(f"Welcome , {student_data['name']}")
        if st.button('Logout',type='secondary' , key = 'loginbackbtn',  shortcut='ctrl+backspace'):
            st.session_state['login_type'] = None
            del st.session_state.student_data
            st.rerun()

    st.space()

    c1,c2 = st.columns(2)

    with c1:
        st.header("Your Enrolled Subject")
    
    with c2:
        if st.button('Enroll in Subject',type='primary',width='stretch'):
            enroll_dialog()

    st.divider()

    with st.spinner("Loading your enrolled subjects.."):
        subjects = get_student_subjects(student_id)
        logs = get_student_attendance(student_id)

    stats_map = {}
    # store attendance statistics total no clasess for each subject and total attended eg : -
    """
        stats_map = {
            1: {'total': 2, 'attended': 1}, # 1- subject
            2   : {'total': 1, 'attended': 1} 
        }
    """

    for log in logs:
        sid = log['subject_id']

        if sid not in stats_map:
             stats_map[sid] = {'total': 0, 'attended': 0}

        stats_map[sid]['total'] += 1

        if log.get('is_present'):
            stats_map[sid]['attended'] += 1


    cols = st.columns(2)
    #enumerate(subjects) gives both the index i and the current enrollment record sub_node
    for i , sub_node in enumerate(subjects):
        #sample subnode
        """
            sub_node = {
                'student_id': 101,
                'subject_id': 1,
                'subjects': {
                    'subject_id': 1,
                    'name': 'DBMS',
                    'subject_code': 'CS301',
                    'section': 'A'
                }
            }
        """
        sub = sub_node['subjects']
        #sub_node['subjects'] extracts the related subject details fetched from Supabase
        sid = sub['subject_id']

        stats = stats_map.get(sid,{'total': 0, 'attended': 0})
        def unenroll_button():
            if st.button("Uneroll from this course",type='primary',width='stretch',icon=':material/delete_forever:'):
                unenroll_student_to_subject(student_id,sid)
                st.toast(f"Unerolled from course - {sub['name']} Sucessfully!")
                st.rerun()

        # display subjects in 2 columns (alternatively)
        with cols[i%2]:
            subject_card(
                name = sub['name'],
                code = sub['subject_code'],
                section = sub['section'],
                stats = [
                    ('🗓️','Total',stats['total']),
                    ('✅','Attended',stats['attended'])
                ],
                footer_callback = unenroll_button 
            )





def student_screen():
    style_background_dashboard()
    col1 , col2 = st.columns(2, vertical_alignment='center',gap = 'xxlarge')


    if "student_data" in st.session_state:
        student_dashboard()
        return 
    
    with col1:
        header_dashboard()
    
    with col2:
        if st.button('Go Back',type='secondary' , key = 'go_back_teacher', icon=':material/arrow_back:', icon_position='left' , shortcut='ctrl+backspace'):
            st.session_state['login_type'] = None
            st.query_params.clear()
            st.rerun()
    
    st.header("Login using FaceID" , text_alignment='center')

    st.space()
    photo_source = st.camera_input("Position your face in the centre")


    show_registration = False
    if photo_source:
        img = np.array(Image.open(photo_source))

        with st.spinner("AI is scanning..."):
            detected , all_ids , num_faces = predict_attendance(img)

            if num_faces == 0:
                st.warning('Face not found')
            elif num_faces >1:
                st.warning('Multiple faces found')
            else:
                # only 1 face should be detected because we are not taking attendace student is logging to his dashboard
                if detected:
                    student_id = list(detected.keys())[0]
                    # detected will be like {'101':True} convert keys into list [101] then [0] will return 101
                    all_students = get_all_students()
                    # fetching all students from db
                    
                    student = next((s for s in all_students if s['student_id']==student_id),None)
                    # finding student id in database record ,next() return first produced value so if that loop return nothing it will take 2nd value that is none

                    if student:
                        #if student is find in db updates session states
                        st.session_state.is_logged_in = True
                        st.session_state.user_role = 'student'
                        st.session_state.student_data = student

                        st.toast(f"Welcome Back {student['name']}")
                        #display pop up 
                        import time
                        time.sleep(1)
                        st.rerun()
                else:
                    st.info('Face not recognized! You might be a new student')
                    show_registration = True
                
    #register new student
    if show_registration:
        with st.container(border=True):
            st.header('Register new Profile')

            new_name = st.text_input('Enter you name',placeholder='E.g. Sagar Awasthi')

            st.subheader('Optional : Voice Enrollment')
            st.info("Enroll your voice for voice only attendance")

            audio_data = None
            try:
                audio_data = st.audio_input("Record a short phrase like I am present , My name is Sagar ... ")

            except Exception:
                st.error('Audio Data Failde')

            if st.button('Create Account',type='primary'):
                #name must be entered
                if new_name:
                    with st.spinner('Creating profile...'):
                        img = np.array(Image.open(photo_source))
                        encodings = get_face_embeddings(img)
                        #find embedding of new student face

                        if encodings:
                            face_emb = encodings[0].tolist()
                            # embeddings will return in 2d convert into 1d and list

                            voice_emb = None #optional thats why mark none

                            if audio_data:
                                voice_emb = get_voice_embedding(audio_data.read())

                            response_data = create_student(new_name,face_embedding=face_emb,voice_embedding=voice_emb)

                            if response_data:
                                train_classifier()
                                st.session_state.is_logged_in = True
                                st.session_state.user_role = 'student'
                                st.session_state.student_data = response_data[0]
                                st.toast(f"Profile Registered! Welcome {new_name}")
                                import time
                                time.sleep(1) 
                                st.rerun() 
                            else:
                                st.error('Could not register your facial features for recognition')                              


                else:
                    st.warning('Please enter your name')




    