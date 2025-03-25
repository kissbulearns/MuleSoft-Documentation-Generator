"""
Parser for extracting error handling information from MuleSoft XML files.

This module analyzes error-handling configurations in MuleSoft applications,
including global error handlers and flow-specific error handlers.
"""

import os
import re
from typing import Dict, List, Any, Optional, Set, Tuple
from lxml import etree
from pathlib import Path


class ErrorHandlerParser:
    """Parser for MuleSoft error handling components."""
    
    # XML namespaces for MuleSoft configuration
    NAMESPACES = {
        'mule': 'http://www.mulesoft.org/schema/mule/core',
        'doc': 'http://www.mulesoft.org/schema/mule/documentation',
        'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
    }
    
    def __init__(self):
        """Initialize the error handler parser."""
        self.global_error_handlers = []
        self.error_handlers = {}  # Flow name -> error handler details
        self.flows_without_handlers = []
        self.error_types = set()
        
    def parse_file(self, file_path: str) -> None:
        """
        Parse a MuleSoft XML file for error handling configuration.
        
        Args:
            file_path: Path to the XML file to parse
        """
        try:
            tree = etree.parse(file_path)
            root = tree.getroot()
            
            # Parse global error handlers
            self._parse_global_error_handlers(root)
            
            # Parse flow error handlers
            self._parse_flow_error_handlers(root)
            
        except Exception as e:
            print(f"Error parsing file {file_path}: {str(e)}")
    
    def parse_directory(self, directory_path: str) -> None:
        """
        Parse all XML files in a directory for error handling configuration.
        
        Args:
            directory_path: Path to the directory containing XML files
        """
        for root, _, files in os.walk(directory_path):
            for file in files:
                if file.endswith('.xml'):
                    file_path = os.path.join(root, file)
                    self.parse_file(file_path)
    
    def _parse_global_error_handlers(self, root: etree.Element) -> None:
        """
        Parse global error handlers from the XML root.
        
        Args:
            root: XML root element
        """
        error_handlers = root.findall('.//mule:error-handler', self.NAMESPACES)
        
        for handler in error_handlers:
            # Skip if this is inside a flow (not global)
            if handler.getparent().tag.endswith('}flow') or handler.getparent().tag.endswith('}sub-flow'):
                continue
                
            name = handler.get('name', 'Unnamed Global Error Handler')
            description = self._get_documentation(handler)
            
            error_types = []
            processors = []
            
            # Parse error handlers (on-error-*)
            for error_element in handler.findall('./mule:*', self.NAMESPACES):
                if not error_element.tag.startswith('{http://www.mulesoft.org/schema/mule/core}on-error'):
                    continue
                
                error_type = error_element.get('type')
                when = error_element.get('when')
                
                if error_type:
                    error_types.append(error_type)
                    self.error_types.add(error_type)
                
                # Parse processors inside the error handler
                for processor in error_element.findall('./mule:*', self.NAMESPACES):
                    processor_type = self._get_element_name(processor.tag)
                    processor_details = self._extract_processor_details(processor)
                    
                    processors.append({
                        'type': processor_type,
                        'when': when,
                        'details': processor_details
                    })
            
            self.global_error_handlers.append({
                'name': name,
                'description': description,
                'error_types': error_types,
                'processors': processors
            })
    
    def _parse_flow_error_handlers(self, root: etree.Element) -> None:
        """
        Parse flow-specific error handlers from the XML root.
        
        Args:
            root: XML root element
        """
        flows = root.findall('.//mule:flow', self.NAMESPACES)
        flows.extend(root.findall('.//mule:sub-flow', self.NAMESPACES))
        
        for flow in flows:
            flow_name = flow.get('name')
            error_handler = flow.find('./mule:error-handler', self.NAMESPACES)
            
            if error_handler is not None:
                description = self._get_documentation(error_handler)
                error_types = []
                processors = []
                
                # Parse error handlers (on-error-*)
                for error_element in error_handler.findall('./mule:*', self.NAMESPACES):
                    if not error_element.tag.startswith('{http://www.mulesoft.org/schema/mule/core}on-error'):
                        continue
                    
                    error_type = error_element.get('type')
                    when = error_element.get('when')
                    
                    if error_type:
                        error_types.append(error_type)
                        self.error_types.add(error_type)
                    
                    # Parse processors inside the error handler
                    for processor in error_element.findall('./mule:*', self.NAMESPACES):
                        processor_type = self._get_element_name(processor.tag)
                        processor_details = self._extract_processor_details(processor)
                        
                        processors.append({
                            'type': processor_type,
                            'when': when,
                            'details': processor_details
                        })
                
                self.error_handlers[flow_name] = {
                    'description': description,
                    'error_types': error_types,
                    'processors': processors
                }
            else:
                # Flow has no error handler
                self.flows_without_handlers.append(flow_name)
    
    def _get_element_name(self, tag: str) -> str:
        """
        Extract element name from the namespaced tag.
        
        Args:
            tag: Namespaced tag
            
        Returns:
            Element name without namespace
        """
        return tag.split('}')[-1] if '}' in tag else tag
    
    def _get_documentation(self, element: etree.Element) -> Optional[str]:
        """
        Extract documentation from a MuleSoft element.
        
        Args:
            element: XML element
            
        Returns:
            Documentation string or None
        """
        doc_elem = element.find('./doc:description', self.NAMESPACES)
        if doc_elem is not None and doc_elem.text:
            return doc_elem.text.strip()
        return None
    
    def _extract_processor_details(self, processor: etree.Element) -> Dict[str, str]:
        """
        Extract details from a processor element.
        
        Args:
            processor: Processor XML element
            
        Returns:
            Dictionary of processor details
        """
        details = {}
        
        # Extract attributes
        for key, value in processor.attrib.items():
            if key not in ('name', 'doc:name'):
                details[key] = value
                
        # Extract special elements for specific processor types
        processor_type = self._get_element_name(processor.tag)
        
        if processor_type == 'set-payload':
            value_elem = processor.find('./mule:value', self.NAMESPACES)
            if value_elem is not None and value_elem.text:
                details['value'] = value_elem.text.strip()
                
        elif processor_type == 'raise-error':
            details['type'] = processor.get('type', '')
            details['description'] = processor.get('description', '')
            
        elif processor_type == 'logger':
            details['message'] = processor.get('message', '')
            details['level'] = processor.get('level', 'INFO')
            
        elif processor_type == 'flow-ref':
            details['name'] = processor.get('name', '')
            
        return details
    
    def get_results(self) -> Dict[str, Any]:
        """
        Get the parsed error handling results.
        
        Returns:
            Dictionary containing error handling information
        """
        return {
            'global_error_handlers': self.global_error_handlers,
            'error_handlers': self.error_handlers,
            'flows_without_handlers': self.flows_without_handlers,
            'error_types': sorted(list(self.error_types))
        }
    
    def analyze_try_scopes(self, root: etree.Element) -> Dict[str, Any]:
        """
        Analyze try scopes in the MuleSoft configuration.
        
        Args:
            root: XML root element
            
        Returns:
            Dictionary with try scope analysis
        """
        try_scopes = root.findall('.//mule:try', self.NAMESPACES)
        
        try_with_handlers = 0
        try_without_handlers = 0
        
        for try_scope in try_scopes:
            if try_scope.find('./mule:error-handler', self.NAMESPACES) is not None:
                try_with_handlers += 1
            else:
                try_without_handlers += 1
        
        return {
            'total': len(try_scopes),
            'with_handlers': try_with_handlers,
            'without_handlers': try_without_handlers
        }


