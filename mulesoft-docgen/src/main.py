#!/usr/bin/env python
"""
MuleSoft Documentation Generator.

This script generates HTML documentation from MuleSoft XML configuration files or JAR files.

Usage:
    python src/main.py --input=/path/to/xml/files --output=/path/to/docs --name="Interface Name"
    python src/main.py --input=/path/to/mulesoft.jar --output=/path/to/docs --name="Interface Name"
"""

import os
import sys
import argparse
import shutil
import tempfile
from pathlib import Path
import zipfile
import traceback
from jinja2.exceptions import TemplateSyntaxError

from .parser.xml_parser import XmlParser
from .model.interface import Interface
from .generator.html_generator import generate_html

def extract_jar_contents(jar_path):
    """
    Extract XML files from a JAR file to a temporary directory.
    
    Args:
        jar_path: Path to JAR file
        
    Returns:
        Path to temporary directory containing extracted files
    """
    temp_dir = tempfile.mkdtemp()
    print(f"Extracting JAR to temporary directory: {temp_dir}")
    
    try:
        with zipfile.ZipFile(jar_path, 'r') as jar:
            # Extract all files from the JAR
            jar.extractall(temp_dir)
            
            # Look for META-INF/mule-src directory which often contains source XML
            mule_src = os.path.join(temp_dir, "META-INF", "mule-src")
            if os.path.exists(mule_src):
                print(f"Found mule-src directory: {mule_src}")
                
        return temp_dir
    except Exception as e:
        print(f"Error extracting JAR: {e}")
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
        raise

def parse_xml_files(xml_files, interface_name):
    """Parse XML files and return an Interface object."""
    parser = XmlParser()
    for xml_file in xml_files:
        parser.parse_file(xml_file)
    
    interface = Interface(interface_name)
    interface.flows = parser.get_flows()
    return interface

def main():
    parser = argparse.ArgumentParser(description='Generate documentation for MuleSoft interfaces')
    parser.add_argument('--input', required=True, help='Input directory containing MuleSoft source files')
    parser.add_argument('--output', required=True, help='Output directory for generated documentation')
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output, exist_ok=True)
    
    # Find all XML files in the input directory
    xml_files = []
    for root, _, files in os.walk(args.input):
        for file in files:
            if file.endswith('.xml'):
                xml_files.append(os.path.join(root, file))
    
    print(f"Found {len(xml_files)} XML files in directory")
    
    # Parse XML files
    print("Parsing XML files...")
    interface = parse_xml_files(xml_files, "MuleSoft Interface")
    
    # Add XML files to interface
    interface.xml_files = xml_files
    
    # Generate HTML documentation
    print("Generating HTML documentation...")
    generate_html(interface, args.output, args.input)
    
    print(f"Documentation generated in {args.output}")

if __name__ == '__main__':
    main() 