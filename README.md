NeuroScan 🚧

AI-powered infrastructure issue detection system using YOLOv8, FastAPI, and Computer Vision.

📌 Overview

NeuroScan is a smart web application that detects and classifies real-world infrastructure issues such as:

Potholes
Open manholes
Garbage accumulation
Damaged road elements

The system uses a YOLOv8 object detection model to process uploaded images or live camera feeds in real time. Detected issues are stored through a FastAPI backend for tracking and analysis.

Built with a responsive and mobile-friendly interface, NeuroScan aims to support smarter urban maintenance and automated infrastructure monitoring.

✨ Features
🔍 Real-time object detection using YOLOv8
📷 Image upload and live camera support
⚡ FastAPI-powered backend
📱 Mobile-friendly interface
🧠 Machine Learning + Computer Vision integration
🗂️ Detection storage for analysis and tracking
🚀 Lightweight and scalable architecture
🛠️ Tech Stack
Frontend
HTML
CSS
JavaScript
Backend
Python
FastAPI
Machine Learning & Computer Vision
YOLOv8
OpenCV
Other Tools
Data Collection & Annotation
REST APIs
📂 Project Structure
NeuroScan/
│
├── backend/
│   ├── main.py
│   ├── routes/
│   ├── models/
│   └── utils/
│
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
│
├── model/
│   └── yolov8_weights.pt
│
├── dataset/
├── requirements.txt
└── README.md
⚙️ Installation
1️⃣ Clone the Repository
git clone https://github.com/PrajHacks/NeuroScan.git
cd NeuroScan
2️⃣ Create Virtual Environment
python -m venv venv
Activate Environment
Windows
venv\Scripts\activate
Linux / macOS
source venv/bin/activate
3️⃣ Install Dependencies
pip install -r requirements.txt
▶️ Run the Project
Start FastAPI Server
uvicorn main:app --reload

Server will run at:

http://127.0.0.1:8000
🔄 Workflow
User uploads image or starts live camera
YOLOv8 processes the frame
Infrastructure issues are detected
Results are displayed in real time
Detected data is stored for tracking and analysis
🎯 Use Cases
Smart city monitoring
Road safety management
Municipal infrastructure maintenance
Automated public issue reporting
Urban analytics systems
🚀 Future Improvements
📍 GPS-based issue mapping
📊 Analytics dashboard
☁️ Cloud deployment
📱 Dedicated mobile app
🔔 Real-time alert system
🌐 Multi-language support
👥 Team

Team Size: 2

Developers
Prajwal
📅 Duration

January 2026 – February 2026

🔗 Project Link

NeuroScan GitHub Repository

📄 License

This project is licensed under the MIT License
