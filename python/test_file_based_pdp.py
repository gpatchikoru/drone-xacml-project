#!/usr/bin/env python3

import os
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

# Import file-based PDP
from file_based_pdp import FileBasedPDP

@dataclass
class DroneOperation:
    """Represents a drone operation with all relevant attributes"""
    # Drone characteristics
    drone_category: str  # 'Category1', 'Category2', 'Category3', 'Category4'
    drone_weight: float  # in pounds
    has_anti_collision_lighting: bool
    has_remote_id: bool
    
    # Operation details
    time_of_day: str  # 'day', 'night', 'civil_twilight'
    operating_over_people: bool
    operating_altitude: float  # in feet
    operating_speed: float  # in knots
    
    # Environment details
    airspace_class: str  # 'B', 'C', 'D', 'E', 'G'
    flight_visibility: float  # in statute miles
    distance_from_clouds_horizontal: float  # in feet
    distance_from_clouds_vertical: float  # in feet
    
    # Optional parameters (with default values)
    has_airworthiness_certificate: bool = False
    complies_with_kinetic_energy_limit: bool = False
    has_exposed_rotating_parts: bool = False
    is_within_400ft_of_structure: bool = False
    operating_altitude_above_structure: float = 0.0  # in feet
    is_airport_surface_area: bool = False
    is_restricted_access_area: bool = False
    people_are_participants: bool = False
    people_under_cover: bool = False
    pilot_has_night_training: bool = False
    has_atc_authorization: bool = False
    remote_pilot_certificate: bool = False


class FileBasedPDPWrapper:
    """Wrapper for the FileBasedPDP to match the API of our original PDP client"""
    
    def __init__(self, policy_file):
        """Initialize with path to policy file"""
        self.pdp = FileBasedPDP(policy_file)
    
    def make_decision(self, operation: DroneOperation) -> Dict[str, Any]:
        """
        Convert drone operation to XACML request and get decision
        Returns the decision response
        """
        # Convert DroneOperation to XACML request
        xacml_request = self._create_xacml_request(operation)
        
        # Send request to PDP
        xacml_response = self.pdp.evaluate(xacml_request)
        
        # Parse response
        return self._parse_xacml_response(xacml_response)
    
    def _create_xacml_request(self, operation: DroneOperation) -> str:
        """Convert a DroneOperation into a XACML request XML"""
        # Create the XACML 3.0 request
        root = ET.Element("Request", xmlns="urn:oasis:names:tc:xacml:3.0:core:schema:wd-17")
        
        # Add subject attributes (pilot)
        subject = ET.SubElement(root, "Attributes", 
                               Category="urn:oasis:names:tc:xacml:1.0:subject-category:access-subject")
        self._add_attribute(subject, "has-completed-night-training", "boolean", str(operation.pilot_has_night_training).lower())
        self._add_attribute(subject, "has-remote-pilot-certificate", "boolean", str(operation.remote_pilot_certificate).lower())
        
        # Add resource attributes (drone)
        resource = ET.SubElement(root, "Attributes", 
                                Category="urn:oasis:names:tc:xacml:3.0:attribute-category:resource")
        self._add_attribute(resource, "drone-category", "string", operation.drone_category)
        self._add_attribute(resource, "drone-weight", "double", str(operation.drone_weight))
        self._add_attribute(resource, "has-anti-collision-lighting", "boolean", str(operation.has_anti_collision_lighting).lower())
        self._add_attribute(resource, "has-remote-id", "boolean", str(operation.has_remote_id).lower())
        self._add_attribute(resource, "has-airworthiness-certificate", "boolean", str(operation.has_airworthiness_certificate).lower())
        self._add_attribute(resource, "complies-with-kinetic-energy-limit", "boolean", str(operation.complies_with_kinetic_energy_limit).lower())
        self._add_attribute(resource, "has-exposed-rotating-parts", "boolean", str(operation.has_exposed_rotating_parts).lower())
        self._add_attribute(resource, "people-are-participants", "boolean", str(operation.people_are_participants).lower())
        self._add_attribute(resource, "people-under-cover", "boolean", str(operation.people_under_cover).lower())
        self._add_attribute(resource, "is-restricted-access-area", "boolean", str(operation.is_restricted_access_area).lower())
        
        # Add action attributes
        action = ET.SubElement(root, "Attributes", 
                              Category="urn:oasis:names:tc:xacml:3.0:attribute-category:action")
        self._add_attribute(action, "is-operating-over-people", "boolean", str(operation.operating_over_people).lower())
        self._add_attribute(action, "operating-speed", "double", str(operation.operating_speed))
        self._add_attribute(action, "operating-altitude", "double", str(operation.operating_altitude))
        self._add_attribute(action, "operating-altitude-above-structure", "double", str(operation.operating_altitude_above_structure))
        self._add_attribute(action, "has-atc-authorization", "boolean", str(operation.has_atc_authorization).lower())
        
        # Add environment attributes
        environment = ET.SubElement(root, "Attributes", 
                                   Category="urn:oasis:names:tc:xacml:3.0:attribute-category:environment")
        self._add_attribute(environment, "time-of-day", "string", operation.time_of_day)
        self._add_attribute(environment, "airspace-class", "string", operation.airspace_class)
        self._add_attribute(environment, "is-airport-surface-area", "boolean", str(operation.is_airport_surface_area).lower())
        self._add_attribute(environment, "flight-visibility", "double", str(operation.flight_visibility))
        self._add_attribute(environment, "distance-from-clouds-horizontal", "double", str(operation.distance_from_clouds_horizontal))
        self._add_attribute(environment, "distance-from-clouds-vertical", "double", str(operation.distance_from_clouds_vertical))
        self._add_attribute(environment, "is-within-400ft-of-structure", "boolean", str(operation.is_within_400ft_of_structure).lower())
        
        # Convert to string
        return ET.tostring(root, encoding='utf8', method='xml').decode()
    
    def _add_attribute(self, parent: ET.Element, attribute_id: str, data_type: str, value: str):
        """Helper to add an attribute to a XACML request"""
        attr = ET.SubElement(parent, "Attribute", 
                            AttributeId=attribute_id,
                            IncludeInResult="true")
        attr_val = ET.SubElement(attr, "AttributeValue", 
                                DataType=f"http://www.w3.org/2001/XMLSchema#{data_type}")
        attr_val.text = value
    
    def _parse_xacml_response(self, response_xml: str) -> Dict[str, Any]:
        """Parse a XACML response XML into a Python dict"""
        # Parse XML response
        root = ET.fromstring(response_xml)
        
        # Find Decision element
        result = root.find(".//{*}Result")
        decision = result.find(".//{*}Decision").text
        
        return {
            "decision": decision,
            "obligations": [],
            "advice": []
        }


