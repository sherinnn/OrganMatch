![Screenshot](https://github.com/sherinnn/OrganMatch/blob/main/organmatch_architecture_diagram.png)

# 🫀 OrganMatch – End-to-End Organ Donation and Logistics Platform

**OrganMatch** is an AI-driven organ donation and logistics portal that automates the entire organ transplantation workflow — from donor registration and viability analysis to donor-recipient matching and transport optimization.  

Developed as part of the **AWS Global AI Agent Hackathon**, it leverages **Amazon Bedrock**, **Lambda**, and **DynamoDB** to power real-time decision-making through intelligent agent-based orchestration.

---

## 🧠 Problem Statement

Organ transplantation is a race against time.  
Manual coordination between donors, recipients, and hospitals often leads to inefficiencies, miscommunication, and organ loss due to delayed logistics.

---

## 💡 Proposed Solution

OrganMatch introduces an **AI-powered intelligent agent** that:
- Analyzes **medical and logistical data** to match donors and recipients in real time.
- Automates **organ viability assessment** using clinical and environmental metrics.
- Optimizes **transportation routes** with weather and flight data integration.
- Provides an **AI conversational assistant** for instant decision support.

---

## 🎯 Objectives

- ✅ Create a unified organ donation portal connecting donors, recipients, and hospitals.  
- ✅ Ensure ethical and equitable distribution using transparent AI scoring.  
- ✅ Automate transport planning using real-time APIs and weather safety checks.  
- ✅ Enable voice/text-based AI assistance for clinicians and coordinators.

---

## ⚙️ System Architecture

### High-Level Overview
OrganMatch is built using a **modular, cloud-native architecture** with serverless Lambda tools connected through **Bedrock AgentCore Gateway**.

<p align="center">
  <img src="Blank diagram.png" alt="OrganMatch System Architecture" width="800"/>
</p>

<p align="center">
  <img src="fallback.png" alt="Bedrock AgentCore Gateway Architecture" width="800"/>
</p>

---

## 🧩 Key Features

| Feature | Description |
|----------|-------------|
| 🧬 **Organ Viability Assessment** | Evaluates organ health using a dynamic viability score (temperature, time, condition). |
| 🤝 **Donor–Recipient Matching** | Calculates compatibility using blood type, HLA typing, urgency, and proximity. |
| ✈️ **Transport Optimization** | Uses mock flight data (S3) + WeatherAPI to find shortest and safest delivery routes. |
| 💬 **AI Conversational Assistant** | Powered by Claude 3 Haiku (AWS Bedrock) for natural-language decision queries. |
| 🔐 **Secure Data Management** | Implements Secrets Manager and IAM roles for data and API key protection. |

---

## 🧱 Tech Stack

### 🧩 Core Technologies
- **Frontend:** Flask (Jinja templates, HTML/CSS, JavaScript)
- **Backend:** Python Flask REST API with AWS Bedrock Agent Runtime
- **Database:** DynamoDB (Donors, Recipients, Hospitals)
- **Storage:** Amazon S3 (Mock flight data)
- **Auth & Config:** AWS Cognito, Secrets Manager
- **Observability:** CloudWatch
- **AI Model:** Claude 3 Haiku (Amazon Bedrock)

### 🧠 AI Agent Components
| Lambda Tool | Function |
|--------------|-----------|
| `viability_tool()` | Computes organ viability score |
| `matcher_tool()` | Matches donor–recipient pairs |
| `flight_tool()` | Fetches and filters flights from S3 |
| `weather_tool()` | Retrieves weather data via WeatherAPI |

---

## 🚀 Setup Instructions

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/<your-username>/OrganMatch.git
cd OrganMatch
