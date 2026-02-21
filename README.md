# Retail Store Project

## Prerequisites

- Python 3.11+
- Node.js 18+
- Redis server (for Dramatiq background tasks)
- pip (Python package manager)
- npm (Node package manager)

## Backend Setup (Django)

1. **Create and activate a virtual environment:**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

2. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

3. **Apply migrations:**
   ```powershell
   python manage.py makemigrations
   python manage.py migrate
   ```

4. **Start the development server:**
   ```powershell
   python manage.py runserver
   ```

5. **Start Dramatiq worker (for background tasks):**
   Ensure Redis is running, then:
   ```powershell
   python manage.py dramatiq
   ```

## Frontend Setup (Angular)

1. **Navigate to the frontend directory:**
   ```powershell
   cd frontend/retail-ui
   ```

2. **Install dependencies:**
   ```powershell
   npm install
   ```

3. **Start the Angular development server:**
   ```powershell
   npm start
   ```

## Additional Notes

- The backend API runs at `http://localhost:8000/` by default.
- The Angular frontend runs at `http://localhost:4200/` by default.
- Dramatiq requires Redis. Download and run Redis from https://redis.io/download if not already installed.
- For CSV uploads and background processing, ensure Dramatiq worker is running.

For further details, see the `docs/` folder.

