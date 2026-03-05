# 🔐 Phishing Simulation & Credential Analysis Platform

![Python](https://img.shields.io/badge/Python-3.10-blue)
![Flask](https://img.shields.io/badge/Framework-Flask-black)
![Database](https://img.shields.io/badge/Database-SQLite-green)
![Status](https://img.shields.io/badge/Project-Educational-orange)

---

## 📌 Project Overview

This project is a **Phishing Simulation Platform** developed using **Python Flask**.
It simulates a login environment to demonstrate how phishing attacks can capture user interaction data.

The system collects and analyzes:

* login credentials
* user device information
* IP addresses
* browser and OS
* interaction time

All captured information is displayed in a **real-time monitoring dashboard**.

This project was developed for **cybersecurity awareness and educational purposes**.

---

## 🧠 Key Features

✔ Realistic Google-style login page
✔ Email or phone validation
✔ Credential capture simulation
✔ User device detection
✔ Browser & OS identification
✔ IP tracking
✔ Time spent on page tracking
✔ Live dashboard monitoring
✔ JSON API for collected data

---

## 🖥 Dashboard Preview

The dashboard displays captured information including:

* Username / Email
* Password
* IP Address
* Operating System
* Browser
* Time spent
* Timestamp

Example dashboard endpoint:

http://127.0.0.1:5000/results

---

## 🏗 Project Architecture

project/
│
├── app.py                # Main Flask application
├── database.db           # SQLite database
│
├── templates/
│   ├── login_email.html
│   ├── login_password.html
│   └── results.html
│
├── requirements.txt
├── .gitignore
└── README.md

---

## ⚙ Installation

### 1️⃣ Clone Repository

git clone https://github.com/YOUR_USERNAME/phishing-simulation.git
cd phishing-simulation

---

### 2️⃣ Install Dependencies

pip install flask user-agents

---

### 3️⃣ Run the Application

python app.py

Server will start on:

http://127.0.0.1:5000

---

## 📊 Monitoring Dashboard

Open:

http://127.0.0.1:5000/results

The dashboard displays:

| Data       | Description            |
| ---------- | ---------------------- |
| Username   | Email or phone entered |
| Password   | Submitted password     |
| IP Address | User network address   |
| Device     | Mobile or Desktop      |
| Browser    | User browser           |
| Time Spent | Time on page           |
| Timestamp  | Login attempt time     |

---

## 🔗 API Endpoint

The system provides a JSON API for data extraction:

/data/json

Example output:

{
"rows": [...],
"stats": {...},
"current_time": "2026-03-05T21:30:00"
}

---

## 🎓 Educational Purpose

This project was created **strictly for educational and cybersecurity training purposes**.

It demonstrates:

* phishing techniques
* credential harvesting
* user behavior analysis
* cybersecurity awareness

⚠ Do not use this project for illegal activities.

---

## 👨‍💻 Authors

Abdulhaq Hussain Ali
Aya Ali Mustafa
Ali Bashar Muhammad

---

## 📜 License

This project is provided for **educational and research purposes only**.

---

## ⭐ Support

If you found this project helpful, consider giving it a ⭐ on GitHub.
