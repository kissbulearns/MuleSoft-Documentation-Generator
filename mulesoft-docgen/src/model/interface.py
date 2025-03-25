"""
Data models for MuleSoft interfaces.
These classes represent the different components of a MuleSoft interface.
"""

from typing import Dict, List, Optional, Any

class Connector:
    """Represents a connector in a MuleSoft flow (file, SFTP, HTTP, etc.)."""
    
    def __init__(self, connector_type: str, attributes: Dict[str, str]):
        """
        Initialize a connector with its type and attributes.
        
        Args:
            connector_type: Type of connector (file, sftp, http, etc.)
            attributes: Connector attributes from XML
        """
        self.type = connector_type
        self.attributes = attributes
    
    @property
    def name(self) -> str:
        """Get the connector name."""
        return self.attributes.get('name', 'Unknown Connector')
    
    @property
    def description(self) -> str:
        """Get a human-readable description of the connector."""
        if self.type == 'file-listener':
            return f"File listener for directory '{self.attributes.get('directory', 'Unknown')}'"
        elif self.type == 'sftp-listener':
            return f"SFTP listener for directory '{self.attributes.get('directory', 'Unknown')}'"
        elif self.type == 'file-write':
            return f"Write to file '{self.attributes.get('path', 'Unknown')}'"
        elif self.type == 'sftp-write':
            return f"Write to SFTP '{self.attributes.get('path', 'Unknown')}'"
        elif self.type == 'http-listener':
            return f"HTTP listener on path '{self.attributes.get('path', 'Unknown')}'"
        else:
            return f"{self.type} connector"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Connector':
        """
        Create a Connector from a dictionary.
        
        Args:
            data: Dictionary with connector information
            
        Returns:
            Connector instance
        """
        return cls(data.get('type', 'unknown'), data.get('attributes', {}))


class Flow:
    """Represents a MuleSoft flow or sub-flow."""
    
    def __init__(self, 
                 flow_id: str, 
                 description: str, 
                 flow_type: str = 'flow', 
                 source: Optional[Dict[str, Any]] = None,
                 processors: Optional[List[Dict[str, Any]]] = None,
                 file_name: str = 'Unknown'):
        """
        Initialize a Flow object.
        
        Args:
            flow_id: Flow identifier
            description: Flow description
            flow_type: Type of flow ('flow' or 'sub-flow')
            source: Source information (trigger)
            processors: List of processors in the flow
            file_name: Name of the file containing this flow
        """
        self.id = flow_id
        self.description = description
        self.type = flow_type
        self.source = source
        self.processors = processors or []
        self.file_name = file_name
        self.transformations = []  # List to store DataWeave transformations
    
    @property
    def is_subflow(self) -> bool:
        """Check if this is a sub-flow."""
        return self.type == 'sub-flow'
    
    @property
    def source_type(self) -> Optional[str]:
        """Get the source type of this flow."""
        if not self.source:
            return None
        return self.source.get('type')
    
    @property
    def has_file_operations(self) -> bool:
        """Check if this flow has file operations."""
        for processor in self.processors:
            if processor.get('type') in ['file:write', 'sftp:write']:
                return True
        return False
    
    @property
    def input_format(self) -> str:
        """Determine the input format of this flow."""
        # Look for transformations to infer the input format
        for processor in self.processors:
            if processor.get('type') == 'transform' and 'transformation' in processor:
                # Basic inference from transformation code
                code = processor['transformation'].get('code', '')
                if isinstance(code, str) and code.startswith('%dw 2.0'):
                    if 'application/json' in code:
                        return 'JSON'
                    elif 'application/xml' in code:
                        return 'XML'
                    elif 'application/csv' in code:
                        return 'CSV'
        
        # If no transformation, try to infer from source
        if self.source:
            if self.source.get('type') in ['file-listener', 'sftp-listener']:
                pattern = self.source.get('pattern', '')
                if isinstance(pattern, str):
                    if pattern.endswith('.json'):
                        return 'JSON'
                    elif pattern.endswith('.xml'):
                        return 'XML'
                    elif pattern.endswith('.csv'):
                        return 'CSV'
                    elif pattern.endswith('.txt'):
                        return 'Text'
        
        return 'Unknown'
    
    @property
    def output_format(self) -> str:
        """Determine the output format of this flow."""
        # Check file operations first
        for processor in self.processors:
            if processor.get('type') in ['file:write', 'sftp:write']:
                path = processor.get('file_operation', {}).get('path', '')
                if isinstance(path, str):
                    if path.endswith('.json'):
                        return 'JSON'
                    elif path.endswith('.xml'):
                        return 'XML'
                    elif path.endswith('.csv'):
                        return 'CSV'
                    elif path.endswith('.txt'):
                        return 'Text'
        
        # Look at the last transformation
        for processor in reversed(self.processors):
            if processor.get('type') == 'transform' and 'transformation' in processor:
                code = processor['transformation'].get('code', '')
                if isinstance(code, str) and code.startswith('%dw 2.0'):
                    if 'application/json' in code:
                        return 'JSON'
                    elif 'application/xml' in code:
                        return 'XML'
                    elif 'application/csv' in code:
                        return 'CSV'
        
        return 'Unknown'
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Flow':
        """
        Create a Flow from a dictionary.
        
        Args:
            data: Dictionary with flow information
            
        Returns:
            Flow instance
        """
        return cls(
            flow_id=data.get('id', 'Unknown'),
            description=data.get('description', ''),
            flow_type=data.get('type', 'flow'),
            source=data.get('source'),
            processors=data.get('processors', []),
            file_name=data.get('file', 'Unknown')
        )


