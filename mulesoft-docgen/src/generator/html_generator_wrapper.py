"""
HTML Generator Wrapper Module

This module provides a clean interface to the HtmlGenerator class,
avoiding the import-time indentation errors in the original module.
"""

import os
import sys
import importlib.util

# Define the main HtmlGenerator class from the original module
class HtmlGenerator:
    """
    HTML documentation generator for MuleSoft interfaces.
    This is a wrapper for the original HtmlGenerator class.
    """
    
    def __init__(self, template_dir=None):
        """
        Initialize the HTML generator by dynamically loading the original implementation.
        
        Args:
            template_dir: Directory containing Jinja2 templates
        """
        # Get the path to the original module
        module_path = os.path.join(os.path.dirname(__file__), 'html_generator.py')
        
        # Dynamically load the module's content
        with open(module_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract only the HtmlGenerator class code
        class_start = content.find("class HtmlGenerator")
        generate_html_pos = content.rfind("def generate_html")
        
        # Only keep the class code, not the standalone function at the end
        class_code = content[class_start:generate_html_pos].strip()
        
        # Create a new namespace and execute the class definition
        namespace = {}
        exec(class_code, namespace)
        
        # Get the class from the namespace
        original_class = namespace['HtmlGenerator']
        
        # Create an instance of the original class
        self._original = original_class(template_dir)
        
        # Mirror the original instance's attributes
        for attr_name in dir(self._original):
            if not attr_name.startswith('_') or attr_name == '__init__':
                setattr(self, attr_name, getattr(self._original, attr_name))
    
    def generate(self, interface, output_dir, xml_dir=None, jar_dir=None):
        """
        Generate HTML documentation for the interface.
        
        Args:
            interface: The interface to generate documentation for.
            output_dir: The output directory to write the documentation to.
            xml_dir: The directory containing the XML files to parse.
            jar_dir: The directory containing the JAR files to parse.
        """
        self._original.generate(interface, output_dir, xml_dir, jar_dir)


# Define the generate_html function that was at the end of the original module
def generate_html(interface, output_dir, xml_dir, jar_dir=None):
    """
    Generate HTML documentation for a MuleSoft interface.
    
    Args:
        interface: Interface to document
        output_dir: Directory to write documentation
        xml_dir: Directory containing XML files
        jar_dir: Directory containing extracted JAR contents (optional)
    """
    generator = HtmlGenerator()
    generator.generate(interface, output_dir, xml_dir, jar_dir) 