class FAADroneRulesEvaluator:
    """Evaluates FAA drone rules using XACML policies"""
    
    def __init__(self, policy_file):
        """Initialize with path to policy file"""
        self.pdp = FileBasedPDPWrapper(policy_file)
    
    def evaluate_operation(self, operation: DroneOperation) -> Dict[str, Any]:
        """
        Evaluate if a drone operation complies with FAA regulations
        
        Returns a dict with decision and details
        """
        # Get decision from PDP
        result = self.pdp.make_decision(operation)
        
        # Process result and provide more user-friendly response
        decision = result["decision"]
        details = []
        
        if decision == "Permit":
            status = "APPROVED"
            details.append("Operation complies with FAA regulations")
        else:
            status = "DENIED"
            
            # Check for specific conditions that might have caused the denial
            if operation.time_of_day == "night" and not operation.pilot_has_night_training:
                details.append("Night operation requires pilot night training")
            
            if operation.time_of_day == "night" and not operation.has_anti_collision_lighting:
                details.append("Night operation requires anti-collision lighting")
            
            if operation.operating_over_people and not any([
                operation.people_are_participants,
                operation.people_under_cover,
                operation.drone_weight < 0.55,
                (operation.drone_category == "Category2" and operation.complies_with_kinetic_energy_limit),
                (operation.drone_category == "Category3" and operation.is_restricted_access_area),
                (operation.drone_category == "Category4" and operation.has_airworthiness_certificate)
            ]):
                details.append("Operation over people does not meet any exemption criteria")
            
            if operation.airspace_class in ['B', 'C', 'D'] and not operation.has_atc_authorization:
                details.append(f"Operation in Class {operation.airspace_class} airspace requires ATC authorization")
            
            if operation.operating_speed > 87:
                details.append(f"Speed exceeds 87 knots limit (current: {operation.operating_speed} knots)")
            
            if operation.operating_altitude > 400 and not operation.is_within_400ft_of_structure:
                details.append(f"Altitude exceeds 400 feet limit (current: {operation.operating_altitude} feet)")
            
            if operation.flight_visibility < 3:
                details.append(f"Visibility below 3 statute miles (current: {operation.flight_visibility} miles)")
            
            if operation.distance_from_clouds_horizontal < 2000:
                details.append(f"Horizontal distance from clouds below 2000 feet (current: {operation.distance_from_clouds_horizontal} feet)")
            
            if operation.distance_from_clouds_vertical < 500:
                details.append(f"Vertical distance from clouds below 500 feet (current: {operation.distance_from_clouds_vertical} feet)")
            
            if not operation.has_remote_id:
                details.append("Drone lacks required Remote ID capability")
            
            # If no specific details were found, add a generic message
            if not details:
                details.append("Operation does not comply with FAA regulations")
        
        return {
            "status": status,
            "details": details,
            "raw_decision": result
        }


