import os
import sys
import requests
import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

@dataclass
class DroneOperation:
    """Represents a drone operation with all relevant attributes"""
    # Drone characteristics
    drone_category: str  # 'Category1', 'Category2', 'Category3', 'Category4'
    drone_weight: float  # in pounds
    has_anti_collision_lighting: bool
    has_remote_id: bool
    has_airworthiness_certificate: bool = False
    complies_with_kinetic_energy_limit: bool = False
    has_exposed_rotating_parts: bool = False

    # Operation details
    time_of_day: str  # 'day', 'night', 'civil_twilight'
    operating_over_people: bool
    operating_altitude: float  # in feet
    operating_speed: float  # in knots
    is_within_400ft_of_structure: bool = False
    operating_altitude_above_structure: float = 0.0  # in feet

    # Environment details
    airspace_class: str  # 'B', 'C', 'D', 'E', 'G'
    is_airport_surface_area: bool = False
    is_restricted_access_area: bool = False
    flight_visibility: float  # in statute miles
    distance_from_clouds_horizontal: float  # in feet
    distance_from_clouds_vertical: float  # in feet
    
    # People details (if operating over people)
    people_are_participants: bool = False
    people_under_cover: bool = False
    
    # Pilot information
    pilot_has_night_training: bool = False
    has_atc_authorization: bool = False
    remote_pilot_certificate: bool = False


class XACMLPolicyDecisionPoint:
    """Interface to a XACML Policy Decision Point"""
    
    def __init__(self, pdp_url: str, pdp_type: str = "balana"):
        """
        Initialize with URL to PDP service and PDP type
        
        Available PDP types:
        - "balana": For WSO2 Balana
        - "authzforce": For AuthzForce
        - "att": For AT&T XACML
        """
        self.pdp_url = pdp_url
        self.pdp_type = pdp_type
        
    def make_decision(self, operation: DroneOperation) -> Dict[str, Any]:
        """
        Convert drone operation to XACML request and get decision
        Returns the full decision response
        """
        # Convert DroneOperation to XACML request
        xacml_request = self._create_xacml_request(operation)
        
        # Send request to PDP
        headers = {"Content-Type": "application/xml"}
        
        # Different PDPs may have different endpoints or formats
        if self.pdp_type == "balana":
            response = requests.post(
                self.pdp_url,
                headers=headers,
                data=xacml_request
            )
        elif self.pdp_type == "authzforce":
            # AuthzForce has a different API structure
            response = requests.post(
                f"{self.pdp_url}/domains/domain/pdp",
                headers=headers,
                data=xacml_request
            )
        elif self.pdp_type == "att":
            # AT&T PDP has its own format
            response = requests.post(
                self.pdp_url,
                headers=headers,
                data=xacml_request
            )
        else:
            raise ValueError(f"Unsupported PDP type: {self.pdp_type}")
        
        if response.status_code != 200:
            raise Exception(f"PDP request failed with status {response.status_code}: {response.text}")
        
        # Parse and return decision
        return self._parse_xacml_response(response.text)
    
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
        
        # Handle different PDP response formats
        if self.pdp_type == "balana":
            # WSO2 Balana format
            result = root.find(".//{urn:oasis:names:tc:xacml:3.0:core:schema:wd-17}Result")
            decision = result.find(".//{urn:oasis:names:tc:xacml:3.0:core:schema:wd-17}Decision").text
            
            # Extract obligations if present
            obligations = []
            obligations_elem = result.find(".//{urn:oasis:names:tc:xacml:3.0:core:schema:wd-17}Obligations")
            if obligations_elem is not None:
                for obligation in obligations_elem.findall(".//{urn:oasis:names:tc:xacml:3.0:core:schema:wd-17}Obligation"):
                    obligation_id = obligation.get("ObligationId")
                    obligations.append(obligation_id)
            
            # Extract advice if present
            advice = []
            advice_elem = result.find(".//{urn:oasis:names:tc:xacml:3.0:core:schema:wd-17}AssociatedAdvice")
            if advice_elem is not None:
                for advice_item in advice_elem.findall(".//{urn:oasis:names:tc:xacml:3.0:core:schema:wd-17}Advice"):
                    advice_id = advice_item.get("AdviceId")
                    advice.append(advice_id)
            
            return {
                "decision": decision,
                "obligations": obligations,
                "advice": advice
            }
        
        elif self.pdp_type == "authzforce":
            # AuthzForce format
            result = root.find(".//{urn:oasis:names:tc:xacml:3.0:core:schema:wd-17}Result")
            decision = result.find(".//{urn:oasis:names:tc:xacml:3.0:core:schema:wd-17}Decision").text
            
            return {
                "decision": decision
            }
        
        elif self.pdp_type == "att":
            # AT&T format
            result = root.find(".//Result")
            decision = result.find(".//Decision").text
            
            return {
                "decision": decision
            }
        
        else:
            # Generic format
            result = root.find(".//Result")
            decision = result.find(".//Decision").text
            
            return {
                "decision": decision
            }


class FAADroneRulesEvaluator:
    """Evaluates FAA drone rules using XACML policies"""
    
    def __init__(self, pdp_url: str, pdp_type: str = "balana"):
        """Initialize with URL to the PDP service"""
        self.pdp = XACMLPolicyDecisionPoint(pdp_url, pdp_type)
    
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
        
        return {
            "status": status,
            "details": details,
            "raw_decision": result
        }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Evaluate FAA drone rules for a given operation')
    parser.add_argument('--pdp-url', type=str, required=True, help='URL of the XACML PDP service')
    parser.add_argument('--pdp-type', type=str, default='balana', choices=['balana', 'authzforce', 'att'],
                       help='Type of PDP implementation')
    parser.add_argument('--json-input', type=str, help='Path to JSON file with operation details')
    
    args = parser.parse_args()
    
    # Initialize the evaluator
    evaluator = FAADroneRulesEvaluator(args.pdp_url, args.pdp_type)
    
    # If JSON input provided, use it
    if args.json_input:
        with open(args.json_input, 'r') as f:
            operation_dict = json.load(f)
        
        # Convert dict to DroneOperation object
        operation = DroneOperation(**operation_dict)
    else:
        # Example operation for testing
        operation = DroneOperation(
            # Drone characteristics
            drone_category="Category2",
            drone_weight=1.5,  # pounds
            has_anti_collision_lighting=True,
            has_remote_id=True,
            complies_with_kinetic_energy_limit=True,
            
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
            
            # Pilot information
            remote_pilot_certificate=True
        )
    
    # Evaluate the operation
    result = evaluator.evaluate_operation(operation)
    
    # Print result
    print(f"\nOperation evaluation result: {result['status']}")
    
    if result["details"]:
        print("\nDetails:")
        for detail in result["details"]:
            print(f"- {detail}")
    
    print("\nRaw XACML decision:", result["raw_decision"])


if __name__ == "__main__":
    main()