class Interface:
    """Represents a complete MuleSoft interface (collection of flows)."""
    
    def __init__(self, name: str, description: str = '', flows: List[Flow] = None, configs: Dict[str, Any] = None, xml_files: List[str] = None):
        """
        Initialize an Interface object.
        
        Args:
            name: Interface name
            description: Interface description
            flows: List of flows in the interface
            configs: Dictionary of configurations
            xml_files: List of XML file paths
        """
        self.name = name
        self.description = description
        self.flows = flows or []
        self.global_configs = configs or {}
        self.xml_files = xml_files or []
    
    def add_flow(self, flow: Flow) -> None:
        """
        Add a flow to this interface.
        
        Args:
            flow: Flow to add
        """
        self.flows.append(flow)
    
    def add_global_config(self, name: str, config: Dict[str, Any]) -> None:
        """
        Add a global configuration to this interface.
        
        Args:
            name: Configuration name
            config: Configuration details
        """
        self.global_configs[name] = config
    
    @property
    def source_flows(self) -> List[Flow]:
        """Get flows that have sources (entry points)."""
        result = []
        for flow in self.flows:
            # Handle both dictionary and object representations of flows
            if isinstance(flow, dict):
                is_subflow = flow.get('type') == 'sub-flow'
                source = flow.get('source')
            else:
                is_subflow = getattr(flow, 'is_subflow', False) 
                source = getattr(flow, 'source', None)
                
            if not is_subflow and source:
                result.append(flow)
        return result
    
    @property
    def subflows(self) -> List[Flow]:
        """Get all sub-flows."""
        result = []
        for flow in self.flows:
            # Handle both dictionary and object representations of flows
            if isinstance(flow, dict):
                is_subflow = flow.get('type') == 'sub-flow'
            else:
                is_subflow = getattr(flow, 'is_subflow', False)
                
            if is_subflow:
                result.append(flow)
        return result
    
    def get_subflows(self) -> List[Flow]:
        """
        Get all sub-flows.
        
        This is an alias for the subflows property for template compatibility.
        
        Returns:
            List of sub-flows
        """
        return self.subflows
    
    @classmethod
    def from_parser_result(cls, name: str, parser_result: Dict[str, Any], description: str = '') -> 'Interface':
        """
        Create an Interface from parser results.
        
        Args:
            name: Interface name
            parser_result: Result from the XML parser
            description: Interface description
            
        Returns:
            Interface instance
        """
        interface = cls(name, description)
        
        # Add flows
        for flow_data in parser_result.get('flows', []):
            flow = Flow.from_dict(flow_data)
            interface.add_flow(flow)
        
        # Add global configurations
        for config_name, config_data in parser_result.get('global_configs', {}).items():
            interface.add_global_config(config_name, config_data)
        
        return interface
    
    def infer_purpose(self) -> str:
        """
        Infer the purpose of this interface based on its flows.
        
        Returns:
            A string describing the likely purpose
        """
        # Count types of operations
        has_file_input = False
        has_file_output = False
        has_sftp_input = False
        has_sftp_output = False
        has_http_endpoints = False
        
        for flow in self.flows:
            # Handle both dictionary and object representation
            if isinstance(flow, dict):
                source = flow.get('source')
                processors = flow.get('processors', [])
            else:
                source = getattr(flow, 'source', None)
                processors = getattr(flow, 'processors', [])
                
            if source:
                source_type = source.get('type', '')
                if source_type == 'file-listener':
                    has_file_input = True
                elif source_type == 'sftp-listener':
                    has_sftp_input = True
                elif source_type == 'http-listener':
                    has_http_endpoints = True
            
            # Check for file outputs
            for processor in processors:
                if processor.get('type') == 'file:write':
                    has_file_output = True
                elif processor.get('type') == 'sftp:write':
                    has_sftp_output = True
        
        # Determine purpose based on patterns
        if (has_file_input or has_sftp_input) and (has_file_output or has_sftp_output):
            return "File Transfer/Transformation"
        elif has_http_endpoints:
            return "API Service"
        elif has_file_input or has_sftp_input:
            return "File Import"
        elif has_file_output or has_sftp_output:
            return "File Export"
        else:
            return "Unknown Purpose" 