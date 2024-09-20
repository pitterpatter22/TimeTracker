import requests
import random
from datetime import datetime, timedelta

# API configuration
#API_URL = "http://localhost:8000"
API_URL = "https://time-api.smithserver.app"

TEST_USER = "testuser"
#PASSWORD = "password123"  # If the user creation requires a password

# Generate random clock-in and clock-out times
def generate_random_time(date):
    # Random clock-in time between 8 AM and 10 AM
    clock_in_hour = random.randint(8, 10)
    clock_in_minute = random.randint(0, 59)
    clock_in_time = date.replace(hour=clock_in_hour, minute=clock_in_minute, second=0)

    # Random clock-out time between 4 PM and 6 PM
    clock_out_hour = random.randint(16, 18)
    clock_out_minute = random.randint(0, 59)
    clock_out_time = date.replace(hour=clock_out_hour, minute=clock_out_minute, second=0)

    return clock_in_time, clock_out_time

# Create a new user
def create_user():
    url = f"{API_URL}/user/create"
    data = {
        "name": TEST_USER,
        #"password": PASSWORD  # If the API requires a password for user creation
    }
    response = requests.post(url, json=data, verify=False)  # Disable TLS verification
    if response.status_code == 200:
        print(f"User '{TEST_USER}' created successfully.")
    elif response.status_code == 400 and 'already exists' in response.text:
        print(f"User '{TEST_USER}' already exists.")
    else:
        print(f"Error creating user: {response.status_code} - {response.text}")
        return False
    return True

# Clock in and clock out using the API
def clock_in_out(date, clock_in_time, clock_out_time):
    # Format times for API
    clock_in_url = f"{API_URL}/time/{TEST_USER}/in"
    clock_out_url = f"{API_URL}/time/{TEST_USER}/out"

    # Perform clock-in
    clock_in_response = requests.post(clock_in_url, params={
        "note": f"Clocked in at {clock_in_time.strftime('%Y-%m-%d %H:%M:%S')}",
        "clock_in_time": clock_in_time.isoformat()
    }, verify=False)  # Disable TLS verification
    if clock_in_response.status_code != 200:
        print(f"Error clocking in for {clock_in_time.date()}: {clock_in_response.status_code} - {clock_in_response.text}")
        return

    # Perform clock-out
    clock_out_response = requests.post(clock_out_url, params={
        "note": f"Clocked out at {clock_out_time.strftime('%Y-%m-%d %H:%M:%S')}",
        "clock_out_time": clock_out_time.isoformat()
    }, verify=False)  # Disable TLS verification
    if clock_out_response.status_code != 200:
        print(f"Error clocking out for {clock_out_time.date()}: {clock_out_response.status_code} - {clock_out_response.text}")
        return

    print(f"Successfully clocked in and out for {clock_in_time.date()}.")

# Main function to create user and generate data
def main():
    if not create_user():
        return

    # Generate data for the past 45 days
    for i in range(45):
        date = datetime.now() - timedelta(days=i)
        clock_in_time, clock_out_time = generate_random_time(date)

        # Perform clock-in and clock-out operations
        clock_in_out(date, clock_in_time, clock_out_time)

if __name__ == "__main__":
    main()