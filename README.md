# CYSCOM Vulnerable Web Application 

## Setup Instructions

1. use virtual environment:
```b
python -m venv venv
venv/bin/activate 
```

2. Install dependencies:
```
pip install -r requirements.txt
```

3. Run the application:
```
python app.py
```

The application will be available at `http://localhost:5000`



# CYSCOM JUICE SHOP WALKTHROUGH

The CYSCOM JUICE SHOP, like OSWAP Juice Shop,includes a broad spectrum of vulnerabilities from simple input-based flaws to logic and design-level flaws. Understanding the rationale behind each exploit reinforces the importance of layered security, input validation, and robust authentication design.
This document provides a detailed analysis of each challenge presented in the CYSCOM Juice Shop Challenge. Each vulnerability is explained alongside its exploitation method and the flag retrieval steps.

## TASK 1: MAIN FLAGS

### Initial Login Page & SQL Injection
<img src="./imagedata/Picture1.png"  width=600 height=300> 
The login form is susceptible to SQL Injection, allowing attackers to bypass authentication without knowing valid credentials. This is due to improperly sanitized user inputs in SQL queries.

Examples of payloads:
```
admin' –
admin';--
admin' /*
' UNION SELECT 1,2,3,1,'admin
```

Entering these in the username followed by any password lets the user login as admin.

> [!NOTE]
> OR-based injections are filtered, requiring alternative payloads.


### Admin Panel Disclosure

The /admin endpoint, typically hidden, becomes accessible post-SQL injection login. This panel leaks usernames and passwords of all registered users, indicating a Sensitive Data Exposure vulnerability.

<img src="./misc/autotab.png"  width=600 height=300> 

Flag Retrieval: Visiting this hidden endpoint grant the user a flag. 


The leaked credentials can be used to authenticate normally to ‘admin’ user and retrieve the corresponding flag. 
