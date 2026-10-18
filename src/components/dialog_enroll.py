import streamlit as st
from src.database.config import supabase
import time
from src.database.db import enroll_student_to_subject


@st.dialog("Enroll in Subject")
def enroll_dialog():
  st.write('Enter the subject code provide by your teacher to enroll')
  join_code = st.text_input('Subject Code',placeholder='Eg. CS101')

  if st.button('Enroll Now',type='primary',width='stretch'):
    #join should exist in db 
    if join_code:
      res = supabase.table('subjects').select('subject_id,name,subject_code').eq('subject_code',join_code).execute()
      # code exist
      if res.data:
        subject = res.data[0]
        #check whether student is already registered in that course
        student_id = st.session_state.student_data['student_id']

        check = supabase.table('subject_students').select('*').eq('subject_id',subject['subject_id']).eq('student_id',student_id).execute()

        if check.data:
          st.warning('You are already enrolled in this program')
        else:
          enroll_student_to_subject(student_id,subject['subject_id'])
          st.success('Successfully')
          time.sleep(1)
          st.rerun()
      else:
        st.warning('Please enter a subject code')
     