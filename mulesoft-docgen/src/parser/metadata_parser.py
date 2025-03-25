"""
Metadata parser for MuleSoft applications.
This module extracts metadata from META-INF and pom.xml files.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from lxml import etree
import xml.etree.ElementTree as ET
import json
from datetime import datetime

class MetadataParser:
    """Parse and extract metadata from MuleSoft applications."""
    
    def __init__(self, jar_dir: str):
        """
        Initialize the metadata parser.
        
        Args:
            jar_dir: Directory containing the extracted JAR contents
        """
        self.jar_dir = jar_dir
        self.meta_inf_dir = os.path.join(jar_dir, 'META-INF')
        
    def extract_metadata(self) -> Dict[str, Any]:
        """
        Extract all available metadata.
        
        Returns:
            Dictionary with extracted metadata
        """
        result = {
            'application': {},
            'maven': self.extract_maven_info(),
            'mule': self.extract_mule_info(),
            'build_info': self.extract_build_info(),
            'dependencies': self.extract_dependencies()
        }
        
        # Extract MANIFEST.MF info
        manifest_info = self.extract_manifest_info()
        if manifest_info:
            result['application'].update(manifest_info)
            
        # Extract mule-artifact.json info
        artifact_info = self.extract_artifact_info()
        if artifact_info:
            result['application'].update(artifact_info)
            
        return result
        
    def extract_manifest_info(self) -> Optional[Dict[str, str]]:
        """
        Extract information from MANIFEST.MF.
        
        Returns:
            Dictionary with manifest information or None if file not found
        """
        manifest_path = os.path.join(self.meta_inf_dir, 'MANIFEST.MF')
        
        if not os.path.exists(manifest_path):
            return None
            
        info = {}
        
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                current_key = None
                current_value = ""
                
                for line in f:
                    line = line.rstrip('\n')
                    
                    # Handle continuation lines (starting with space)
                    if line.startswith(' '):
                        if current_key:
                            current_value += line.strip()
                        continue
                    
                    # Process previous key-value pair
                    if current_key:
                        info[current_key] = current_value
                        current_key = None
                        current_value = ""
                    
                    # Parse new key-value pair
                    if ':' in line:
                        key, value = line.split(':', 1)
                        current_key = key.strip()
                        current_value = value.strip()
                
                # Add last key-value pair
                if current_key:
                    info[current_key] = current_value
            
            # Format certain fields
            if 'Build-Date' in info:
                try:
                    build_date = datetime.strptime(info['Build-Date'], '%Y-%m-%dT%H:%M:%SZ')
                    info['Build-Date-Formatted'] = build_date.strftime('%Y-%m-%d %H:%M:%S UTC')
                except:
                    pass
            
            return info
            
        except Exception as e:
            print(f"Error parsing MANIFEST.MF: {e}")
            return None
    
    def extract_maven_info(self) -> Dict[str, Any]:
        """
        Extract Maven project information from pom.xml.
        
        Returns:
            Dictionary with Maven project information
        """
        pom_path = os.path.join(self.meta_inf_dir, 'maven')
        
        if not os.path.exists(pom_path):
            return {}
            
        # Find pom.xml in subdirectories
        pom_files = []
        for root, _, files in os.walk(pom_path):
            for file in files:
                if file == 'pom.xml':
                    pom_files.append(os.path.join(root, file))
        
        if not pom_files:
            return {}
            
        # Parse the first pom.xml found
        try:
            tree = ET.parse(pom_files[0])
            root = tree.getroot()
            
            # Extract namespace
            ns_match = re.match(r'{(.*)}', root.tag)
            ns = ns_match.group(1) if ns_match else ''
            
            # Function to find element with namespace
            def find_elem(parent, tag):
                if ns:
                    return parent.find(f'{{{ns}}}{tag}')
                else:
                    return parent.find(tag)
            
            # Extract basic info
            info = {}
            
            # Project coordinates
            group_id = find_elem(root, 'groupId')
            artifact_id = find_elem(root, 'artifactId')
            version = find_elem(root, 'version')
            
            if group_id is not None:
                info['groupId'] = group_id.text
            if artifact_id is not None:
                info['artifactId'] = artifact_id.text
            if version is not None:
                info['version'] = version.text
                
            # Project metadata
            name = find_elem(root, 'name')
            description = find_elem(root, 'description')
            
            if name is not None:
                info['name'] = name.text
            if description is not None:
                info['description'] = description.text
                
            # Extract parent info
            parent_elem = find_elem(root, 'parent')
            if parent_elem is not None:
                parent = {}
                parent_group_id = find_elem(parent_elem, 'groupId')
                parent_artifact_id = find_elem(parent_elem, 'artifactId')
                parent_version = find_elem(parent_elem, 'version')
                
                if parent_group_id is not None:
                    parent['groupId'] = parent_group_id.text
                if parent_artifact_id is not None:
                    parent['artifactId'] = parent_artifact_id.text
                if parent_version is not None:
                    parent['version'] = parent_version.text
                    
                if parent:
                    info['parent'] = parent
            
            return info
            
        except Exception as e:
            print(f"Error parsing pom.xml: {e}")
            return {}
    
    def extract_mule_info(self) -> Dict[str, Any]:
        """
        Extract Mule-specific information.
        
        Returns:
            Dictionary with Mule information
        """
        mule_info = {}
        
        # Check for mule-plugin.json
        plugin_path = os.path.join(self.meta_inf_dir, 'mule-plugin.json')
        if os.path.exists(plugin_path):
            try:
                with open(plugin_path, 'r', encoding='utf-8') as f:
                    plugin_info = json.load(f)
                mule_info['plugin'] = plugin_info
            except Exception as e:
                print(f"Error parsing mule-plugin.json: {e}")
        
        return mule_info
    
    def extract_artifact_info(self) -> Dict[str, Any]:
        """
        Extract information from mule-artifact.json.
        
        Returns:
            Dictionary with artifact information
        """
        artifact_path = os.path.join(self.meta_inf_dir, 'mule-artifact.json')
        
        if not os.path.exists(artifact_path):
            return {}
            
        try:
            with open(artifact_path, 'r', encoding='utf-8') as f:
                artifact_info = json.load(f)
                
            # Format and clean up information
            result = {}
            
            if 'name' in artifact_info:
                result['name'] = artifact_info['name']
                
            if 'minMuleVersion' in artifact_info:
                result['muleVersion'] = artifact_info['minMuleVersion']
                
            if 'requiredProduct' in artifact_info:
                result['product'] = artifact_info['requiredProduct']
                
            if 'classLoaderModelLoaderDescriptor' in artifact_info:
                descriptor = artifact_info['classLoaderModelLoaderDescriptor']
                if 'id' in descriptor:
                    result['classLoaderType'] = descriptor['id']
                    
            if 'bundleDescriptorLoader' in artifact_info:
                descriptor = artifact_info['bundleDescriptorLoader']
                if 'id' in descriptor:
                    result['bundleType'] = descriptor['id']
                    
            # Include configs if available
            if 'configs' in artifact_info:
                result['configFiles'] = artifact_info['configs']
                
            # Include secure properties if available
            if 'secureProperties' in artifact_info:
                result['secureProperties'] = artifact_info['secureProperties']
                
            return result
            
        except Exception as e:
            print(f"Error parsing mule-artifact.json: {e}")
            return {}
    
    def extract_build_info(self) -> Dict[str, Any]:
        """
        Extract build information.
        
        Returns:
            Dictionary with build information
        """
        # Check for build properties file
        properties_path = os.path.join(self.meta_inf_dir, 'build.properties')
        if os.path.exists(properties_path):
            try:
                properties = {}
                with open(properties_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            key, value = line.split('=', 1)
                            properties[key.strip()] = value.strip()
                return properties
            except Exception as e:
                print(f"Error parsing build.properties: {e}")
        
        return {}
    
    def extract_dependencies(self) -> List[Dict[str, str]]:
        """
        Extract dependency information.
        
        Returns:
            List of dependencies
        """
        dependencies = []
        
        # Try to find maven dependencies
        pom_properties_dir = os.path.join(self.meta_inf_dir, 'maven')
        
        if not os.path.exists(pom_properties_dir):
            return dependencies
            
        # Find all pom.properties files
        for root, _, files in os.walk(pom_properties_dir):
            for file in files:
                if file == 'pom.properties':
                    prop_path = os.path.join(root, file)
                    try:
                        # Read properties file
                        props = {}
                        with open(prop_path, 'r', encoding='utf-8') as f:
                            for line in f:
                                line = line.strip()
                                if line and not line.startswith('#'):
                                    key, value = line.split('=', 1)
                                    props[key.strip()] = value.strip()
                        
                        # Extract dependency info
                        if 'groupId' in props and 'artifactId' in props:
                            dep = {
                                'groupId': props['groupId'],
                                'artifactId': props['artifactId']
                            }
                            
                            if 'version' in props:
                                dep['version'] = props['version']
                                
                            dependencies.append(dep)
                    except Exception as e:
                        print(f"Error parsing {prop_path}: {e}")
        
        return dependencies

def extract_metadata(jar_dir: str) -> Dict[str, Any]:
    """
    Extract metadata from a JAR directory.
    
    Args:
        jar_dir: Directory containing the extracted JAR contents
        
    Returns:
        Dictionary with extracted metadata
    """
    parser = MetadataParser(jar_dir)
    return parser.extract_metadata() 