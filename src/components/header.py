import streamlit as st

def header_home():
    logo_url = "https://i.ibb.co/YTYGn5qV/logo.png"
    
    st.markdown(f"""
        <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; margin-bottom:30px; margin-top:30px">
            <img src='{logo_url}' style='height:100px;' />
            <h1 style='text-align:center; color:#E0E3FF'>Pehchaan AI</h1>
            <h3 style='text-align:center; color:#E0E3FF'>Smart Attendance with Face & Voice Recognition</h3>
        </div>   
                
    """, unsafe_allow_html=True)

def header_dashboard():
    logo_url = "https://i.ibb.co/YTYGn5qV/logo.png"
    
    st.markdown(f"""
        <div style="display:flex; align-items:center; justify-content:center; gap:20px; margin:30px 0; width:max-content; max-width:100%">
            <img src='{logo_url}' style='height:100px; flex-shrink:0' />
            <h1 style='text-align:center; color:#5865F2; margin:0; white-space:nowrap; flex-shrink:0'>Pehchaan AI</h1>
        </div>   
                
    """, unsafe_allow_html=True) 
    