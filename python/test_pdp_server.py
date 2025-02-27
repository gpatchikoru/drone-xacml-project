import requests
import xml.etree.ElementTree as ET
from dataclasses import dataclass

@dataclass
class DroneOperation:
    # [Same DroneOperation class from direct_faa_rules.py]
    # Copy the entire class definition from there
    pass

def create_xacml_request(operation):
    # Create XACML request XML
    root = ET.Element("Request", xmlns="urn:oasis:names:tc:xacml:3.0:core:schema:wd-17")
    
    # Add attributes (subject, resource, action, environment)
    # [Add the same attributes as in file_based_pdp.py]
    
    # Convert to string
    return ET.tostring(root, encoding='utf8', method='xml').decode()

def test_pdp_server():
    # Create a compliant operation
    operation = DroneOperation(
        drone_category="Category2",
        drone_weight=1.5,
        has_anti_collision_lighting=True,
        has_remote_id=True,
        time_of_day="day",
        operating_over_people=False,
        operating_altitude=200,
        operating_speed=35,
        airspace_class="G",
        flight_visibility=5,
        distance_from_clouds_horizontal=2500,
        distance_from_clouds_vertical=600,
        complies_with_kinetic_energy_limit=True,
        pilot_has_night_training=True,
        remote_pilot_certificate=True
    )
    
    # Create XACML request
    xacml_request = create_xacml_request(operation)
    
    # Send request to PDP server
    response = requests.post(
        "http://localhost:8080/pdp",
        headers={"Content-Type": "application/xml"},
        data=xacml_request
    )
    
    # Check response
    if response.status_code == 200:
        print("PDP server responded successfully")
        print(response.text)
    else:
        print(f"Error: PDP server returned status code {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_pdp_server()