import streamlit as st
import qrcode
from PIL import Image
import os
import firebase_admin
from firebase_admin import credentials, db
import time
from streamlit_js_eval import get_geolocation
import math
from streamlit_js_eval import streamlit_js_eval
import pandas as pd
import pydeck as pdk

st.set_page_config(page_title="CampusRath",layout="wide")
json_file = "prsu-ricksaw-tracker-firebase-adminsdk-fbsvc-8e88bb1de7.json"

if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(json_file) 
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://prsu-ricksaw-tracker-default-rtdb.asia-southeast1.firebasedatabase.app/'
        })
    except Exception as e:
        st.error(f"Cloud Connection Error: {e}")

status_data = db.reference('system_status').get()
rickshaw_pos = db.reference('rickshaw_location').get()



if status_data:
    is_live = status_data.get('is_live', False)
    stop_reason = status_data.get('stop_reason', "No reason provided")
    
    if not is_live:
        # 2. Show a professional alert to the students
        st.error(f"⚠️ Rickshaw is currently OFFLINE")
        st.info(f"**Driver's Note:** {stop_reason}")
    else:
        st.success("✅ Rickshaw is currently LIVE on campus")

user_id = streamlit_js_eval(js_expressions="window.location.hostname", key="USER_ID")

# 1. Initialize Firebase only if it hasn't been started yet

st.success("Bridge Connected to Firebase! 🚀")



# Define your translations
translations = {
    "English": {
        "write":"Prof. Rajendra Singh (Rajju Bhaiya) University",
        "title": "🛺 Live Campus Rickshaw Tracker",
        "header": "Check real-time location",
        "button": "Click to track location",
        "sidebar_title": "📲 Mobile Access",
        "sidebar_write":"Scan to track rickshaw on your phone",
        "qr_caption": "Scan to track"
    },
    "Hindi": {
        "write":"प्रो० राजेन्द्र सिंह (रज्जू भय्या) विश्वविद्यालय",
        "title": "🛺 लाइव कैंपस रिक्शा ट्रैकर",
        "header": "वास्तविक समय की स्थिति जांचें",
        "button": "लोकेशन ट्रैक करने के लिए क्लिक करें",
        "sidebar_title": "📲 मोबाइल एक्सेस",
        "sidebar_write":"अपने फोन पर रिक्शा ट्रैक करने के लिए स्कैन करें",
        "qr_caption": "ट्रैक करने के लिए स्कैन करें"
    }
}
language = st.sidebar.radio("Select Language / भाषा चुनें", ["English", "Hindi"])
lang=translations[language]
st.header(lang["write"])
st. write(lang["title"])
st.write(lang["header"])
st.button(lang["button"])

st.subheader("🛰️ Live Campus Radar")

if rickshaw_pos and isinstance(rickshaw_pos, dict):
    import pandas as pd
    
    # Create the data frame for the original map
    df_map = pd.DataFrame({
        'lat': [rickshaw_pos['lat']],
        'lon': [rickshaw_pos['lon']]
    })
    
    # Using the standard map (No white block issues)
    st.map(df_map, zoom=15)
    st.caption(f"Last signal received: {rickshaw_pos.get('last_updated', 'N/A')}")
else:
    st.info("Searching for Rickshaw signal... 📡")
    
def get_qr_code(url):
    qr = qrcode.QRCode(version=1, box_size=10, border=10)
    # This points to your LIVE app
    qr.add_data("https://campusrath-tklfehqbbq8luduku5s4b3.streamlit.app/")
    qr.make(fit=True)
    image = qr.make_image(fill_color="Black", back_color="white")
    
    # FIXED: Actually save the file to the cloud's current folder
    qr_path = "website_qr.png"
    image.save(qr_path)
    return qr_path

st.sidebar.title(lang["sidebar_title"])
st.sidebar.write(lang["sidebar_write"])
site_url=""
qr_img_path=get_qr_code("website_qr.png")
st.sidebar.image(qr_img_path,caption="scan qr to track")


# 1. Add a lot of vertical space so the footer is at the very bottom
for _ in range(5):
    st.write("")


# Precise PRSU Campus Coordinates
CAMPUS_LAT = 25.35496
CAMPUS_LON = 81.88766
ALLOWED_RADIUS_KM = 0.8 

def is_inside_campus(user_lat, user_lon):
    R = 6371 
    dLat = math.radians(user_lat - CAMPUS_LAT)
    dLon = math.radians(user_lon - CAMPUS_LON)
    a = math.sin(dLat/2)**2 + math.cos(math.radians(CAMPUS_LAT)) * \
        math.cos(math.radians(user_lat)) * math.sin(dLon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return (R * c) <= ALLOWED_RADIUS_KM

# Add a unique key to prevent the DuplicateElementKey error
user_id = streamlit_js_eval(js_expressions="window.location.hostname", key="BROWSER_ID")
with st.container():
    loc = get_geolocation()

# Check if the user is on the blacklist before showing anything
is_blocked = db.reference(f'blacklist/{user_id}').get()

if is_blocked:
    st.sidebar.error("Access Revoked 🛑")
    st.sidebar.warning("You have been banned for violating campus transit rules.")
elif loc:
    lat = loc['coords']['latitude']
    lon = loc['coords']['longitude']
    
    if is_inside_campus(lat, lon):
        st.sidebar.success("Verified: On PRSU Campus ✅")
        
        urgent_msg = st.sidebar.text_input("Message for Driver", placeholder="Type here...", key="msg_input")
        
        if st.sidebar.button("Send Request"):
            if urgent_msg:
                try:
                    ref = db.reference('passenger_requests')
                    ref.push({
                        'text': urgent_msg,
                        'user_id': user_id, # Send the ID so driver can block
                        'timestamp': time.strftime("%H:%M:%S"),
                        "status": "new"
                    })
                    st.sidebar.success("Request Sent!")
                except Exception as e:
                    st.sidebar.error(f"Bridge Error: {e}")
    else:
        st.sidebar.error("Outside Geofence 🛑")
else:
    st.sidebar.info("Waiting for GPS location...")


st.divider()
# 2. Use a simple centered column for credits
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    st.markdown(
        """
        <div style="text-align: center; color: gray; font-size: 14px;">
            Designed & Developed by: <br>
            <b>Shashank Shekhar Gupta & Suryansh Mishra & Vineet Thakur</b> <br>
            Branch: B.Tech Computer Science <br>
            © 2026 | Science Exhibition Project
        </div>
        """,
        unsafe_allow_html=True
    )

time.sleep(5)

st.rerun()





