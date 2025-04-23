# Financial Reimbursement Claim Management System

This is a Django-based REST API for managing financial reimbursement claims for university societies.

## Virtual Environment Setup

### Activating the Virtual Environment in PowerShell

There are two ways to activate the virtual environment:

#### Option 1: Using the Batch File

Run the following command in Command Prompt:

```
activate_venv.bat
```

#### Option 2: Using the PowerShell Script

Run the following command in PowerShell:

```powershell
# You may need to set the execution policy first
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
# Then run the activation script
.\activate_venv.ps1
```

#### Option 3: Direct Activation in PowerShell

If you prefer to activate the environment directly in PowerShell:

```powershell
# Set execution policy if needed
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
# Activate the environment
.\.venv\Scripts\activate.ps1
```

> **Note:** Do not use `builtin source` command as it's not supported in PowerShell. This is a bash/shell command.

### Running the Django Server

Once the virtual environment is activated, you can run the Django server:

```
python manage.py runserver
```

## Project Structure

- **Frontend:** React JS (Single-Page Application)
- **Backend:** Django with Django REST Framework
- **Database:** SQLite
- **Authentication:** JWT (JSON Web Token) authentication with session authentication as fallback

## Core Functionality & User Roles

- **Users:** Society Members, Committee Members, SU Staff
- **Claims:** Multi-stage approval process
- **Societies:** Users belong to societies; claims are associated with societies