def parse_error_handling(xml_dir: str) -> Dict[str, Any]:
    """
    Parse error handling configuration from a directory of MuleSoft XML files.
    
    Args:
        xml_dir: Directory containing MuleSoft XML files
        
    Returns:
        Dictionary with error handling information
    """
    parser = ErrorHandlerParser()
    parser.parse_directory(xml_dir)
    return parser.get_results()


def analyze_error_handling(xml_files: List[str]) -> Dict[str, Any]:
    """
    Analyze error handling configuration from a list of MuleSoft XML files.
    
    This is an alias for parse_error_handling to maintain compatibility with existing code.
    Instead of a directory, it accepts a list of file paths.
    
    Args:
        xml_files: List of paths to MuleSoft XML files
        
    Returns:
        Dictionary with error handling information
    """
    parser = ErrorHandlerParser()
    for file_path in xml_files:
        parser.parse_file(file_path)
    return parser.get_results()


if __name__ == '__main__':
    # Example usage
    import sys
    
    if len(sys.argv) > 1:
        xml_directory = sys.argv[1]
        results = parse_error_handling(xml_directory)
        
        print(f"Global Error Handlers: {len(results['global_error_handlers'])}")
        print(f"Flow Error Handlers: {len(results['error_handlers'])}")
        print(f"Flows Without Handlers: {len(results['flows_without_handlers'])}")
        print(f"Error Types: {len(results['error_types'])}")
    else:
        print("Please provide a directory path to MuleSoft XML files.") 