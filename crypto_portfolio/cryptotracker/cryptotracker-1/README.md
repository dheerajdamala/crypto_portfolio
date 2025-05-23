# README for Crypto Tracker

## Overview
Crypto Tracker is a Django-based web application designed to help users track their cryptocurrency portfolio. The application provides features to monitor prices, manage assets, and analyze performance over time.

## Installation Instructions

1. **Clone the repository:**
   ```
   git clone <repository-url>
   cd cryptotracker
   ```

2. **Set up a virtual environment:**
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install the required packages:**
   ```
   pip install -r requirements.txt
   ```

4. **Configure the database:**
   Update the database settings in `cryptotracker/settings.py` as needed.

5. **Run migrations:**
   ```
   python manage.py migrate
   ```

6. **Start the development server:**
   ```
   python manage.py runserver
   ```

## Usage Guidelines
- Access the application in your web browser at `http://127.0.0.1:8000/`.
- Follow the on-screen instructions to create an account and start tracking your cryptocurrencies.

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.