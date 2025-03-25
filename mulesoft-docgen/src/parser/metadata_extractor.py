"""
Module for extracting metadata from MuleSoft applications.

This module extracts metadata from MuleSoft JAR files and XML configurations,
including Maven project information, dependencies, and build details.
"""

import os
import re
import json
import zipfile
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from lxml import etree
import xml.etree.ElementTree as ET
from xml.dom import minidom


class MetadataExtractor:
    """Extracts metadata from MuleSoft applications."""
    
    def __init__(self):
        """Initialize the metadata extractor."""
        self.metadata = {
            'app_info': {},
            'maven_info': {},
            'build_info': {},
            'dependencies': [],
            'plugins': [],
            'secure_properties': []
        }
    
    def extract_from_jar(self, jar_path: str) -> Dict[str, Any]:
        """
        Extract metadata from a MuleSoft JAR file.
        
        Args:
            jar_path: Path to the JAR file
            
        Returns:
            Dictionary containing metadata
        """
        if not os.path.exists(jar_path):
            raise FileNotFoundError(f"JAR file not found: {jar_path}")
        
        with zipfile.ZipFile(jar_path) as jar:
            # Extract application info from manifest
            self._extract_manifest(jar)
            
            # Extract Maven info from pom.xml
            self._extract_pom_info(jar)
            
            # Extract secure properties
            self._extract_secure_properties(jar)
            
        return self.metadata
    
    def extract_from_directory(self, dir_path: str) -> Dict[str, Any]:
        """
        Extract metadata from a MuleSoft project directory.
        
        Args:
            dir_path: Path to the project directory
            
        Returns:
            Dictionary containing metadata
        """
        if not os.path.exists(dir_path):
            raise FileNotFoundError(f"Directory not found: {dir_path}")
        
        # Extract Maven info from pom.xml
        pom_path = os.path.join(dir_path, 'pom.xml')
        if os.path.exists(pom_path):
            self._extract_pom_from_file(pom_path)
        
        # Look for secure properties files
        for root, _, files in os.walk(dir_path):
            for file in files:
                if file.endswith('.secure.properties') or file.endswith('.properties'):
                    self._extract_properties_from_file(os.path.join(root, file))
        
        # Extract API specifications if available
        api_dir = os.path.join(dir_path, 'src', 'main', 'resources', 'api')
        if os.path.exists(api_dir):
            self._extract_api_specs(api_dir)
        
        return self.metadata
    
    def _extract_manifest(self, jar: zipfile.ZipFile) -> None:
        """
        Extract metadata from the JAR manifest.
        
        Args:
            jar: ZipFile object for the JAR
        """
        try:
            if 'META-INF/MANIFEST.MF' in jar.namelist():
                manifest_data = jar.read('META-INF/MANIFEST.MF').decode('utf-8')
                
                # Parse manifest entries
                for line in manifest_data.splitlines():
                    if not line or ': ' not in line:
                        continue
                    
                    key, value = line.split(': ', 1)
                    if key == 'Implementation-Title':
                        self.metadata['app_info']['title'] = value
                    elif key == 'Implementation-Version':
                        self.metadata['app_info']['version'] = value
                    elif key == 'Built-By':
                        self.metadata['build_info']['built_by'] = value
                    elif key == 'Build-Jdk':
                        self.metadata['build_info']['build_jdk'] = value
                    elif key == 'Created-By':
                        self.metadata['build_info']['created_by'] = value
                    elif key == 'Build-Date':
                        self.metadata['build_info']['build_date'] = value
        except Exception as e:
            print(f"Error reading manifest: {str(e)}")
    
    def _extract_pom_info(self, jar: zipfile.ZipFile) -> None:
        """
        Extract Maven project information from pom.xml in a JAR.
        
        Args:
            jar: ZipFile object for the JAR
        """
        try:
            pom_files = [name for name in jar.namelist() if name.endswith('pom.xml')]
            
            if pom_files:
                # Choose the root pom.xml if available, otherwise just use the first one
                pom_path = next((f for f in pom_files if f.count('/') <= 1), pom_files[0])
                pom_content = jar.read(pom_path).decode('utf-8')
                
                self._parse_pom_content(pom_content)
        except Exception as e:
            print(f"Error extracting POM info: {str(e)}")
    
    def _extract_pom_from_file(self, file_path: str) -> None:
        """
        Extract Maven project information from a pom.xml file.
        
        Args:
            file_path: Path to the pom.xml file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                pom_content = f.read()
                
            self._parse_pom_content(pom_content)
        except Exception as e:
            print(f"Error reading POM file: {str(e)}")
    
    def _parse_pom_content(self, pom_content: str) -> None:
        """
        Parse Maven POM XML content.
        
        Args:
            pom_content: POM XML content as string
        """
        try:
            # Parse XML safely
            root = ET.fromstring(pom_content)
            
            # Define XML namespaces
            ns = {'m': 'http://maven.apache.org/POM/4.0.0'}
            
            # Extract groupId, artifactId, version
            group_id = self._find_element_text(root, './/m:groupId', ns)
            artifact_id = self._find_element_text(root, './/m:artifactId', ns)
            version = self._find_element_text(root, './/m:version', ns)
            name = self._find_element_text(root, './/m:name', ns)
            description = self._find_element_text(root, './/m:description', ns)
            
            # Update metadata
            self.metadata['maven_info'] = {
                'group_id': group_id,
                'artifact_id': artifact_id,
                'version': version,
                'name': name,
                'description': description
            }
            
            # Extract parent info if present
            parent = root.find('.//m:parent', ns)
            if parent is not None:
                parent_group_id = self._find_element_text(parent, './m:groupId', ns)
                parent_artifact_id = self._find_element_text(parent, './m:artifactId', ns)
                parent_version = self._find_element_text(parent, './m:version', ns)
                
                self.metadata['maven_info']['parent'] = {
                    'group_id': parent_group_id,
                    'artifact_id': parent_artifact_id,
                    'version': parent_version
                }
            
            # Extract properties
            properties_elem = root.find('.//m:properties', ns)
            if properties_elem is not None:
                properties = {}
                for prop in properties_elem:
                    tag = prop.tag.split('}')[-1] if '}' in prop.tag else prop.tag
                    properties[tag] = prop.text
                
                if properties:
                    self.metadata['maven_info']['properties'] = properties
            
            # Extract dependencies
            dependencies = []
            deps_elem = root.find('.//m:dependencies', ns)
            if deps_elem is not None:
                for dep in deps_elem.findall('./m:dependency', ns):
                    dep_info = {
                        'group_id': self._find_element_text(dep, './m:groupId', ns),
                        'artifact_id': self._find_element_text(dep, './m:artifactId', ns),
                        'version': self._find_element_text(dep, './m:version', ns)
                    }
                    
                    # Optional dependency attributes
                    scope = self._find_element_text(dep, './m:scope', ns)
                    if scope:
                        dep_info['scope'] = scope
                    
                    classifier = self._find_element_text(dep, './m:classifier', ns)
                    if classifier:
                        dep_info['classifier'] = classifier
                    
                    dependencies.append(dep_info)
            
            self.metadata['dependencies'] = dependencies
            
            # Extract plugins
            plugins = []
            build_elem = root.find('.//m:build', ns)
            if build_elem is not None:
                plugins_elem = build_elem.find('./m:plugins', ns)
                if plugins_elem is not None:
                    for plugin in plugins_elem.findall('./m:plugin', ns):
                        plugin_info = {
                            'group_id': self._find_element_text(plugin, './m:groupId', ns),
                            'artifact_id': self._find_element_text(plugin, './m:artifactId', ns),
                            'version': self._find_element_text(plugin, './m:version', ns)
                        }
                        
                        # Extract plugin configuration
                        config_elem = plugin.find('./m:configuration', ns)
                        if config_elem is not None:
                            configuration = {}
                            for config in config_elem:
                                tag = config.tag.split('}')[-1] if '}' in config.tag else config.tag
                                configuration[tag] = config.text
                            
                            if configuration:
                                plugin_info['configuration'] = configuration
                        
                        plugins.append(plugin_info)
            
            self.metadata['plugins'] = plugins
            
        except Exception as e:
            print(f"Error parsing POM content: {str(e)}")
    
    def _find_element_text(self, parent, xpath, namespaces=None) -> Optional[str]:
        """
        Find and extract text from an XML element.
        
        Args:
            parent: Parent element to search from
            xpath: XPath expression
            namespaces: XML namespaces
            
        Returns:
            Text content of the element or None
        """
        element = parent.find(xpath, namespaces)
        return element.text if element is not None and element.text else None
    
    def _extract_secure_properties(self, jar: zipfile.ZipFile) -> None:
        """
        Extract secure properties from properties files in a JAR.
        
        Args:
            jar: ZipFile object for the JAR
        """
        try:
            # Look for .properties files
            property_files = [name for name in jar.namelist() if
                               name.endswith('.properties') or 
                               name.endswith('.secure.properties')]
            
            for prop_file in property_files:
                try:
                    content = jar.read(prop_file).decode('utf-8')
                    
                    # Process properties
                    self._process_properties(content, os.path.basename(prop_file))
                except Exception as e:
                    print(f"Error reading property file {prop_file}: {str(e)}")
        except Exception as e:
            print(f"Error extracting secure properties: {str(e)}")
    
    def _extract_properties_from_file(self, file_path: str) -> None:
        """
        Extract properties from a file.
        
        Args:
            file_path: Path to the properties file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            self._process_properties(content, os.path.basename(file_path))
        except Exception as e:
            print(f"Error processing properties file {file_path}: {str(e)}")
    
    def _process_properties(self, content: str, filename: str) -> None:
        """
        Process properties file content.
        
        Args:
            content: Properties file content
            filename: Name of the properties file
        """
        secure_props = []
        
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Check if this might be a secure property
                is_secure = (
                    'password' in key.lower() or
                    'secret' in key.lower() or
                    'key' in key.lower() or
                    'token' in key.lower() or
                    'secure' in filename.lower()
                )
                
                if is_secure:
                    secure_props.append({
                        'key': key,
                        'masked_value': '*****',
                        'file': filename
                    })
        
        self.metadata['secure_properties'].extend(secure_props)
    
    def _extract_api_specs(self, api_dir: str) -> None:
        """
        Extract API specifications from a directory.
        
        Args:
            api_dir: Directory containing API specifications
        """
        api_specs = []
        
        try:
            for file in os.listdir(api_dir):
                if file.endswith('.raml') or file.endswith('.yaml') or file.endswith('.json'):
                    file_path = os.path.join(api_dir, file)
                    
                    api_spec = {
                        'file': file,
                        'type': file.split('.')[-1].upper(),
                        'size': os.path.getsize(file_path)
                    }
                    
                    # For RAML files, try to extract the title and version
                    if file.endswith('.raml'):
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            title_match = re.search(r'title:\s*(.*)', content)
                            version_match = re.search(r'version:\s*(.*)', content)
                            
                            if title_match:
                                api_spec['title'] = title_match.group(1).strip()
                            if version_match:
                                api_spec['version'] = version_match.group(1).strip()
                    
                    api_specs.append(api_spec)
            
            if api_specs:
                self.metadata['api_specs'] = api_specs
        except Exception as e:
            print(f"Error extracting API specs: {str(e)}")


def extract_metadata(path: str) -> Dict[str, Any]:
    """
    Extract metadata from a MuleSoft application JAR or directory.
    
    Args:
        path: Path to JAR file or project directory
        
    Returns:
        Dictionary containing extracted metadata
    """
    extractor = MetadataExtractor()
    
    if os.path.isfile(path) and path.endswith('.jar'):
        return extractor.extract_from_jar(path)
    elif os.path.isdir(path):
        return extractor.extract_from_directory(path)
    else:
        raise ValueError("Path must be a JAR file or a directory")


if __name__ == '__main__':
    # Example usage
    import sys
    import json
    
    if len(sys.argv) > 1:
        path = sys.argv[1]
        try:
            metadata = extract_metadata(path)
            print(json.dumps(metadata, indent=2))
        except Exception as e:
            print(f"Error: {str(e)}")
    else:
        print("Please provide a path to a MuleSoft JAR file or project directory.") 