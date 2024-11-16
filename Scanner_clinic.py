import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import os

# Files to store appointments and cancellation requests
APPOINTMENTS_FILE = "appointments.csv"
CANCELLATION_REQUESTS_FILE = "cancellation_requests.csv"
admin_password = "nlheesahh"  # Admin password

# Function to load appointments from a CSV file
def load_appointments():
    if os.path.exists(APPOINTMENTS_FILE):
        date_parser = lambda x: pd.to_datetime(x, errors='coerce')
        df = pd.read_csv(APPOINTMENTS_FILE, parse_dates=['datetime'], date_parser=date_parser)
        df = df.dropna(subset=['datetime'])  # Remove rows with invalid/missing dates
        return df
    return pd.DataFrame(columns=['day', 'datetime', 'name', 'contact'])


# Initialize appointment data if not in session state
if 'appointments_df' not in st.session_state:
    st.session_state.appointments_df = load_appointments()
    if st.session_state.appointments_df.empty:
        st.session_state.appointments_df = pd.DataFrame(columns=['day', 'datetime', 'name', 'contact'])

# Initialize cancellation requests if not in session state
if 'cancellation_requests' not in st.session_state:
    st.session_state.cancellation_requests = []

# Ensure 'datetime' column is of datetime type
if 'datetime' in st.session_state.appointments_df.columns:
    st.session_state.appointments_df['datetime'] = pd.to_datetime(st.session_state.appointments_df['datetime'], errors='coerce')

# Function to save appointments to a CSV file
def save_appointments(df):
    try:
        df.to_csv(APPOINTMENTS_FILE, index=False)
        st.success(f"Appointments saved successfully to {APPOINTMENTS_FILE}.")
    except Exception as e:
        st.error(f"Error saving appointments: {e}")

def add_appointment(new_appointment):
    df = st.session_state.appointments_df
    df = df.append(new_appointment, ignore_index=True)
    save_appointments(df)  # Save to the correct path
    st.session_state.appointments_df = df  # Update the session state

# Function to load cancellation requests from a CSV file
def load_cancellation_requests():
    if os.path.exists(CANCELLATION_REQUESTS_FILE):
        return pd.read_csv(CANCELLATION_REQUESTS_FILE).values.flatten().tolist()
    return []

# Function to save cancellation requests to a CSV file
def save_cancellation_requests(requests):
    pd.Series(requests).to_csv(CANCELLATION_REQUESTS_FILE, index=False)

# Function to get available slots
def get_available_slots(day, date):
    slots = []
    if day == 'Tuesday':
        start_time = datetime(date.year, date.month, date.day, 9)
    else:  # Thursday
        if (date.isocalendar()[1] % 2) == 0:  # Even week
            start_time = datetime(date.year, date.month, date.day, 11)
        else:  # Odd week
            start_time = datetime(date.year, date.month, date.day, 9)

    for i in range(2):  # Maximum 2 patients
        slot_time = start_time + timedelta(minutes=30 * i)
        slots.append(slot_time)

    # Filter out occupied slots
    occupied_slots = st.session_state.appointments_df[
        (st.session_state.appointments_df['day'] == day) & 
        (st.session_state.appointments_df['datetime'].dt.date == date)
    ].datetime

    available_slots = [slot for slot in slots if slot not in occupied_slots.values]
    return available_slots


# Streamlit app layout
st.title("Welcome to Intraoral Scanner Reservation System")

# Show current appointments on app start
st.header("Current Appointments:")
for day in ['Tuesday', 'Thursday']:
    day_appointments = st.session_state.appointments_df[st.session_state.appointments_df['day'] == day]
    if not day_appointments.empty:
        st.write(f"**{day}:**")
        for _, row in day_appointments.iterrows():
            st.write(f"- {row['datetime'].strftime('%Y-%m-%d')} at {row['datetime'].strftime('%H:%M')} (Name: {row['name']}, Contact: {row['contact']})")
    else:
        st.write(f"**{day}:** No appointments reserved.")

# User input for admin access
is_admin = st.checkbox("Admin Access")
if is_admin:
    password = st.text_input("Enter admin password:", type="password")

