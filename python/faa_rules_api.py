from flask import Flask, request, jsonify, render_template, send_file
from direct_faa_rules import DroneOperation, FAADroneRulesEvaluator
import json
import logging
import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
from io import BytesIO
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("faa_rules_api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("faa-rules-api")

app = Flask(__name__)
evaluator = FAADroneRulesEvaluator()

# Create templates directory if it doesn't exist
os.makedirs('templates', exist_ok=True)

# Create reports directory if it doesn't exist
os.makedirs('reports', exist_ok=True)

# Create a simple HTML form for the web interface
with open('templates/index.html', 'w') as f:
    f.write("""<!DOCTYPE html>
<html>
<head>
    <title>FAA Drone Rules Evaluator</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input, select { width: 100%; padding: 8px; box-sizing: border-box; }
        button { background-color: #4CAF50; color: white; padding: 10px 15px; border: none; cursor: pointer; }
        .result { margin-top: 20px; border: 1px solid #ddd; padding: 15px; border-radius: 5px; }
        .approved { background-color: #dff0d8; border-color: #d6e9c6; }
        .denied { background-color: #f2dede; border-color: #ebccd1; }
        .section { border-bottom: 1px solid #eee; padding-bottom: 10px; margin-bottom: 20px; }
        h3 { margin-top: 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>FAA Drone Rules Evaluator</h1>
        <p>Enter your drone operation details below to check compliance with FAA regulations.</p>
        
        <form id="droneForm">
            <div class="section">
                <h3>Drone Characteristics</h3>
                <div class="form-group">
                    <label for="drone_category">Drone Category:</label>
                    <select id="drone_category" name="drone_category">
                        <option value="Category1">Category 1 (less than 0.55 lbs)</option>
                        <option value="Category2" selected>Category 2 (less than 11ft-lbs kinetic energy)</option>
                        <option value="Category3">Category 3 (restricted areas only)</option>
                        <option value="Category4">Category 4 (requires airworthiness certificate)</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="drone_weight">Weight (pounds):</label>
                    <input type="number" id="drone_weight" name="drone_weight" value="1.5" step="0.1" min="0">
                </div>
                <div class="form-group">
                    <label for="has_anti_collision_lighting">Has Anti-Collision Lighting:</label>
                    <select id="has_anti_collision_lighting" name="has_anti_collision_lighting">
                        <option value="true" selected>Yes</option>
                        <option value="false">No</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="has_remote_id">Has Remote ID:</label>
                    <select id="has_remote_id" name="has_remote_id">
                        <option value="true" selected>Yes</option>
                        <option value="false">No</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="has_airworthiness_certificate">Has Airworthiness Certificate:</label>
                    <select id="has_airworthiness_certificate" name="has_airworthiness_certificate">
                        <option value="false" selected>No</option>
                        <option value="true">Yes</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="complies_with_kinetic_energy_limit">Complies with Kinetic Energy Limit:</label>
                    <select id="complies_with_kinetic_energy_limit" name="complies_with_kinetic_energy_limit">
                        <option value="true" selected>Yes</option>
                        <option value="false">No</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="has_exposed_rotating_parts">Has Exposed Rotating Parts:</label>
                    <select id="has_exposed_rotating_parts" name="has_exposed_rotating_parts">
                        <option value="false" selected>No</option>
                        <option value="true">Yes</option>
                    </select>
                </div>
            </div>
            
            <div class="section">
                <h3>Operation Details</h3>
                <div class="form-group">
                    <label for="time_of_day">Time of Day:</label>
                    <select id="time_of_day" name="time_of_day">
                        <option value="day" selected>Day</option>
                        <option value="night">Night</option>
                        <option value="civil_twilight">Civil Twilight</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="operating_over_people">Operating Over People:</label>
                    <select id="operating_over_people" name="operating_over_people">
                        <option value="false" selected>No</option>
                        <option value="true">Yes</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="operating_altitude">Altitude (feet):</label>
                    <input type="number" id="operating_altitude" name="operating_altitude" value="200" min="0">
                </div>
                <div class="form-group">
                    <label for="operating_speed">Speed (knots):</label>
                    <input type="number" id="operating_speed" name="operating_speed" value="35" min="0">
                </div>
                <div class="form-group">
                    <label for="is_within_400ft_of_structure">Within 400ft of Structure:</label>
                    <select id="is_within_400ft_of_structure" name="is_within_400ft_of_structure">
                        <option value="false" selected>No</option>
                        <option value="true">Yes</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="operating_altitude_above_structure">Altitude Above Structure (feet):</label>
                    <input type="number" id="operating_altitude_above_structure" name="operating_altitude_above_structure" value="0" min="0">
                </div>
            </div>
            
            <div class="section">
                <h3>Environment Details</h3>
                <div class="form-group">
                    <label for="airspace_class">Airspace Class:</label>
                    <select id="airspace_class" name="airspace_class">
                        <option value="G" selected>Class G</option>
                        <option value="E">Class E</option>
                        <option value="D">Class D</option>
                        <option value="C">Class C</option>
                        <option value="B">Class B</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="is_airport_surface_area">In Airport Surface Area:</label>
                    <select id="is_airport_surface_area" name="is_airport_surface_area">
                        <option value="false" selected>No</option>
                        <option value="true">Yes</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="is_restricted_access_area">In Restricted Access Area:</label>
                    <select id="is_restricted_access_area" name="is_restricted_access_area">
                        <option value="false" selected>No</option>
                        <option value="true">Yes</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="flight_visibility">Visibility (statute miles):</label>
                    <input type="number" id="flight_visibility" name="flight_visibility" value="5" min="0" step="0.1">
                </div>
                <div class="form-group">
                    <label for="distance_from_clouds_horizontal">Horizontal Distance from Clouds (feet):</label>
                    <input type="number" id="distance_from_clouds_horizontal" name="distance_from_clouds_horizontal" value="2500" min="0">
                </div>
                <div class="form-group">
                    <label for="distance_from_clouds_vertical">Vertical Distance from Clouds (feet):</label>
                    <input type="number" id="distance_from_clouds_vertical" name="distance_from_clouds_vertical" value="600" min="0">
                </div>
            </div>
            
            <div class="section">
                <h3>People Details</h3>
                <div class="form-group">
                    <label for="people_are_participants">People are Direct Participants:</label>
                    <select id="people_are_participants" name="people_are_participants">
                        <option value="false" selected>No</option>
                        <option value="true">Yes</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="people_under_cover">People are Under Cover:</label>
                    <select id="people_under_cover" name="people_under_cover">
                        <option value="false" selected>No</option>
                        <option value="true">Yes</option>
                    </select>
                </div>
            </div>
            
            <div class="section">
                <h3>Pilot Information</h3>
                <div class="form-group">
                    <label for="pilot_has_night_training">Pilot Has Night Training:</label>
                    <select id="pilot_has_night_training" name="pilot_has_night_training">
                        <option value="true" selected>Yes</option>
                        <option value="false">No</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="has_atc_authorization">Has ATC Authorization:</label>
                    <select id="has_atc_authorization" name="has_atc_authorization">
                        <option value="false" selected>No</option>
                        <option value="true">Yes</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="remote_pilot_certificate">Has Remote Pilot Certificate:</label>
                    <select id="remote_pilot_certificate" name="remote_pilot_certificate">
                        <option value="true" selected>Yes</option>
                        <option value="false">No</option>
                    </select>
                </div>
            </div>
            
            <button type="button" onclick="evaluateDrone()">Evaluate Operation</button>
            <button type="button" onclick="generateReport()" style="margin-left: 10px; background-color: #4b70e2; color: white; padding: 10px 15px; border: none; cursor: pointer;">Generate PDF Report</button>
        </form>
        
        <div id="result" class="result" style="display:none;"></div>
    </div>
    
    <script>
        function evaluateDrone() {
            const form = document.getElementById('droneForm');
            const formData = new FormData(form);
            const data = {};
            
            for (const [key, value] of formData.entries()) {
                // Convert boolean strings to actual booleans
                if (value === 'true' || value === 'false') {
                    data[key] = value === 'true';
                }
                // Convert numeric strings to numbers
                else if (!isNaN(value) && value !== '') {
                    data[key] = Number(value);
                }
                else {
                    data[key] = value;
                }
            }
            
            fetch('/api/evaluate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            })
            .then(response => response.json())
            .then(result => {
                const resultDiv = document.getElementById('result');
                resultDiv.style.display = 'block';
                
                if (result.status === 'APPROVED') {
                    resultDiv.className = 'result approved';
                    resultDiv.innerHTML = `<h2>✅ APPROVED</h2><p>${result.details[0]}</p>`;
                } else {
                    resultDiv.className = 'result denied';
                    let html = `<h2>❌ DENIED</h2><p>Your drone operation violates the following FAA rules:</p><ul>`;
                    for (const detail of result.details) {
                        html += `<li>${detail}</li>`;
                    }
                    html += '</ul>';
                    resultDiv.innerHTML = html;
                }
            })
            .catch(error => {
                console.error('Error:', error);
                const resultDiv = document.getElementById('result');
                resultDiv.style.display = 'block';
                resultDiv.className = 'result denied';
                resultDiv.innerHTML = `<h2>Error</h2><p>An error occurred: ${error.message}</p>`;
            });
        }
        
        function generateReport() {
            const form = document.getElementById('droneForm');
            const formData = new FormData(form);
            const data = {};
            
            for (const [key, value] of formData.entries()) {
                // Convert boolean strings to actual booleans
                if (value === 'true' || value === 'false') {
                    data[key] = value === 'true';
                }
                // Convert numeric strings to numbers
                else if (!isNaN(value) && value !== '') {
                    data[key] = Number(value);
                }
                else {
                    data[key] = value;
                }
            }
            
            fetch('/api/report', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            })
            .then(response => {
                if (response.ok) {
                    return response.blob();
                }
                throw new Error('Network response was not ok');
            })
            .then(blob => {
                // Create a link to download the PDF
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = 'drone_compliance_report.pdf';
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error generating report: ' + error.message);
            });
        }
    </script>
</body>
</html>""")

@app.route('/')
def index():
    """Render the web interface"""
    return render_template('index.html')

@app.route('/api/evaluate', methods=['POST'])
def evaluate_drone():
    """API endpoint to evaluate drone operations"""
    try:
        # Get JSON data from request
        data = request.json
        logger.info(f"Received evaluation request: {data}")
        
        # Convert boolean and numeric values
        for key, value in data.items():
            if isinstance(value, str):
                if value.lower() == 'true':
                    data[key] = True
                elif value.lower() == 'false':
                    data[key] = False
                elif value.replace('.', '', 1).isdigit():
                    data[key] = float(value)
        
        # Create DroneOperation object
        try:
            operation = DroneOperation(
                drone_category=data.get('drone_category'),
                drone_weight=float(data.get('drone_weight')),
                has_anti_collision_lighting=bool(data.get('has_anti_collision_lighting')),
                has_remote_id=bool(data.get('has_remote_id')),
                time_of_day=data.get('time_of_day'),
                operating_over_people=bool(data.get('operating_over_people')),
                operating_altitude=float(data.get('operating_altitude')),
                operating_speed=float(data.get('operating_speed')),
                airspace_class=data.get('airspace_class'),
                flight_visibility=float(data.get('flight_visibility')),
                distance_from_clouds_horizontal=float(data.get('distance_from_clouds_horizontal')),
                distance_from_clouds_vertical=float(data.get('distance_from_clouds_vertical')),
                # Optional parameters with default values
                has_airworthiness_certificate=bool(data.get('has_airworthiness_certificate', False)),
                complies_with_kinetic_energy_limit=bool(data.get('complies_with_kinetic_energy_limit', False)),
                has_exposed_rotating_parts=bool(data.get('has_exposed_rotating_parts', False)),
                is_within_400ft_of_structure=bool(data.get('is_within_400ft_of_structure', False)),
                operating_altitude_above_structure=float(data.get('operating_altitude_above_structure', 0.0)),
                is_airport_surface_area=bool(data.get('is_airport_surface_area', False)),
                is_restricted_access_area=bool(data.get('is_restricted_access_area', False)),
                people_are_participants=bool(data.get('people_are_participants', False)),
                people_under_cover=bool(data.get('people_under_cover', False)),
                pilot_has_night_training=bool(data.get('pilot_has_night_training', False)),
                has_atc_authorization=bool(data.get('has_atc_authorization', False)),
                remote_pilot_certificate=bool(data.get('remote_pilot_certificate', False))
            )
        except Exception as e:
            logger.error(f"Error creating DroneOperation: {e}")
            return jsonify({
                "status": "ERROR",
                "message": f"Invalid operation data: {str(e)}"
            }), 400
        
        # Evaluate operation
        result = evaluator.evaluate_operation(operation)
        logger.info(f"Evaluation result: {result}")
        
        return jsonify(result)
    
    except Exception as e:
        logger.exception(f"Error processing request: {e}")
        return jsonify({
            "status": "ERROR",
            "message": str(e)
        }), 500

@app.route('/api/docs')
def api_docs():
    """API documentation endpoint"""
    return jsonify({
        "name": "FAA Drone Rules Evaluator API",
        "version": "1.0.0",
        "description": "API for evaluating drone operations against FAA regulations",
        "endpoints": [
            {
                "path": "/api/evaluate",
                "method": "POST",
                "description": "Evaluate a drone operation",
                "request_body": {
                    "drone_category": "string (Category1, Category2, Category3, Category4)",
                    "drone_weight": "number (pounds)",
                    "has_anti_collision_lighting": "boolean",
                    "has_remote_id": "boolean",
                    "time_of_day": "string (day, night, civil_twilight)",
                    "operating_over_people": "boolean",
                    "operating_altitude": "number (feet)",
                    "operating_speed": "number (knots)",
                    "airspace_class": "string (B, C, D, E, G)",
                    "flight_visibility": "number (statute miles)",
                    "distance_from_clouds_horizontal": "number (feet)",
                    "distance_from_clouds_vertical": "number (feet)",
                    "has_airworthiness_certificate": "boolean (optional)",
                    "complies_with_kinetic_energy_limit": "boolean (optional)",
                    "has_exposed_rotating_parts": "boolean (optional)",
                    "is_within_400ft_of_structure": "boolean (optional)",
                    "operating_altitude_above_structure": "number (optional, feet)",
                    "is_airport_surface_area": "boolean (optional)",
                    "is_restricted_access_area": "boolean (optional)",
                    "people_are_participants": "boolean (optional)",
                    "people_under_cover": "boolean (optional)",
                    "pilot_has_night_training": "boolean (optional)",
                    "has_atc_authorization": "boolean (optional)",
                    "remote_pilot_certificate": "boolean (optional)"
                },
                "responses": {
                    "200": {
                        "status": "string (APPROVED or DENIED)",
                        "details": "array of strings with details",
                        "raw_decision": "object with raw decision details"
                    },
                    "400": {
                        "status": "ERROR",
                        "message": "Error details"
                    },
                    "500": {
                        "status": "ERROR",
                        "message": "Error details"
                    }
                }
            },
            {
                "path": "/api/report",
                "method": "POST",
                "description": "Generate a PDF compliance report",
                "request_body": "Same as /api/evaluate",
                "responses": {
                    "200": "PDF File Download",
                    "400": {
                        "status": "ERROR",
                        "message": "Error details"
                    },
                    "500": {
                        "status": "ERROR",
                        "message": "Error details"
                    }
                }
            }
        ]
    })

def generate_compliance_report(operation, result):
    """Generate a PDF compliance report for a drone operation"""
    # Create a unique filename
    report_id = str(uuid.uuid4())[:8]
    filename = f"reports/drone_compliance_report_{report_id}.pdf"
    
    # Create a PDF document
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Create custom styles - avoid using 'Title' as it's already defined
    styles.add(ParagraphStyle(
        name='ReportTitle',  # Changed from 'Title'
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=0.3*inch
    ))
    styles.add(ParagraphStyle(
        name='SectionHeader',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=0.2*inch,
        spaceBefore=0.2*inch
    ))
    styles.add(ParagraphStyle(
        name='RightAligned',
        parent=styles['Normal'],
        alignment=2  # 2 is right-aligned
    ))
    
    # Document elements
    elements = []
    
    # Title and header
    elements.append(Paragraph("FAA Drone Compliance Report", styles['ReportTitle']))  # Changed from 'Title'
    elements.append(Paragraph(f"Report ID: {report_id}", styles['RightAligned']))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['RightAligned']))
    elements.append(Spacer(1, 0.2*inch))
    
    # Compliance status section
    status_color = colors.green if result['status'] == 'APPROVED' else colors.red
    elements.append(Paragraph(f"Compliance Status: <font color={status_color}>{result['status']}</font>", 
                             styles['SectionHeader']))
    
    for detail in result['details']:
        elements.append(Paragraph(f"• {detail}", styles['Normal']))
    
    elements.append(Spacer(1, 0.2*inch))
    
    # Drone characteristics
    elements.append(Paragraph("Drone Characteristics", styles['SectionHeader']))
    
    # Convert operation dataclass to dictionary
    op_dict = operation.__dict__
    
    drone_data = [
        ["Parameter", "Value"],
        ["Category", op_dict['drone_category']],
        ["Weight", f"{op_dict['drone_weight']} pounds"],
        ["Has Anti-Collision Lighting", "Yes" if op_dict['has_anti_collision_lighting'] else "No"],
        ["Has Remote ID", "Yes" if op_dict['has_remote_id'] else "No"],
        ["Has Airworthiness Certificate", "Yes" if op_dict['has_airworthiness_certificate'] else "No"],
        ["Complies with Kinetic Energy Limit", "Yes" if op_dict['complies_with_kinetic_energy_limit'] else "No"],
        ["Has Exposed Rotating Parts", "Yes" if op_dict['has_exposed_rotating_parts'] else "No"]
    ]
    
    # Create table
    drone_table = Table(drone_data, colWidths=[3*inch, 2*inch])
    drone_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.black),
        ('ALIGN', (0, 0), (1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (1, 0), 12),
        ('BACKGROUND', (0, 1), (1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    elements.append(drone_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Operation details
    elements.append(Paragraph("Operation Details", styles['SectionHeader']))
    
    operation_data = [
        ["Parameter", "Value"],
        ["Time of Day", op_dict['time_of_day']],
        ["Operating Over People", "Yes" if op_dict['operating_over_people'] else "No"],
        ["Altitude", f"{op_dict['operating_altitude']} feet"],
        ["Speed", f"{op_dict['operating_speed']} knots"],
        ["Within 400ft of Structure", "Yes" if op_dict['is_within_400ft_of_structure'] else "No"],
        ["Altitude Above Structure", f"{op_dict['operating_altitude_above_structure']} feet"]
    ]
    
    operation_table = Table(operation_data, colWidths=[3*inch, 2*inch])
    operation_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.black),
        ('ALIGN', (0, 0), (1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (1, 0), 12),
        ('BACKGROUND', (0, 1), (1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    elements.append(operation_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Environment details
    elements.append(Paragraph("Environment Details", styles['SectionHeader']))
    
    environment_data = [
        ["Parameter", "Value"],
        ["Airspace Class", op_dict['airspace_class']],
        ["In Airport Surface Area", "Yes" if op_dict['is_airport_surface_area'] else "No"],
        ["In Restricted Access Area", "Yes" if op_dict['is_restricted_access_area'] else "No"],
        ["Visibility", f"{op_dict['flight_visibility']} statute miles"],
        ["Horizontal Distance from Clouds", f"{op_dict['distance_from_clouds_horizontal']} feet"],
        ["Vertical Distance from Clouds", f"{op_dict['distance_from_clouds_vertical']} feet"]
    ]
    
    environment_table = Table(environment_data, colWidths=[3*inch, 2*inch])
    environment_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.black),
        ('ALIGN', (0, 0), (1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (1, 0), 12),
        ('BACKGROUND', (0, 1), (1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    elements.append(environment_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Pilot information
    elements.append(Paragraph("Pilot Information", styles['SectionHeader']))
    
    pilot_data = [
        ["Parameter", "Value"],
        ["Has Night Training", "Yes" if op_dict['pilot_has_night_training'] else "No"],
        ["Has ATC Authorization", "Yes" if op_dict['has_atc_authorization'] else "No"],
        ["Has Remote Pilot Certificate", "Yes" if op_dict['remote_pilot_certificate'] else "No"]
    ]
    
    pilot_table = Table(pilot_data, colWidths=[3*inch, 2*inch])
    pilot_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.black),
        ('ALIGN', (0, 0), (1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (1, 0), 12),
        ('BACKGROUND', (0, 1), (1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    elements.append(pilot_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Disclaimer
    elements.append(Paragraph("Disclaimer: This report is for informational purposes only. The final determination of compliance with FAA regulations rests with the FAA and other relevant authorities.", styles['Normal']))
    
    # Build the PDF
    doc.build(elements)
    
    # Save PDF to file
    with open(filename, 'wb') as f:
        f.write(buffer.getvalue())
    
    return filename, buffer.getvalue()

@app.route('/api/report', methods=['POST'])
def create_report():
    """Create a PDF compliance report for a drone operation"""
    try:
        # Get JSON data from request
        data = request.json
        logger.info(f"Received report generation request: {data}")
        
        # Create DroneOperation object (same as in evaluate_drone function)
        try:
            operation = DroneOperation(
                drone_category=data.get('drone_category'),
                drone_weight=float(data.get('drone_weight')),
                has_anti_collision_lighting=bool(data.get('has_anti_collision_lighting')),
                has_remote_id=bool(data.get('has_remote_id')),
                time_of_day=data.get('time_of_day'),
                operating_over_people=bool(data.get('operating_over_people')),
                operating_altitude=float(data.get('operating_altitude')),
                operating_speed=float(data.get('operating_speed')),
                airspace_class=data.get('airspace_class'),
                flight_visibility=float(data.get('flight_visibility')),
                distance_from_clouds_horizontal=float(data.get('distance_from_clouds_horizontal')),
                distance_from_clouds_vertical=float(data.get('distance_from_clouds_vertical')),
                # Optional parameters with default values
                has_airworthiness_certificate=bool(data.get('has_airworthiness_certificate', False)),
                complies_with_kinetic_energy_limit=bool(data.get('complies_with_kinetic_energy_limit', False)),
                has_exposed_rotating_parts=bool(data.get('has_exposed_rotating_parts', False)),
                is_within_400ft_of_structure=bool(data.get('is_within_400ft_of_structure', False)),
                operating_altitude_above_structure=float(data.get('operating_altitude_above_structure', 0.0)),
                is_airport_surface_area=bool(data.get('is_airport_surface_area', False)),
                is_restricted_access_area=bool(data.get('is_restricted_access_area', False)),
                people_are_participants=bool(data.get('people_are_participants', False)),
                people_under_cover=bool(data.get('people_under_cover', False)),
                pilot_has_night_training=bool(data.get('pilot_has_night_training', False)),
                has_atc_authorization=bool(data.get('has_atc_authorization', False)),
                remote_pilot_certificate=bool(data.get('remote_pilot_certificate', False))
            )
        except Exception as e:
            logger.error(f"Error creating DroneOperation: {e}")
            return jsonify({
                "status": "ERROR",
                "message": f"Invalid operation data: {str(e)}"
            }), 400
        
        # Evaluate operation
        result = evaluator.evaluate_operation(operation)
        logger.info(f"Evaluation result for report: {result}")
        
        # Generate PDF report
        filename, pdf_data = generate_compliance_report(operation, result)
        logger.info(f"Generated report: {filename}")
        
        # Return the report as a downloadable file
        return send_file(
            BytesIO(pdf_data),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=os.path.basename(filename)
        )
    
    except Exception as e:
        logger.exception(f"Error generating report: {e}")
        return jsonify({
            "status": "ERROR",
            "message": f"Error generating report: {str(e)}"
        }), 500

if __name__ == '__main__':
    # Log startup
    logger.info("Starting FAA Drone Rules API Server")
    
    # Create example operations file if it doesn't exist
    if not os.path.exists('example_operations.json'):
        with open('example_operations.json', 'w') as f:
            json.dump([
                {
                    "name": "Compliant Operation",
                    "description": "A fully compliant drone operation",
                    "operation": {
                        "drone_category": "Category2",
                        "drone_weight": 1.5,
                        "has_anti_collision_lighting": True,
                        "has_remote_id": True,
                        "time_of_day": "day",
                        "operating_over_people": False,
                        "operating_altitude": 200,
                        "operating_speed": 35,
                        "airspace_class": "G",
                        "flight_visibility": 5,
                        "distance_from_clouds_horizontal": 2500,
                        "distance_from_clouds_vertical": 600,
                        "complies_with_kinetic_energy_limit": True,
                        "pilot_has_night_training": True,
                        "remote_pilot_certificate": True
                    }
                },
                {
                    "name": "Non-Compliant Operation",
                    "description": "Drone operation with multiple violations",
                    "operation": {
                        "drone_category": "Category2",
                        "drone_weight": 1.5,
                        "has_anti_collision_lighting": True,
                        "has_remote_id": False,
                        "time_of_day": "day",
                        "operating_over_people": False,
                        "operating_altitude": 600,
                        "operating_speed": 35,
                        "airspace_class": "G",
                        "flight_visibility": 2,
                        "distance_from_clouds_horizontal": 2500,
                        "distance_from_clouds_vertical": 600,
                        "complies_with_kinetic_energy_limit": True,
                        "pilot_has_night_training": False,
                        "remote_pilot_certificate": True
                    }
                }
            ], f, indent=2)
        
        logger.info("Created example_operations.json file")
    
    app.run(debug=True, host='0.0.0.0', port=8080)