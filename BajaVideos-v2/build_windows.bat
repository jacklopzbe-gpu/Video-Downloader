@echo off
REM Compilar BajaVideos.exe en Windows (alternativa a GitHub Actions).
cd /d "%~dp0"

python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller

pyinstaller --noconfirm --onefile --windowed --name "BajaVideos" --icon assets\icon.ico --collect-all customtkinter --collect-all imageio_ffmpeg --collect-all yt_dlp --collect-all telegram app.py

echo.
echo Listo: dist\BajaVideos.exe
pause
