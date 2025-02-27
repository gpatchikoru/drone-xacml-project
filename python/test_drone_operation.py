#!/usr/bin/env python3

from faa_drone_rules import DroneOperation, FAADroneRulesEvaluator

def main():
    # Create an example drone operation
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
        pilot_has_night_training=True,
        remote_pilot_certificate=True
    )
    
    # Create the evaluator with URL to your local PDP
    evaluator = FAADroneRulesEvaluator("http://localhost:8080/pdp", "balana")
    
    # Evaluate the operation
    result = evaluator.evaluate_operation(operation)
    
    # Print result
    print("\nDrone Operation Evaluation Result:")
    print(f"Status: {result['status']}")
    
    if result["details"]:
        print("\nDetails:")
        for detail in result["details"]:
            print(f"- {detail}")
    
    print("\nRaw XACML decision:", result["raw_decision"])
    
    # Try a non-compliant operation
    print("\n\nTesting a non-compliant operation...")
    operation.operating_altitude = 600  # Above 400 feet limit
    operation.has_remote_id = False  # Missing Remote ID
    operation.flight_visibility = 2  # Below 3 mile visibility requirement
    
    # Re-evaluate
    result = evaluator.evaluate_operation(operation)
    
    # Print result
    print("\nNon-Compliant Drone Operation Evaluation Result:")
    print(f"Status: {result['status']}")
    
    if result["details"]:
        print("\nDetails:")
        for detail in result["details"]:
            print(f"- {detail}")

if __name__ == "__main__":
    main()