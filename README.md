# TimeTracker App

The **TimeTracker App** is a simple web-based tool designed to help users track their working hours by clocking in and clocking out. It also allows users to view their hours worked over specific time periods (week, pay period, or month), and offers functionality for user creation and deletion. It’s built with **FastAPI** for the backend and **Alpine.js** for the frontend, supporting dark mode and responsive design.

## Features

- **User Creation**: If a user does not exist, a modal prompts to create a new user.
- **Clock In/Out**: Users can clock in and out with a simple button click, and their time entries are recorded.
- **View Time Data**: Users can view their time data by week, pay period, or month.
- **Delete Entries**: Users can delete today's clock-in and clock-out entry.
- **Dark Mode**: Toggle dark mode for better readability in low light conditions.
- **Export Data**: Users can export their time entries in CSV format.
- **Admin Panel**: Admin functionality to manage users and view their time entries.

## Technologies

- **Backend**: [FastAPI](https://fastapi.tiangolo.com/)
- **Frontend**: [Alpine.js](https://alpinejs.dev/), HTML5, CSS3
- **Database**: SQLite (via SQLAlchemy ORM)
- **Styling**: Custom styles with support for dark mode
- **Deployment**: Docker

## Getting Started

### Prerequisites

Make sure you have the following tools installed on your system:

- **Python 3.12+**
- **FastAPI** and its dependencies (`SQLAlchemy`, `bcrypt`, etc.)
- **Docker** (for containerization, optional)

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/your-repo/timetracker.git
   cd timetracker
2.	Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3.	Set up environment variables for the admin user:
    Create a .env file in the root of the project and define the following variables:
    ```
    ADMIN_USERNAME=admin
    ADMIN_PASSWORD=your_password_here
    ```

## Running the Application

1.	Run the FastAPI server:
    ```bash
    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
    ```
    The app will be accessible at `http://localhost:8000`.

2.	Open the frontend by navigating to `http://localhost:8000` in your browser.

## Using Docker (Optional)

You can also run the app in a Docker container. Follow these steps:

1.	Build the Docker image:
    ```bash
    docker build -t timetracker .
    ```
2.	Run the Docker container:
    ```bash
    docker run -p 8000:8000 timetracker
    ```

## Endpoints

- `/`: Main web interface.
- `/edit`: Interface to Edit Times.
- `/docs`: Docs page.

- `/user/create (POST)`: Create a new user.
- `/user/status/{user} (GET)`: Check the user’s current status (clocked in/out).
- `/time/{user}/in (POST)`: Clock in the user.
- `/time/{user}/out (POST)`: Clock out the user.
- `/time/{user}/recall/{period} (GET)`: Get time data for a specific period (week, pay period, or month).
- `/time/{user}/today (DELETE)`: Delete today’s clock-in and clock-out times.

## Frontend Functionality

- **Dark Mode Toggle**: Click the Toggle Dark Mode button to switch between light and dark modes.
- **Clock In/Out**: Click the Clock In or Clock Out button to record your time.
- **User Creation**: If the user doesn’t exist, you’ll be prompted with a modal to create a new user.
- **View Time Data**: Use the Week, Payperiod, and Month buttons to fetch your time data.
- **Export Data**: Export time entries to CSV by clicking the Export Data button.

## Acknowledgements

- Built using FastAPI for the backend.
- Alpine.js for a lightweight frontend framework.