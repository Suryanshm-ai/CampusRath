import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import time
import pandas as pd
import pydeck as pdk
from streamlit_js_eval import get_geolocation

st.set_page_config(page_title="CampusRath", layout="centered")
json_file = "prsu-ricksaw-tracker-firebase-adminsdk-fbsvc-8e88bb1de7.json"

if not firebase_admin._apps:
    try:
        # Load the certificate from the same folder as your code
        cred = credentials.Certificate(json_file) 
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://prsu-ricksaw-tracker-default-rtdb.asia-southeast1.firebasedatabase.app/'
        })
    except Exception as e:
        st.error(f"Cloud Connection Error: {e}")



# 3. HEADER & UI
st.header("Prof. Rajendra Singh (Rajju Bhaiya) University")
st.sidebar.markdown(f"**Last Cloud Sync:** `{time.strftime('%H:%M:%S')}`")
st.sidebar.caption("🔄 Auto-refreshing every 5 seconds")
if 'driver_state' not in st.session_state:
    st.session_state.driver_state = "Idle"
st.title("Driver Control Unit")

# --- DRIVER LOGIC ---
if st.session_state.driver_state == "Idle":
    if st.button("🔓 Unlock System", use_container_width=True):
        st.session_state.driver_state = "Armed"
        st.rerun()

elif st.session_state.driver_state == "Armed":
    st.warning("System Armed. Ready to Broadcast GPS?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Yes, GO LIVE", type="primary"):
            db.reference('system_status').update({
                'is_live': True,
                'stop_reason': "Driving now"
                })
            st.session_state.driver_state = "Live"
            st.rerun()
    with col2:
        if st.button("❌ CANCEL"):
            st.session_state.driver_state = "Idle"
            st.rerun()

elif st.session_state.driver_state == "Live":
    st.success("🛰️ BROADCASTING LIVE TO CAMPUS")
    
    # 1. Get Live GPS from the Driver's phone
    with st.container():
        driver_loc = get_geolocation(key="DRIVER_GPS")
    
    if driver_loc:
        curr_lat = driver_loc['coords']['latitude']
        curr_lon = driver_loc['coords']['longitude']
        
        # 2. Push to Firebase so students can see it
        db.reference('rickshaw_location').update({
            'lat': curr_lat,
            'lon': curr_lon,
            'last_updated': time.strftime("%H:%M:%S")
        })
        st.sidebar.caption(f"GPS Active: {curr_lat:.4f}, {curr_lon:.4f}")

    if st.button("🛑 STOP SHARING", type="secondary"):
        st.session_state.driver_state = "Stopping"
        st.rerun()
elif st.session_state.driver_state == "Stopping":
    st.subheader("Reason for stop")
    reason = st.selectbox("Choose Reason", ["I am on lunch break", "Ricksaw Battery is low", "I am unavailable", "Others"])
    if st.button("Confirm"):
        db.reference('system_status').update({
            'is_live': False,
            'stop_reason': reason
        })
        st.session_state.driver_state = "Idle" # Fixed: Use single = for assignment
        st.success(f"Stopped. Reason logged: {reason}")
        st.rerun()

# 4. MESSAGE RECEIVER (BOTTOM OF PAGE)
st.divider()
st.subheader("📍 Live Passenger Requests")
ref = db.reference('passenger_requests')
messages = ref.get()

if messages:
    last_msg_id = list(messages.keys())[-1]
    
    # Check for NEW messages only
    if "last_notified_id" not in st.session_state or st.session_state.last_notified_id != last_msg_id:
        # 1. Visual Toast
        st.toast(f"New Request: {messages[last_msg_id]['text']}", icon="🔔")
        
        # 2. Audio & Vibration Injection
        st.markdown(
            f"""
            <audio autoplay><source src="https://www.soundjay.com/buttons/sounds/beep-07a.mp3" type="audio/mpeg"></audio>
            <script>
                // Vibrates for 500ms when a new message arrives
                if (window.navigator && window.navigator.vibrate) {{
                    window.navigator.vibrate(500);
                }}
            </script>
            """,
            unsafe_allow_html=True
        )
        
        st.session_state.last_notified_id = last_msg_id 

    # 3. Display Messages
    for msg_id in reversed(list(messages.keys())):
        msg_data = messages[msg_id]
        sender_id = msg_data.get('user_id')
        
        with st.chat_message("user"):
            st.write(f"**Request:** {msg_data['text']}")
            
            # FIXED INDENTATION BELOW
            if st.button(f"🚫 Ban User", key=f"ban_btn_{msg_id}"):
                if sender_id:
                    db.reference(f'blacklist/{sender_id}').set(True)
                    st.toast(f"User {sender_id} Blacklisted!")
                    st.rerun()
            
            st.caption(f"Received at: {msg_data.get('timestamp', 'N/A')}")
    
    if st.button("🗑️ Clear All Requests"):
        ref.delete()
        if "last_notified_id" in st.session_state:
            del st.session_state.last_notified_id
        st.rerun()
else:
    st.info("No active requests from students.")



# --- ADMIN UNBAN SECTION ---
st.sidebar.divider()
st.sidebar.subheader("🛡️ Blacklist Management")

# 1. Fetch the list of banned IDs from the bridge
banned_ref = db.reference('blacklist')
banned_users = banned_ref.get()

if banned_users:
    # 2. Create a dropdown of all banned IDs
    user_to_unban = st.sidebar.selectbox("Select User to Unban", options=list(banned_users.keys()))
    
    if st.sidebar.button("🔓 Unban User"):
        # 3. Delete the specific user entry from the bridge
        db.reference(f'blacklist/{user_to_unban}').delete()
        st.sidebar.success(f"User {user_to_unban} is now unbanned!")
        time.sleep(1)
        st.rerun()
else:
    st.sidebar.info("The blacklist is currently empty.")

if st.session_state.driver_state == "Live":
    time.sleep(5)
    st.rerun()
else:
    if st.sidebar.button("🔄 Manual Sync"):
        st.rerun()
