@echo off
REM ============================================
REM  CampusVote - Online Voting System launcher
REM  Just double-click this file to start the app
REM ============================================
cd /d "%~dp0"
echo Starting CampusVote...
python -m streamlit run online_voting_system.py
pause
