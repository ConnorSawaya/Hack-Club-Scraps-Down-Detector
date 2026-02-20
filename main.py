import streamlit as st
import requests
import time
from datetime import datetime

#Config Page for things like the title and page icon!

st.set_page_config(page_title="Scraps Down Detector", page_icon="🔍")



# Mark down stuff for style
st.markdown(""" 
    <style>
    .status-box{
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            font-weight: bold;
            font-size: 24px;
            margin-bottom: 20px;
            }
        </style>
""", unsafe_allow_html=True)



st.title("Scraps Down Detector") # For the Top
st.write("Real Time Monitering for Scraps.hackclub.com") # Title and stuff basically


URL = "https://scraps.hackclub.com" # Target url might make it so u can put any 



def check_status(): # main thing to check if its pinging back any response to our request
    try:
        response = requests.get(URL, timeout=5) # Setting a timeout so hackclub does not get mad and block our request
        
        return response.status_code # Returns the status code
    except: # for exception
        return None
    

st.sidebar.header("Settings") # Sidebar Settings
refresh_rate = st.sidebar.slider("Refresh Rate (in Seconds)", 5, 60, 10) # Refresh rate so hackclub does not get mad for many requests

status_code = check_status() # Checks Status
current_time = datetime.now().strftime("%H:%M:%S") # current time variable for activity log 



if status_code ==200: # working normally
    st.success(f"Scraps is online ✅") # Shows scraps is on
    st.metric(label="Status Code", value=status_code, delta="Healthy")
    
    if st.button("Celebrate Scraps Actually working(rare event)"): # Funny Ballons celebration bc scraps is actually working 
        st.balloons() # streamlit premade balloons thing



elif status_code: # Partiually down error
    st.error(f" Scraps Is Acting Up Or Something") # Error msg 
    st.metric(label="Status Code", value=status_code, delta="- Issues Detected", delta_color="inverse") # shows status code requested using requests



else: # Last result So if its fully down
    st.error("Scraps is Down or Unreachable")  # If @notaroomba messes up the site again 😹 lol
    st.metric(label="Status Code", value="OFFLINE", delta ="=-Critical", delta_color="inverse")


    # Activity Log stuff 
st.divider()
st.subheader("Activity Log")
st.write(f"Last Checked at: '{current_time}'" )  # Time from last Scan

time.sleep(refresh_rate) # Refreshes so hackclub aint get angry Grrrrr...
st.rerun() # streamlit rerun so it aint jst stop 

