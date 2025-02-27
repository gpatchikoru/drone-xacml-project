# FAA Drone Rules Evaluator

A comprehensive solution for evaluating drone operations against FAA regulations. This system uses a direct implementation approach to evaluate drone operations for compliance with FAA rules and generates detailed PDF reports.

## Table of Contents

1. [Project Overview](#project-overview)
2. [Environment Setup](#environment-setup)
3. [Project Structure](#project-structure)
4. [Implementation Details](#implementation-details)
5. [Usage Guide](#usage-guide)
6. [Output Explanation](#output-explanation)
7. [Future Enhancements](#future-enhancements)

## Project Overview

The FAA Drone Rules Evaluator is a web application that allows users to input drone operation parameters and evaluate compliance with FAA regulations. The system provides:

- A user-friendly web interface for entering drone operation details
- Real-time compliance evaluation against FAA rules
- Detailed explanations of any compliance violations
- PDF report generation for documentation and record-keeping

This project implements FAA drone regulations including:
- Altitude limits (400 feet)
- Remote ID requirements
- Visibility requirements (3 statute miles)
- Cloud distance requirements
- Airspace restrictions
- Night operation requirements
- Operating over people requirements

## Environment Setup

### Prerequisites

- Python 3.9+ 
- pip (Python package manager)
- macOS, Linux, or Windows

### Installation Steps

1. **Create a project directory**:
```bash
mkdir -p ~/drone-xacml-project
cd ~/drone-xacml-project
```

2. **Set up a Python virtual environment**:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install required packages**:
```bash
pip install flask reportlab lxml
```

4. **Create project structure**:
```bash
mkdir -p python
mkdir -p python/templates
mkdir -p policies
mkdir -p reports
```

## Project Structure

The project consists of the following key files:

### 1. `direct_faa_rules.py`

This file contains the core implementation of the FAA drone rules:

```bash
touch ~/drone-xacml-project/python/direct_faa_rules.py
```

Key components:
- `DroneOperation` dataclass: Represents a drone operation with all relevant attributes
- `FAADroneRulesEvaluator` class: Implements the rule evaluation logic
- Rule checks for altitude, visibility, remote ID, airspace, and more

### 2. `faa_rules_api.py`

The Flask web application that provides a user interface and API:

```bash
touch ~/drone-xacml-project/python/faa_rules_api.py
```

Key components:
- Web interface with forms for all drone operation parameters
- `/api/evaluate` endpoint for evaluating drone operations
- `/api/report` endpoint for generating PDF reports
- Logging and error handling

### 3. `templates/index.html`

The HTML form for the web interface (created automatically by the application):

Key components:
- Form sections for drone characteristics, operation details, environment, and pilot information
- JavaScript for submitting data and handling responses
- Styling for a professional appearance

### 4. Initial XACML Policy Files (Alternative Approach)

While the project ultimately used a direct implementation approach, we initially explored XACML:

```bash
touch ~/drone-xacml-project/policies/FAADroneRules.xml
```

This file contains XACML policies representing FAA drone rules.

## Implementation Details

### Direct Rules Implementation Approach

After experimenting with XACML for policy enforcement, we chose a direct implementation approach for several reasons:

1. **Simplicity**: The direct implementation is easier to understand and maintain
2. **Performance**: Direct rule checking is more efficient than XACML processing
3. **Flexibility**: Easier to modify and extend rules
4. **Fewer Dependencies**: No need for complex XACML processing engines

The implementation follows these steps:
1. Create a dataclass to represent drone operations
2. Implement rule checks directly in Python
3. Return detailed information about compliance status and violations
4. Generate PDF reports with ReportLab

### PDF Report Generation

The PDF report generation uses ReportLab to create professional reports including:

1. Report header with unique ID and timestamp
2. Compliance status (approved or denied)
3. Detailed tables for:
   - Drone characteristics
   - Operation details
   - Environment information
   - Pilot qualifications
4. Disclaimer for legal purposes

## Usage Guide

### Starting the Application

```bash
cd ~/drone-xacml-project/python
python faa_rules_api.py
```

The application will start on port 8080.

### Using the Web Interface

1. Open a web browser and navigate to `http://localhost:8080`
2. Fill out the drone operation form with all required parameters
3. Click "Evaluate Operation" to check compliance
4. View the results (approved or denied with details)
5. Click "Generate PDF Report" to create and download a PDF report

### API Usage

You can also use the API directly:

#### Evaluate Drone Operation

```bash
curl -X POST http://localhost:8080/api/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "drone_category": "Category2",
    "drone_weight": 1.5,
    "has_anti_collision_lighting": true,
    "has_remote_id": true,
    "time_of_day": "day",
    "operating_over_people": false,
    "operating_altitude": 200,
    "operating_speed": 35,
    "airspace_class": "G",
    "flight_visibility": 5,
    "distance_from_clouds_horizontal": 2500,
    "distance_from_clouds_vertical": 600
  }'
```

#### Generate PDF Report

```bash
curl -X POST http://localhost:8080/api/report \
  -H "Content-Type: application/json" \
  -d '{
    "drone_category": "Category2",
    "drone_weight": 1.5,
    "has_anti_collision_lighting": true,
    "has_remote_id": true,
    "time_of_day": "day",
    "operating_over_people": false,
    "operating_altitude": 200,
    "operating_speed": 35,
    "airspace_class": "G",
    "flight_visibility": 5,
    "distance_from_clouds_horizontal": 2500,
    "distance_from_clouds_vertical": 600
  }' \
  --output drone_compliance_report.pdf
```

## Output Explanation

### Compliance Check Results

The system evaluates drone operations against FAA rules and returns:

1. **Status**: `APPROVED` or `DENIED`
2. **Details**: 
   - For approved operations: "Operation complies with FAA regulations"
   - For denied operations: List of specific rule violations

Example output for a non-compliant operation:
```
Status: DENIED

Details:
- Altitude exceeds 400 feet limit (current: 600 feet)
- Visibility below 3 statute miles (current: 2 miles)
- Drone lacks required Remote ID capability
```

### PDF Report

The generated PDF report includes:

1. **Header**: Report ID and generation timestamp
2. **Compliance Status**: Highlighted in green (approved) or red (denied)
3. **Operation Details**: Tables with all operation parameters
4. **Violation Details**: For denied operations, explanations of all rule violations
5. **Disclaimer**: Legal statement about the informational nature of the report

## Future Enhancements

Potential improvements to the system:

1. **Authentication**: Add user authentication for security
2. **Database Integration**: Store evaluation history
3. **Map Integration**: Visual representation of operation area
4. **Extended Rules**: Add more detailed FAA regulations
5. **API Documentation**: Interactive API documentation with Swagger
6. **Containerization**: Package as Docker container for easy deployment

---

This project provides a comprehensive solution for evaluating drone operations against FAA regulations, with both a user-friendly web interface and a programmable API.