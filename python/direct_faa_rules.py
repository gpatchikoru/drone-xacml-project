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


class FAADroneRulesEvaluator:
    """Directly evaluates FAA drone rules without using XACML PDP"""
    
    def evaluate_operation(self, operation: DroneOperation) -> Dict[str, Any]:
        """
        Evaluate if a drone operation complies with FAA regulations
        
        Returns a dict with decision and details
        """
        # Check all FAA regulations directly
        violations = []
        
        # Check night operation rules
        if operation.time_of_day == "night":
            if not operation.pilot_has_night_training:
                violations.append("Night operation requires pilot night training")
            if not operation.has_anti_collision_lighting:
                violations.append("Night operation requires anti-collision lighting")
        
        # Check civil twilight operation rules
        if operation.time_of_day == "civil_twilight" and not operation.has_anti_collision_lighting:
            violations.append("Civil twilight operation requires anti-collision lighting")
        
        # Check operation over people rules
        if operation.operating_over_people:
            if not any([
                operation.people_are_participants,
                operation.people_under_cover,
                operation.drone_weight < 0.55,
                (operation.drone_category == "Category2" and operation.complies_with_kinetic_energy_limit),
                (operation.drone_category == "Category3" and operation.is_restricted_access_area),
                (operation.drone_category == "Category4" and operation.has_airworthiness_certificate)
            ]):
                violations.append("Operation over people does not meet any exemption criteria")
        
        # Check airspace restrictions
        if operation.airspace_class in ['B', 'C', 'D'] and not operation.has_atc_authorization:
            violations.append(f"Operation in Class {operation.airspace_class} airspace requires ATC authorization")
        
        if operation.airspace_class == 'E' and operation.is_airport_surface_area and not operation.has_atc_authorization:
            violations.append("Operation in Class E airport surface area requires ATC authorization")
        
        # Check operating limitations
        if operation.operating_speed > 87:
            violations.append(f"Speed exceeds 87 knots limit (current: {operation.operating_speed} knots)")
        
        if operation.operating_altitude > 400 and not operation.is_within_400ft_of_structure:
            violations.append(f"Altitude exceeds 400 feet limit (current: {operation.operating_altitude} feet)")
        
        if operation.is_within_400ft_of_structure and operation.operating_altitude_above_structure > 400:
            violations.append(f"Altitude exceeds 400 feet above structure (current: {operation.operating_altitude_above_structure} feet)")
        
        if operation.flight_visibility < 3:
            violations.append(f"Visibility below 3 statute miles (current: {operation.flight_visibility} miles)")
        
        if operation.distance_from_clouds_horizontal < 2000:
            violations.append(f"Horizontal distance from clouds below 2000 feet (current: {operation.distance_from_clouds_horizontal} feet)")
        
        if operation.distance_from_clouds_vertical < 500:
            violations.append(f"Vertical distance from clouds below 500 feet (current: {operation.distance_from_clouds_vertical} feet)")
        
        # Check Remote ID requirement
        if not operation.has_remote_id:
            violations.append("Drone lacks required Remote ID capability")
        
        # Category-specific rules
        if operation.drone_category == "Category2" and operation.has_exposed_rotating_parts:
            violations.append("Category 2 drones must not have exposed rotating parts")
        
        if operation.drone_category == "Category4" and not operation.has_airworthiness_certificate:
            violations.append("Category 4 drones require an airworthiness certificate")
        
        # Determine result based on violations
        if violations:
            status = "DENIED"
            details = violations
            decision = "Deny"
        else:
            status = "APPROVED"
            details = ["Operation complies with FAA regulations"]
            decision = "Permit"
        
        # Create result
        result = {
            "status": status,
            "details": details,
            "raw_decision": {
                "decision": decision,
                "obligations": [],
                "advice": []
            }
        }
        
        return result


def main():
    # Initialize the evaluator
    evaluator = FAADroneRulesEvaluator()
    
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
    
    print("\nRaw decision:", result["raw_decision"])
    
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


if __name__ == "__main__":
    main()