if is_admin and password == admin_password:
    st.header("Admin Panel")
    
    # Show cancellation requests
    st.write("### Cancellation Requests:")
    if isinstance(st.session_state.cancellation_requests, list):
        if st.session_state.cancellation_requests:
            for idx, request in enumerate(st.session_state.cancellation_requests):
                st.write(f"{idx + 1}. {request} ")
                if st.button(f"Delete Request {idx + 1}", key=f"delete_request_{idx}"):
                    st.session_state.cancellation_requests.pop(idx)
                    save_cancellation_requests(st.session_state.cancellation_requests)
                    st.success("Cancellation request deleted.")
                    st.stop()  # Stop to refresh the state
        else:
            st.write("No cancellation requests.")
    else:
        st.error("Cancellation requests are not in the expected format.")

    # Remove appointment section
    st.write("### Remove Appointment")
    remove_date = st.date_input("Select a date to remove appointment:", datetime.now())
    remove_day = remove_date.strftime("%A")
    
    if remove_day in ['Tuesday', 'Thursday']:
        available_slots = get_available_slots(remove_day, remove_date)
        remove_slot = st.selectbox("Select a slot to remove:", options=[
            f"{time.strftime('%H:%M')}" for time in available_slots
        ])

        if st.button("Remove Appointment"):
            # Convert the selected slot into a datetime object
            selected_datetime = None
            for slot in available_slots:
                if slot.strftime('%H:%M') == remove_slot:
                    selected_datetime = slot
                    break
            if selected_datetime:
                row_to_remove = st.session_state.appointments_df[
                 (st.session_state.appointments_df['day'] == remove_day) & 
                 (st.session_state.appointments_df['datetime'] == selected_datetime) 
                ]
                if not row_to_remove.empty:
                    st.session_state.appointments_df = st.session_state.appointments_df.drop(row_to_remove.index)
                    save_appointments(st.session_state.appointments_df)
                    st.success(f"Removed appointment on {remove_day} at {remove_slot}.")
                else:
                    st.error("No such appointment found.")

else:
    # Public section for making reservations
    selected_date = st.date_input("Select a date", datetime.now())
    day_of_week = selected_date.strftime("%A")

    if day_of_week in ['Tuesday', 'Thursday']:
        available_slots = get_available_slots(day_of_week, selected_date)

        # Check if the maximum number of appointments is reached
        if len(st.session_state.appointments_df[
            (st.session_state.appointments_df['day'] == day_of_week) & 
            (st.session_state.appointments_df['datetime'].dt.date == selected_date)]) >= 2:
            st.warning("Maximum number of appointments reached for this day.")
        else:
            if available_slots:
                st.write(f"Available slots for {day_of_week}, {selected_date}:")
                slot_times = [slot.strftime('%H:%M') for slot in available_slots]

                for idx, slot in enumerate(slot_times):
                    st.write(f"{idx + 1}. {slot}")  # Display slot numbers starting from 1

                # User input for reservation
                name = st.text_input("Enter your name:")
                contact = st.text_input("Enter your contact number:")

                # Appointment selection with index starting from 1
                selected_index = st.selectbox("Select a time to reserve:", options=range(1, len(slot_times) + 1))

                # Reserve the appointment
                if st.button("Reserve Appointment"):
                    if name and contact:
                        selected_time = available_slots[selected_index - 1]  # Adjust for 0-indexing
                        
                        # Check if the selected time is already booked
                        existing_appointment = st.session_state.appointments_df[
                            (st.session_state.appointments_df['day'] == day_of_week) &
                            (st.session_state.appointments_df['datetime'] == selected_time)
                        ]
                        
                        if existing_appointment.empty:
                            # Save the appointment
                            new_appointment = pd.DataFrame({
                                'day': [day_of_week],
                                'datetime': [selected_time],
                                'name': [name],
                                'contact': [contact]
                            })
                            st.session_state.appointments_df = pd.concat([st.session_state.appointments_df, new_appointment], ignore_index=True)
                            save_appointments(st.session_state.appointments_df)

                            st.success(f"Appointment reserved for {name} on {selected_date.strftime('%Y-%m-%d')} at {selected_time.strftime('%H:%M')}.")
                        else:
                            st.error("This time slot is already reserved. Please select another.")
                    else:
                        st.error("Please enter both your name and contact number.")
            else:
                st.warning(f"No available slots on {day_of_week}, {selected_date}.")
    else:
        st.warning("The clinic is open only on Tuesdays and Thursdays.")

    # Cancellation request from users
    st.header("Cancellation Request")
    cancellation_message = st.text_area("Please enter your cancellation message (please add your name and your contact number and any other comments):")
    if st.button("Send Cancellation Request"):
        if cancellation_message:
            st.session_state.cancellation_requests.append(cancellation_message)
            save_cancellation_requests(st.session_state.cancellation_requests)  # Save to file
            st.success("Your cancellation request has been sent.")
        else:
            st.error("Please enter a valid message to send.")

