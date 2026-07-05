@echo off
REM =================================================
REM  CampusVote - one-time setup
REM  1) Installs Python dependencies
REM  2) Creates the MySQL database (asks for password)
REM =================================================
cd /d "%~dp0"

echo Installing Python dependencies...
python -m pip install -r requirements.txt

echo.
echo Creating the MySQL database (you will be asked for your MySQL root password)...
mysql -u root -p < schema.sql

echo.
echo Setup complete! Now run the app with run.bat
pause
