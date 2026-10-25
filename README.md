# PeoplePulse - Workforce Attrition and Productivity Analytics

## Project Overview
PeoplePulse is an HR analytics dashboard designed to analyze workforce attrition, attendance, hiring effectiveness, employee productivity, and workforce planning.

## Technologies Used
- Python
- Streamlit
- Pandas
- MySQL
- SQL
- Plotly

## Dashboard Modules
1. Executive Overview
2. Attendance Analytics
3. Hiring Analytics
4. Productivity Analytics
5. Workforce Planning
6. Upload Dataset

## Key Features
- Employee headcount and attrition analysis
- Department and tenure-based attrition trends
- Attendance and absenteeism analysis
- Hiring source and recruitment analysis
- Employee productivity metrics
- Probation outcomes and workforce planning indicators
- CSV and Excel dataset upload

## Data Disclaimer
The employee attrition baseline uses the IBM HR Analytics dataset. Additional attendance, hiring, productivity, and workforce event records are simulated demonstration data. They are not verified records from a real company.

Rule-based attrition indicators are descriptive screening criteria, not predictions. Workforce forecasts and critical-role indicators require validation before operational use.

## Run Locally
1. Install Python.
2. Install dependencies:

   pip install -r requirements.txt

3. Start the dashboard:

   python -m streamlit run dashboard/app.py

## Privacy and Security
Do not publish database passwords, API keys, or secret configuration files. Configure credentials securely for any hosted deployment.

## Project Status
Developed as an HR analytics demonstration project.
