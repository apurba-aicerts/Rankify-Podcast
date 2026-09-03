"""
Pydantic to Gemini Schema Converter

This module provides utility functions for converting Pydantic models to Gemini's
OpenAPI 3.0 Schema format for structured output enforcement.

Usage:
    from helpers.pydantic_to_gemini_schema import pydantic_to_gemini_schema
    from pydantic import BaseModel
    
    class MyModel(BaseModel):
        name: str
        age: int
    
    schema = pydantic_to_gemini_schema(MyModel)
"""

from typing import Any, Dict
from pydantic import BaseModel


def pydantic_to_gemini_schema(model: type[BaseModel]) -> Dict[str, Any]:
    """
    Convert a Pydantic model to Gemini's OpenAPI 3.0 Schema format.
    
    This function generates the responseSchema configuration that Gemini API expects,
    which enforces structured output at the API level rather than relying on prompts.
    
    Benefits:
    - Enforces structure at the API level for better reliability
    - Reduces hallucination of incorrect formats
    - Provides automatic type validation
    - Ensures consistent property ordering in the output
    
    See: https://ai.google.dev/gemini-api/docs/structured-output
    
    Args:
        model: A Pydantic BaseModel class
        
    Returns:
        dict: OpenAPI 3.0 compatible schema for Gemini API
        
    Example:
        >>> from pydantic import BaseModel, Field
        >>> from typing import List
        >>> 
        >>> class Person(BaseModel):
        ...     name: str = Field(description="Person's name")
        ...     age: int = Field(description="Person's age")
        >>> 
        >>> schema = pydantic_to_gemini_schema(Person)
        >>> print(schema['type'])
        OBJECT
    """
    json_schema = model.model_json_schema()
    
    # Store definitions for resolving $ref references
    definitions = json_schema.get("$defs", {})
    
    def resolve_ref(ref: str) -> Dict[str, Any]:
        """
        Resolve a $ref reference to its definition.
        
        Args:
            ref: Reference string like "#/$defs/MyModel"
            
        Returns:
            dict: The referenced schema definition
        """
        if ref.startswith("#/$defs/"):
            ref_name = ref.split("/")[-1]
            return definitions.get(ref_name, {})
        return {}
    
    def convert_type(prop_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert JSON Schema types to Gemini's OpenAPI format.
        
        Args:
            prop_schema: JSON Schema property definition
            
        Returns:
            dict: Gemini-compatible schema definition
        """
        gemini_schema: Dict[str, Any] = {}
        
        # Handle $ref (nested model references)
        if "$ref" in prop_schema:
            resolved = resolve_ref(prop_schema["$ref"])
            return convert_type(resolved)
        
        # Handle allOf (used for model inheritance/composition)
        if "allOf" in prop_schema:
            merged_schema = {}
            for sub_schema in prop_schema["allOf"]:
                if "$ref" in sub_schema:
                    resolved = resolve_ref(sub_schema["$ref"])
                    merged_schema.update(resolved)
                else:
                    merged_schema.update(sub_schema)
            return convert_type(merged_schema)
        
        # Handle type
        if "type" in prop_schema:
            json_type = prop_schema["type"]
            type_mapping = {
                "string": "STRING",
                "number": "NUMBER",
                "integer": "INTEGER",
                "boolean": "BOOLEAN",
                "array": "ARRAY",
                "object": "OBJECT"
            }
            gemini_schema["type"] = type_mapping.get(json_type, "STRING")
        
        # Handle arrays
        if gemini_schema.get("type") == "ARRAY" and "items" in prop_schema:
            gemini_schema["items"] = convert_type(prop_schema["items"])
        
        # Handle objects
        if gemini_schema.get("type") == "OBJECT":
            if "properties" in prop_schema:
                gemini_schema["properties"] = {}
                property_order = []
                for prop_name, prop_def in prop_schema["properties"].items():
                    gemini_schema["properties"][prop_name] = convert_type(prop_def)
                    property_order.append(prop_name)
                
                # Add propertyOrdering for consistent output
                if property_order:
                    gemini_schema["propertyOrdering"] = property_order
            
            # Handle required fields
            if "required" in prop_schema:
                gemini_schema["required"] = prop_schema["required"]
        
        # Handle enums
        if "enum" in prop_schema:
            gemini_schema["enum"] = prop_schema["enum"]
        
        # Handle description
        if "description" in prop_schema:
            gemini_schema["description"] = prop_schema["description"]
        
        # Handle nullable (anyOf with null type)
        if "anyOf" in prop_schema:
            for item in prop_schema["anyOf"]:
                if item.get("type") == "null":
                    gemini_schema["nullable"] = True
                else:
                    # Merge the non-null schema
                    gemini_schema.update(convert_type(item))
        
        # Handle default values by marking as nullable if present
        if "default" in prop_schema and prop_schema["default"] is None:
            gemini_schema["nullable"] = True
        
        # Handle format
        if "format" in prop_schema:
            gemini_schema["format"] = prop_schema["format"]
        
        return gemini_schema       
    
    return convert_type(json_schema)
