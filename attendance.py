# Reload the original CSV again to create June 2025 version
import pandas as pd

df_june = pd.read_csv("/Users/chiragkhanduja/PycharmProjects/PythonProject11/Attendance Logs.xlsx - Attendance Logs.csv")

# Convert AttendanceDate, In DateTime, Out DateTime to datetime and shift them by 6 months (Dec 2024 -> June 2025)
df_june['AttendanceDate'] = pd.to_datetime(df_june['AttendanceDate'], format='%d-%m-%Y', errors='coerce')
df_june['In DateTime'] = pd.to_datetime(df_june['In DateTime'], errors='coerce')
df_june['Out DateTime'] = pd.to_datetime(df_june['Out DateTime'], errors='coerce')

# Shift dates by 6 months
df_june['AttendanceDate'] = df_june['AttendanceDate'] + pd.DateOffset(months=7)
df_june['In DateTime'] = df_june['In DateTime'] + pd.DateOffset(months=7)
df_june['Out DateTime'] = df_june['Out DateTime'] + pd.DateOffset(months=7)

# PunchRecords remains same since it doesn't have full dates
df_june['PunchRecords'] = df_june['PunchRecords']

# Reformat AttendanceDate as original format (dd-mm-yyyy)
df_june['AttendanceDate'] = df_june['AttendanceDate'].dt.strftime('%d-%m-%Y')

# Reformat In DateTime & Out DateTime
df_june['In DateTime'] = df_june['In DateTime'].dt.strftime('%Y-%m-%d %H:%M')
df_june['Out DateTime'] = df_june['Out DateTime'].dt.strftime('%Y-%m-%d %H:%M')

# Save updated CSV for June 2025
output_path_june = "/Users/chiragkhanduja/PycharmProjects/PythonProject11/Attendance_Logs_July2025.csv"
df_june.to_csv(output_path_june, index=False)

print(f"File saved at: {output_path_june}")

