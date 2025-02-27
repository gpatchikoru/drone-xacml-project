#!/usr/bin/env python3

import os
import xml.etree.ElementTree as ET
from lxml import etree
import re
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FileBasedPDP:
    """
    A simplified file-based XACML Policy Decision Point
    This implementation uses a simplified approach to evaluate XACML policies
    without requiring a separate server
    """
    
    def __init__(self, policy_file):
        """
        Initialize with path to XACML policy file
        """
        self.policy_file = policy_file
        self._load_policy()
        
    def _load_policy(self):
        """
        Load and parse the XACML policy file
        """
        try:
            logger.info(f"Loading policy from {self.policy_file}")
            self.policy_tree = ET.parse(self.policy_file)
            self.policy_root = self.policy_tree.getroot()
            logger.info("Policy loaded successfully")
        except Exception as e:
            logger.error(f"Error loading policy: {e}")
            raise
    
    def evaluate(self, request_xml):
        """
        Evaluate a XACML request against the policy
        Returns a simplified XACML response
        """
        try:
            logger.info("Evaluating XACML request")
            
            # Parse request XML
            request_root = ET.fromstring(request_xml)
            
            # Extract request attributes for easier access
            attributes = self._extract_attributes(request_root)
            
            # Simplified evaluation: check policies in order
            decision = self._evaluate_policies(attributes)
            
            # Create response XML
            response_xml = self._create_response(decision)
            
            logger.info(f"Evaluation complete, decision: {decision}")
            return response_xml
        
        except Exception as e:
            logger.error(f"Error evaluating request: {e}")
            return self._create_response("Indeterminate")
    
    def _extract_attributes(self, request_root):
        """
        Extract attributes from request XML for easier processing
        """
        attributes = {}
        
        # Process each attribute category
        for category_elem in request_root.findall('.//{*}Attributes'):
            category = category_elem.get('Category')
            
            if category not in attributes:
                attributes[category] = {}
                
            # Process each attribute in this category
            for attr_elem in category_elem.findall('.//{*}Attribute'):
                attr_id = attr_elem.get('AttributeId')
                
                # Get attribute value
                value_elem = attr_elem.find('.//{*}AttributeValue')
                if value_elem is not None:
                    data_type = value_elem.get('DataType').split('#')[-1]  # Get just the type name
                    value = value_elem.text
                    
                    # Convert value based on data type
                    if data_type == 'boolean':
                        value = value.lower() == 'true'
                    elif data_type in ('integer', 'double'):
                        value = float(value)
                        
                    attributes[category][attr_id] = value
        
        return attributes
    
    def _evaluate_policies(self, attributes):
        """
        Evaluate policies in the policy set
        """
        # Get policy combining algorithm from PolicySet
        policy_combining_alg = self.policy_root.get('PolicyCombiningAlgId').split(':')[-1]
        logger.debug(f"Policy combining algorithm: {policy_combining_alg}")
        
        # Get all policies in the policy set
        policies = self.policy_root.findall('.//{*}Policy')
        
        # For deny-unless-permit combining algorithm (default fallback)
        has_applicable_policy = False
        final_decision = "Deny"
        
        for policy in policies:
            policy_id = policy.get('PolicyId')
            
            # Check if policy applies based on Target
            if self._policy_applies(policy, attributes):
                logger.info(f"Evaluating policy: {policy_id}")
                has_applicable_policy = True
                
                # Get rule combining algorithm for this policy
                rule_combining_alg = policy.get('RuleCombiningAlgId').split(':')[-1]
                
                # Evaluate rules based on combining algorithm
                if rule_combining_alg == 'deny-unless-permit':
                    policy_decision = self._evaluate_deny_unless_permit(policy, attributes)
                elif rule_combining_alg == 'first-applicable':
                    policy_decision = self._evaluate_first_applicable(policy, attributes)
                else:
                    # Default to permit-overrides for other algorithms
                    policy_decision = self._evaluate_permit_overrides(policy, attributes)
                
                # Apply policy combining algorithm
                if policy_combining_alg == 'ordered-permit-overrides':
                    if policy_decision == "Permit":
                        return "Permit"
                elif policy_combining_alg == 'permit-overrides':
                    if policy_decision == "Permit":
                        return "Permit"
                elif policy_combining_alg == 'deny-overrides':
                    if policy_decision == "Deny":
                        return "Deny"
                    elif policy_decision == "Permit" and final_decision != "Deny":
                        final_decision = "Permit"
                elif policy_combining_alg == 'first-applicable':
                    if policy_decision in ("Permit", "Deny"):
                        return policy_decision
        
        if not has_applicable_policy:
            # If no policy applies, return NotApplicable
            return "NotApplicable"
        
        return final_decision
    
    def _policy_applies(self, policy, attributes):
        """
        Check if policy applies based on Target match
        """
        target = policy.find('.//{*}Target')
        
        # If no Target, the policy applies to all requests
        if target is None or len(list(target)) == 0:
            return True
        
        # Check AnyOf elements
        any_of_elements = target.findall('.//{*}AnyOf')
        if not any_of_elements:
            return True
            
        for any_of in any_of_elements:
            any_match = False
            
            # Check AllOf elements (within AnyOf)
            for all_of in any_of.findall('.//{*}AllOf'):
                all_match = True
                
                # Check Match elements (within AllOf)
                for match in all_of.findall('.//{*}Match'):
                    match_id = match.get('MatchId').split(':')[-1]
                    
                    # Get attribute value from policy
                    attr_value_elem = match.find('.//{*}AttributeValue')
                    policy_value = attr_value_elem.text
                    
                    # Get attribute designator
                    attr_desig = match.find('.//{*}AttributeDesignator')
                    category = attr_desig.get('Category')
                    attr_id = attr_desig.get('AttributeId')
                    
                    # Get request value
                    if category in attributes and attr_id in attributes[category]:
                        request_value = str(attributes[category][attr_id])
                        
                        # Perform match based on match type
                        if match_id == 'string-equal':
                            if policy_value != request_value:
                                all_match = False
                                break
                        elif match_id == 'boolean-equal':
                            if str(policy_value).lower() != str(request_value).lower():
                                all_match = False
                                break
                        elif match_id == 'string-regexp-match':
                            if not re.match(policy_value, request_value):
                                all_match = False
                                break
                    else:
                        # If attribute doesn't exist, no match
                        all_match = False
                        break
                
                if all_match:
                    any_match = True
                    break
            
            if not any_match:
                return False
        
        return True
    
    def _evaluate_deny_unless_permit(self, policy, attributes):
        """
        Implementation of deny-unless-permit rule combining algorithm
        """
        # Default is Deny unless a rule explicitly permits
        found_applicable_rule = False
        
        for rule in policy.findall('.//{*}Rule'):
            rule_id = rule.get('RuleId')
            effect = rule.get('Effect')
            
            # Check if rule applies based on Target
            if not self._rule_applies(rule, attributes):
                continue
                
            found_applicable_rule = True
            
            # Check rule condition
            if self._evaluate_condition(rule, attributes):
                logger.info(f"Rule {rule_id} evaluates to {effect}")
                if effect == "Permit":
                    return "Permit"
        
        return "Deny" if found_applicable_rule else "NotApplicable"
    
    def _evaluate_first_applicable(self, policy, attributes):
        """
        Implementation of first-applicable rule combining algorithm
        """
        found_applicable_rule = False
        
        for rule in policy.findall('.//{*}Rule'):
            rule_id = rule.get('RuleId')
            effect = rule.get('Effect')
            
            # Check if rule applies based on Target
            if not self._rule_applies(rule, attributes):
                continue
                
            found_applicable_rule = True
            
            # Check rule condition
            if self._evaluate_condition(rule, attributes):
                logger.info(f"Rule {rule_id} evaluates to {effect}")
                return effect
        
        # Default if no rule applies
        return "NotApplicable" if not found_applicable_rule else "Deny"
    
    def _evaluate_permit_overrides(self, policy, attributes):
        """
        Implementation of permit-overrides rule combining algorithm
        """
        found_deny = False
        found_applicable_rule = False
        
        for rule in policy.findall('.//{*}Rule'):
            rule_id = rule.get('RuleId')
            effect = rule.get('Effect')
            
            # Check if rule applies based on Target
            if not self._rule_applies(rule, attributes):
                continue
                
            found_applicable_rule = True
            
            # Check rule condition
            if self._evaluate_condition(rule, attributes):
                logger.info(f"Rule {rule_id} evaluates to {effect}")
                if effect == "Permit":
                    return "Permit"
                elif effect == "Deny":
                    found_deny = True
        
        if found_deny:
            return "Deny"
        
        return "NotApplicable" if not found_applicable_rule else "Deny"
    
    def _rule_applies(self, rule, attributes):
        """
        Check if rule applies based on Target
        """
        target = rule.find('.//{*}Target')
        
        # If no Target, the rule applies to all requests
        if target is None or len(list(target)) == 0:
            return True
        
        # Check AnyOf elements
        any_of_elements = target.findall('.//{*}AnyOf')
        if not any_of_elements:
            return True
            
        for any_of in any_of_elements:
            any_match = False
            
            # Check AllOf elements (within AnyOf)
            for all_of in any_of.findall('.//{*}AllOf'):
                all_match = True
                
                # Check Match elements (within AllOf)
                for match in all_of.findall('.//{*}Match'):
                    match_id = match.get('MatchId').split(':')[-1]
                    
                    # Get attribute value from rule
                    attr_value_elem = match.find('.//{*}AttributeValue')
                    rule_value = attr_value_elem.text
                    
                    # Get attribute designator
                    attr_desig = match.find('.//{*}AttributeDesignator')
                    category = attr_desig.get('Category')
                    attr_id = attr_desig.get('AttributeId')
                    
                    # Get request value
                    if category in attributes and attr_id in attributes[category]:
                        request_value = str(attributes[category][attr_id])
                        
                        # Perform match based on match type
                        if match_id == 'string-equal':
                            if rule_value != request_value:
                                all_match = False
                                break
                        elif match_id == 'boolean-equal':
                            if str(rule_value).lower() != str(request_value).lower():
                                all_match = False
                                break
                        elif match_id == 'string-regexp-match':
                            if not re.match(rule_value, request_value):
                                all_match = False
                                break
                    else:
                        # If attribute doesn't exist, no match
                        all_match = False
                        break
                
                if all_match:
                    any_match = True
                    break
            
            if not any_match:
                return False
        
        return True
    
    def _evaluate_condition(self, rule, attributes):
        """
        Evaluate a rule condition
        """
        condition = rule.find('.//{*}Condition')
        
        # If no condition, the rule applies
        if condition is None:
            return True
        
        # Get the Apply function
        apply_elem = condition.find('.//{*}Apply')
        if apply_elem is None:
            return True
        
        return self._evaluate_apply(apply_elem, attributes)
    
    def _evaluate_apply(self, apply_elem, attributes):
        """
        Evaluate an Apply element in a condition
        """
        function_id = apply_elem.get('FunctionId').split(':')[-1]
        
        # Handle different XACML functions
        if function_id == 'and':
            # Evaluate all child Apply elements, return true if all are true
            for child_apply in apply_elem.findall('.//{*}Apply'):
                if child_apply.getparent() == apply_elem:  # Only direct children
                    if not self._evaluate_apply(child_apply, attributes):
                        return False
            return True
            
        elif function_id == 'or':
            # Evaluate all child Apply elements, return true if any is true
            for child_apply in apply_elem.findall('.//{*}Apply'):
                if child_apply.getparent() == apply_elem:  # Only direct children
                    if self._evaluate_apply(child_apply, attributes):
                        return True
            return False
            
        elif function_id == 'boolean-equal':
            # Get the two children
            children = list(apply_elem)
            attr_value_elem = None
            attr_desig = None
            
            for child in children:
                if child.tag.endswith('AttributeValue'):
                    attr_value_elem = child
                elif child.tag.endswith('AttributeDesignator'):
                    attr_desig = child
            
            if attr_value_elem is not None and attr_desig is not None:
                policy_value = attr_value_elem.text.lower() == 'true'
                category = attr_desig.get('Category')
                attr_id = attr_desig.get('AttributeId')
                
                # Get request value
                if category in attributes and attr_id in attributes[category]:
                    request_value = attributes[category][attr_id]
                    return policy_value == request_value
            
            return False
            
        elif function_id == 'string-equal':
            # Get the two children
            children = list(apply_elem)
            attr_value_elem = None
            attr_desig = None
            
            for child in children:
                if child.tag.endswith('AttributeValue'):
                    attr_value_elem = child
                elif child.tag.endswith('AttributeDesignator'):
                    attr_desig = child
            
            if attr_value_elem is not None and attr_desig is not None:
                policy_value = attr_value_elem.text
                category = attr_desig.get('Category')
                attr_id = attr_desig.get('AttributeId')
                
                # Get request value
                if category in attributes and attr_id in attributes[category]:
                    request_value = attributes[category][attr_id]
                    return policy_value == str(request_value)
            
            return False
            
        elif function_id in ['double-less-than', 'integer-less-than']:
            # Get the two children
            children = list(apply_elem)
            
            # Get attribute designator and value
            attr_desig = None
            attr_value = None
            
            for child in children:
                if child.tag.endswith('AttributeDesignator'):
                    attr_desig = child
                elif child.tag.endswith('AttributeValue'):
                    attr_value = child
            
            if attr_desig is not None and attr_value is not None:
                category = attr_desig.get('Category')
                attr_id = attr_desig.get('AttributeId')
                policy_value = float(attr_value.text)
                
                # Get request value
                if category in attributes and attr_id in attributes[category]:
                    request_value = float(attributes[category][attr_id])
                    return request_value < policy_value
            
            return False
            
        elif function_id in ['double-greater-than', 'integer-greater-than']:
            # Get the two children
            children = list(apply_elem)
            
            # Get attribute designator and value
            attr_desig = None
            attr_value = None
            
            for child in children:
                if child.tag.endswith('AttributeDesignator'):
                    attr_desig = child
                elif child.tag.endswith('AttributeValue'):
                    attr_value = child
            
            if attr_desig is not None and attr_value is not None:
                category = attr_desig.get('Category')
                attr_id = attr_desig.get('AttributeId')
                policy_value = float(attr_value.text)
                
                # Get request value
                if category in attributes and attr_id in attributes[category]:
                    request_value = float(attributes[category][attr_id])
                    return request_value > policy_value
            
            return False
            
        elif function_id in ['double-less-than-or-equal', 'integer-less-than-or-equal']:
            # Get the two children
            children = list(apply_elem)
            
            # Get attribute designator and value
            attr_desig = None
            attr_value = None
            
            for child in children:
                if child.tag.endswith('AttributeDesignator'):
                    attr_desig = child
                elif child.tag.endswith('AttributeValue'):
                    attr_value = child
            
            if attr_desig is not None and attr_value is not None:
                category = attr_desig.get('Category')
                attr_id = attr_desig.get('AttributeId')
                policy_value = float(attr_value.text)
                
                # Get request value
                if category in attributes and attr_id in attributes[category]:
                    request_value = float(attributes[category][attr_id])
                    return request_value <= policy_value
            
            return False
            
        elif function_id in ['double-greater-than-or-equal', 'integer-greater-than-or-equal']:
            # Get the two children
            children = list(apply_elem)
            
            # Get attribute designator and value
            attr_desig = None
            attr_value = None
            
            for child in children:
                if child.tag.endswith('AttributeDesignator'):
                    attr_desig = child
                elif child.tag.endswith('AttributeValue'):
                    attr_value = child
            
            if attr_desig is not None and attr_value is not None:
                category = attr_desig.get('Category')
                attr_id = attr_desig.get('AttributeId')
                policy_value = float(attr_value.text)
                
                # Get request value
                if category in attributes and attr_id in attributes[category]:
                    request_value = float(attributes[category][attr_id])
                    return request_value >= policy_value
            
            return False
        
        # Default to false for unsupported functions
        logger.warning(f"Unsupported function: {function_id}")
        return False
    
    def _create_response(self, decision):
        """
        Create a XACML response with the given decision
        """
        root = ET.Element("Response", xmlns="urn:oasis:names:tc:xacml:3.0:core:schema:wd-17")
        result = ET.SubElement(root, "Result")
        
        # Add Decision element
        decision_elem = ET.SubElement(result, "Decision")
        decision_elem.text = decision
        
        # Convert to string
        return ET.tostring(root, encoding='utf8', method='xml').decode()

# Test the PDP
if __name__ == "__main__":
    # Example policy file
    policy_file = "../policies/FAADroneRules.xml"
    
    # Create PDP
    pdp = FileBasedPDP(policy_file)
    
    # Example request
    request = """
    <Request xmlns="urn:oasis:names:tc:xacml:3.0:core:schema:wd-17">
        <Attributes Category="urn:oasis:names:tc:xacml:1.0:subject-category:access-subject">
            <Attribute AttributeId="has-completed-night-training" IncludeInResult="true">
                <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#boolean">true</AttributeValue>
            </Attribute>
        </Attributes>
        <Attributes Category="urn:oasis:names:tc:xacml:3.0:attribute-category:resource">
            <Attribute AttributeId="has-anti-collision-lighting" IncludeInResult="true">
                <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#boolean">true</AttributeValue>
            </Attribute>
        </Attributes>
        <Attributes Category="urn:oasis:names:tc:xacml:3.0:attribute-category:environment">
            <Attribute AttributeId="time-of-day" IncludeInResult="true">
                <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">night</AttributeValue>
            </Attribute>
        </Attributes>
    </Request>
    """
    
    # Evaluate request
    response = pdp.evaluate(request)
    print(response)