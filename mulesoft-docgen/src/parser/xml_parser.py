"""
XML parser for MuleSoft configuration files.
This module extracts information about flows, connectors, and transformations from Mule XML files.
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from lxml import etree
import traceback

from ..model.interface import Interface, Flow
from .dataweave_parser import DataWeaveParser

# MuleSoft XML namespaces
NAMESPACES = {
    'mule': 'http://www.mulesoft.org/schema/mule/core',
    'doc': 'http://www.mulesoft.org/schema/mule/documentation',
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
    'file': 'http://www.mulesoft.org/schema/mule/file',
    'sftp': 'http://www.mulesoft.org/schema/mule/sftp',
    'dw': 'http://www.mulesoft.org/schema/mule/ee/dw',
    'db': 'http://www.mulesoft.org/schema/mule/db',
    'ee': 'http://www.mulesoft.org/schema/mule/ee/core',
    'http': 'http://www.mulesoft.org/schema/mule/http',
    'batch': 'http://www.mulesoft.org/schema/mule/batch'
}

class XmlParser:
    """Parser for MuleSoft XML configuration files."""
    
    def __init__(self):
        """Initialize the XML parser."""
        self.flows = []
        
    def parse_file(self, xml_file_path: str):
        """
        Parse a MuleSoft XML file.
        
        Args:
            xml_file_path: Path to the MuleSoft XML file
        """
        try:
            # Create a parser instance for this specific file
            parser = self._create_file_parser(xml_file_path)
            
            # Extract flows and add them to our collection
            flows = parser.get_flows()
            self.flows.extend(flows)
        except Exception as e:
            print(f"Error parsing XML file {xml_file_path}: {e}")
            raise
    
    def _create_file_parser(self, xml_file_path: str):
        """
        Create a parser for a specific file.
        
        Args:
            xml_file_path: Path to the MuleSoft XML file
            
        Returns:
            An instance of MuleFileXmlParser
        """
        return MuleFileXmlParser(xml_file_path)
    
    def get_flows(self) -> List[Dict[str, Any]]:
        """
        Get all parsed flows.
        
        Returns:
            List of dictionaries with flow information
        """
        return self.flows

class MuleFileXmlParser:
    """Parser for a single MuleSoft XML configuration file."""
    
    def __init__(self, xml_file_path: str):
        """
        Initialize the parser with a MuleSoft XML file path.
        
        Args:
            xml_file_path: Path to the MuleSoft XML file
        """
        self.xml_file_path = xml_file_path
        self.tree = None
        self.root = None
        self.parse()
    
    def parse(self) -> None:
        """Parse the XML file and set up the tree and root elements."""
        try:
            self.tree = etree.parse(self.xml_file_path)
            self.root = self.tree.getroot()
        except Exception as e:
            print(f"Error parsing XML file {self.xml_file_path}: {e}")
            raise
    
    def get_flows(self) -> List[Dict[str, Any]]:
        """
        Extract all flows from the XML file.
        
        Returns:
            List of dictionaries with flow information
        """
        flows = []
        
        # Find all flow elements
        flow_elements = self.root.xpath('//mule:flow', namespaces=NAMESPACES)
        
        for flow in flow_elements:
            flow_id = flow.get('name', 'Unknown')
            
            # Get flow documentation if available
            doc = flow.xpath('./doc:description', namespaces=NAMESPACES)
            description = doc[0].text if doc and doc[0].text else f"Flow: {flow_id}"
            
            # Extract source information (triggers/listeners)
            source = self._extract_source(flow)
            
            # Extract processors (components in the flow)
            processors = self._extract_processors(flow)
            
            flows.append({
                'id': flow_id,
                'description': description,
                'source': source,
                'processors': processors,
                'type': 'flow'
            })
        
        # Also get sub-flows
        subflow_elements = self.root.xpath('//mule:sub-flow', namespaces=NAMESPACES)
        for subflow in subflow_elements:
            subflow_id = subflow.get('name', 'Unknown')
            
            # Get subflow documentation if available
            doc = subflow.xpath('./doc:description', namespaces=NAMESPACES)
            description = doc[0].text if doc and doc[0].text else f"Sub-flow: {subflow_id}"
            
            # Extract processors
            processors = self._extract_processors(subflow)
            
            flows.append({
                'id': subflow_id,
                'description': description,
                'source': None,  # Sub-flows don't have sources
                'processors': processors,
                'type': 'sub-flow'
            })
        
        return flows
    
    def _extract_source(self, flow_element) -> Optional[Dict[str, Any]]:
        """
        Extract the source (trigger) of a flow.
        
        Args:
            flow_element: The flow XML element
            
        Returns:
            Dictionary with source information or None if no source found
        """
        # Common triggers/sources in MuleSoft
        source_elements = []
        
        # File connectors
        source_elements.extend(flow_element.xpath('./file:listener', namespaces=NAMESPACES))
        source_elements.extend(flow_element.xpath('./sftp:listener', namespaces=NAMESPACES))
        
        # HTTP listeners
        source_elements.extend(flow_element.xpath('./http:listener', namespaces=NAMESPACES))
        
        # Schedulers
        source_elements.extend(flow_element.xpath('./mule:scheduler', namespaces=NAMESPACES))
        
        if not source_elements:
            return None
        
        # Take the first source element (usually there's only one)
        source = source_elements[0]
        
        # Safe way to extract tag name and namespace
        if hasattr(source, 'tag'):
            if isinstance(source.tag, str) and '}' in source.tag:
                # Extract namespace and local name from tag string
                ns, tag = source.tag.rsplit('}', 1)
                ns = ns.strip('{')
            else:
                # Fallback for non-string or non-namespace tags
                tag = 'unknown'
                ns = ''
        else:
            # Fallback for elements without tag attribute
            tag = 'unknown'
            ns = ''
        
        if tag == 'listener':
            # File or SFTP listener
            if 'file' in ns:
                return {
                    'type': 'file-listener',
                    'directory': source.get('directory', 'Not specified'),
                    'pattern': source.get('matcher', 'Not specified')
                }
            elif 'sftp' in ns:
                return {
                    'type': 'sftp-listener',
                    'directory': source.get('directory', 'Not specified'),
                    'pattern': source.get('matcher', 'Not specified')
                }
            elif 'http' in ns:
                return {
                    'type': 'http-listener',
                    'path': source.get('path', 'Not specified'),
                    'method': source.get('method', 'All methods')
                }
        elif tag == 'scheduler':
            return {
                'type': 'scheduler',
                'frequency': source.get('frequency', 'Not specified')
            }
        
        # Generic source information
        return {
            'type': tag,
            'attributes': {key: source.get(key) for key in source.keys()}
        }
    
    def _extract_processors(self, flow_element) -> List[Dict[str, Any]]:
        """
        Extract all processors (components) from a flow.
        
        Args:
            flow_element: The flow or sub-flow XML element
            
        Returns:
            List of dictionaries with processor information
        """
        processors = []
        
        # Skip the first child if it's a source in a flow (not in sub-flows)
        children = list(flow_element)
        start_idx = 1 if (flow_element.tag.endswith('flow') and len(children) > 0 and 
                          not (children[0].tag.endswith('description'))) else 0
        
        # Skip documentation elements
        if start_idx < len(children) and children[start_idx].tag.endswith('description'):
            start_idx += 1
        
        for child in children[start_idx:]:
            # Safe way to extract tag name
            if hasattr(child, 'tag'):
                if isinstance(child.tag, str) and '}' in child.tag:
                    # Extract namespace and local name from tag string
                    _, tag = child.tag.rsplit('}', 1)
                else:
                    # Fallback for non-string or non-namespace tags
                    tag = 'unknown'
            else:
                # Fallback for elements without tag attribute
                tag = 'unknown'
            
            # Basic processor info
            processor = {
                'type': tag,
                'attributes': {key: child.get(key) for key in child.keys()}
            }
            
            # Special handling for certain processor types
            if tag == 'transform':
                # Handle DataWeave transformations
                dw_elements = child.xpath('.//dw:set-payload', namespaces=NAMESPACES)
                if dw_elements:
                    code = dw_elements[0].get('resource') or dw_elements[0].text or 'No transformation code found'
                    processor['transformation'] = {
                        'type': 'dw-set-payload',
                        'code': code
                    }
            elif tag in ['file:write', 'sftp:write']:
                # Handle file write operations
                processor['file_operation'] = {
                    'path': child.get('path', 'Not specified'),
                    'mode': child.get('mode', 'Overwrite')
                }
            elif tag == 'choice':
                # Handle choice routers
                when_elements = child.xpath('./mule:when', namespaces=NAMESPACES)
                processor['routes'] = []
                
                for when in when_elements:
                    expression = when.get('expression', 'No condition')
                    # Extract the processors inside this when route
                    route_processors = self._extract_processors(when)
                    processor['routes'].append({
                        'condition': expression,
                        'processors': route_processors
                    })
                
                # Handle the default route (otherwise)
                otherwise = child.xpath('./mule:otherwise', namespaces=NAMESPACES)
                if otherwise:
                    route_processors = self._extract_processors(otherwise[0])
                    processor['routes'].append({
                        'condition': 'otherwise',
                        'processors': route_processors
                    })
            
            processors.append(processor)
        
        return processors
    
    def get_global_configs(self) -> Dict[str, Any]:
        """
        Extract global configurations from the XML file.
        
        Returns:
            Dictionary with global configuration information
        """
        configs = {}
        
        # Extract file configurations
        file_configs = self.root.xpath('//file:config', namespaces=NAMESPACES)
        if file_configs:
            configs['file'] = []
            for config in file_configs:
                configs['file'].append({
                    'name': config.get('name', 'Unknown'),
                    'working-directory': config.get('workingDirectory', 'Not specified')
                })
        
        # Extract SFTP configurations
        sftp_configs = self.root.xpath('//sftp:config', namespaces=NAMESPACES)
        if sftp_configs:
            configs['sftp'] = []
            for config in sftp_configs:
                connection = config.find('.//sftp:connection', namespaces=NAMESPACES)
                conn_details = {}
                if connection is not None:
                    conn_details = {
                        'host': connection.get('host', 'Not specified'),
                        'port': connection.get('port', '22'),
                        'username': connection.get('username', 'Not specified')
                    }
                
                configs['sftp'].append({
                    'name': config.get('name', 'Unknown'),
                    'connection': conn_details
                })
        
        # Extract HTTP configurations
        http_configs = self.root.xpath('//http:listener-config', namespaces=NAMESPACES)
        if http_configs:
            configs['http'] = []
            for config in http_configs:
                connection = config.find('.//http:listener-connection', namespaces=NAMESPACES)
                conn_details = {}
                if connection is not None:
                    conn_details = {
                        'host': connection.get('host', 'Not specified'),
                        'port': connection.get('port', '8081')
                    }
                
                configs['http'].append({
                    'name': config.get('name', 'Unknown'),
                    'base-path': config.get('basePath', '/'),
                    'connection': conn_details
                })
        
        return configs

def parse_directory(directory_path: str) -> Dict[str, Any]:
    """
    Parse all XML files in a directory.
    
    Args:
        directory_path: Path to the directory containing XML files
        
    Returns:
        Dictionary with parsed information
    """
    parser = XmlParser()
    
    for file_path in Path(directory_path).glob('**/*.xml'):
        parser.parse_file(str(file_path))
    
    return {
        'flows': parser.get_flows()
    }

def parse_xml_files(xml_files: List[str], interface_name: str = "MuleSoft Interface") -> Interface:
    """
    Parse XML files and create an Interface object.
    
    Args:
        xml_files: List of XML file paths
        interface_name: Name of the interface
        
    Returns:
        Interface object
    """
    interface = Interface(interface_name)
    dataweave_parser = DataWeaveParser()
    
    for xml_file in xml_files:
        try:
            tree = etree.parse(xml_file)
            root = tree.getroot()
            
            # Define namespaces
            namespaces = {
                'mule': 'http://www.mulesoft.org/schema/mule/core',
                'dw': 'http://www.mulesoft.org/schema/mule/ee/dw',
                'ee': 'http://www.mulesoft.org/schema/mule/ee/core',
            }
            
            # Find flows
            flow_elements = root.xpath('//mule:flow', namespaces=namespaces)
            for flow_elem in flow_elements:
                flow_id = flow_elem.get('name', 'Unnamed Flow')
                
                # Get flow documentation if available
                doc = flow_elem.xpath('./doc:description', namespaces=NAMESPACES)
                description = doc[0].text if doc and doc[0].text else f"Flow: {flow_id}"
                
                # Extract source information (triggers/listeners)
                source = self._extract_source(flow_elem)
                
                # Extract processors (components in the flow)
                processors = self._extract_processors(flow_elem)
                
                flow = Flow(
                    flow_id=flow_id,
                    description=description,
                    flow_type='flow',
                    source=source,
                    processors=processors,
                    file_name=os.path.basename(xml_file)
                )
                
                # Find DataWeave transformations in the flow
                dw_elements = []
                
                # Look for ee:transform elements
                dw_elements.extend(flow_elem.xpath('.//ee:transform', namespaces=namespaces))
                
                # Look for dw:transform elements (older style)
                dw_elements.extend(flow_elem.xpath('.//dw:transform', namespaces=namespaces))
                
                # Look for ee:set-payload with DataWeave code
                dw_elements.extend(flow_elem.xpath('.//ee:set-payload', namespaces=namespaces))
                
                for dw_elem in dw_elements:
                    dw_code = None
                    
                    # Try to find the DataWeave code
                    if dw_elem.tag.endswith('transform'):
                        # Look for dw:set-payload inside transform
                        set_payload = dw_elem.xpath('.//dw:set-payload', namespaces=namespaces)
                        if set_payload and set_payload[0].text:
                            dw_code = set_payload[0].text
                        
                        # Look for ee:set-payload inside transform
                        set_payload = dw_elem.xpath('.//ee:set-payload', namespaces=namespaces)
                        if set_payload and set_payload[0].text:
                            dw_code = set_payload[0].text
                            
                    elif dw_elem.tag.endswith('set-payload') and dw_elem.text and '%dw' in dw_elem.text:
                        dw_code = dw_elem.text
                    
                    if dw_code:
                        # Extract info from the DataWeave code
                        dw_data = dataweave_parser.extract_info(dw_code)
                        dw_data['file_path'] = xml_file
                        flow.transformations.append(dw_data)
                
                interface.add_flow(flow)
            
            # Find configurations
            config_elements = root.xpath('//mule:configuration', namespaces=namespaces)
            for config_elem in config_elements:
                config_name = config_elem.get('name', 'default')
                if config_name not in interface.configs:
                    interface.configs[config_name] = {'properties': {}}
                
                # Extract properties
                property_elements = config_elem.xpath('.//mule:property', namespaces=namespaces)
                for prop_elem in property_elements:
                    prop_name = prop_elem.get('name')
                    prop_value = prop_elem.get('value')
                    if prop_name and prop_value:
                        interface.configs[config_name]['properties'][prop_name] = prop_value
            
        except Exception as e:
            print(f"Error parsing XML file {xml_file}: {e}")
            traceback.print_exc()
    
    return interface 