def main():
    # Get path to policy file
    policy_file = None
    
    # Try different potential policy file locations
    potential_paths = [
        "../policies/FAADroneRules.xml",
        "policies/FAADroneRules.xml",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "../policies/FAADroneRules.xml"),
        "/Users/girishkumarpatchikoru/drone-xacml-project/policies/FAADroneRules.xml"
    ]
    
    for path in potential_paths:
        if os.path.exists(path):
            policy_file = path
            break
    
    if policy_file is None:
        print("Error: Policy file not found. Please ensure the FAADroneRules.xml file exists.")
        print("Checked the following locations:")
        for path in potential_paths:
            print(f"  - {path}")
        return
    
    print(f"Using policy file: {policy_file}")
    
    # Initialize the evaluator
    evaluator = FAADroneRulesEvaluator(policy_file)
    
    # Example operation for testing - compliant case
    operation = DroneOperation(
        # Drone characteristics
        drone_category="Category2",
        drone_weight=1.5,  # pounds
        has_anti_collision_lighting=True,
        has_remote_id=True,
        
        # Operation details
        time_of_day="day",
        operating_over_people=False,
        operating_altitude=200,  # feet
        operating_speed=35,  # knots
        
        # Environment details
        airspace_class="G",
        flight_visibility=5,  # statute miles
        distance_from_clouds_horizontal=2500,  # feet
        distance_from_clouds_vertical=600,  # feet
        
        # Optional parameters
        complies_with_kinetic_energy_limit=True,
        pilot_has_night_training=True,
        remote_pilot_certificate=True
    )
    
    # Evaluate the compliant operation
    result = evaluator.evaluate_operation(operation)
    
    # Print result
    print("\nCOMPLIANT OPERATION EVALUATION:")
    print(f"Status: {result['status']}")
    
    if result["details"]:
        print("\nDetails:")
        for detail in result["details"]:
            print(f"- {detail}")
    
    print("\nRaw XACML decision:", result["raw_decision"])
    
    # Try a non-compliant operation
    print("\n\nNON-COMPLIANT OPERATION EVALUATION:")
    
    # Create a new operation with multiple non-compliant attributes
    non_compliant_operation = DroneOperation(
        # Drone characteristics
        drone_category="Category2",
        drone_weight=1.5,  # pounds
        has_anti_collision_lighting=True,
        has_remote_id=False,  # Missing Remote ID (violation)
        
        # Operation details
        time_of_day="day",
        operating_over_people=False,
        operating_altitude=600,  # Above 400 feet limit (violation)
        operating_speed=35,  # knots
        
        # Environment details
        airspace_class="G",
        flight_visibility=2,  # Below 3 mile visibility requirement (violation)
        distance_from_clouds_horizontal=2500,  # feet
        distance_from_clouds_vertical=600,  # feet
        
        # Optional parameters
        complies_with_kinetic_energy_limit=True,
        pilot_has_night_training=False,  # No night training
        remote_pilot_certificate=True
    )
    
    # Re-evaluate with non-compliant operation
    result = evaluator.evaluate_operation(non_compliant_operation)
    
    # Print result
    print(f"Status: {result['status']}")
    
    if result["details"]:
        print("\nDetails:")
        for detail in result["details"]:
            print(f"- {detail}")
    
    print("\nRaw XACML decision:", result["raw_decision"])


if __name__ == "__main__":
    main()