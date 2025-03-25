"""
DataWeave transformation parser for MuleSoft.
This module extracts and analyzes DataWeave transformation code.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from lxml import etree

class DataWeaveParser:
    """Parser for DataWeave transformation files and code blocks."""
    
    def __init__(self, dw_content: str = None, dw_file_path: str = None):
        """
        Initialize with either DataWeave content or a file path.
        
        Args:
            dw_content: DataWeave code content as string
            dw_file_path: Path to DataWeave file
        """
        self.content = dw_content
        self.file_path = dw_file_path
        
        if self.file_path and not self.content:
            self._load_from_file()
    
    def _load_from_file(self) -> None:
        """Load DataWeave content from a file."""
        try:
            with open(self.file_path, 'r') as file:
                self.content = file.read()
        except Exception as e:
            print(f"Error loading DataWeave file {self.file_path}: {e}")
            self.content = ""
    
    def get_dataweave_version(self) -> str:
        """
        Extract the DataWeave version.
        
        Returns:
            DataWeave version or 'Unknown'
        """
        if not self.content:
            return "Unknown"
        
        # Look for version declaration in header
        version_match = re.search(r'%dw\s+(\d+\.\d+)', self.content)
        if version_match:
            return version_match.group(1)
        
        return "Unknown"
    
    def get_output_mimetype(self) -> str:
        """
        Extract the output MIME type.
        
        Returns:
            Output MIME type or 'Unknown'
        """
        if not self.content:
            return "Unknown"
        
        # Look for output directive
        output_match = re.search(r'output\s+(application|text)/(\w+)', self.content)
        if output_match:
            return f"{output_match.group(1)}/{output_match.group(2)}"
        
        return "Unknown"
    
    def get_input_types(self) -> Dict[str, str]:
        """
        Extract the input types.
        
        Returns:
            Dictionary of input variable names and their types
        """
        if not self.content:
            return {}
        
        result = {}
        
        # Look for input type declarations (var : Type format)
        input_matches = re.finditer(r'var\s+(\w+)\s*:\s*(\w+)', self.content)
        for match in input_matches:
            var_name = match.group(1)
            var_type = match.group(2)
            result[var_name] = var_type
        
        return result
    
    def get_variables(self) -> List[str]:
        """
        Extract variable declarations.
        
        Returns:
            List of variable names
        """
        if not self.content:
            return []
        
        result = []
        
        # Look for variable declarations
        var_matches = re.finditer(r'var\s+(\w+)', self.content)
        for match in var_matches:
            result.append(match.group(1))
        
        return result
    
    def get_functions(self) -> List[Dict[str, Any]]:
        """
        Extract function declarations.
        
        Returns:
            List of function details
        """
        if not self.content:
            return []
        
        result = []
        
        # Look for function declarations
        func_matches = re.finditer(r'fun\s+(\w+)\s*\((.*?)\)', self.content)
        for match in func_matches:
            func_name = match.group(1)
            params_str = match.group(2).strip()
            
            params = []
            if params_str:
                param_parts = params_str.split(',')
                for part in param_parts:
                    part = part.strip()
                    if ':' in part:
                        param_name, param_type = part.split(':', 1)
                        params.append({
                            'name': param_name.strip(),
                            'type': param_type.strip()
                        })
                    else:
                        params.append({
                            'name': part,
                            'type': 'Any'
                        })
            
            result.append({
                'name': func_name,
                'parameters': params
            })
        
        return result
    
    def get_transformation_summary(self) -> Dict[str, Any]:
        """
        Generate a summary of the transformation.
        
        Returns:
            Dictionary with transformation details
        """
        if not self.content:
            return {'error': 'No content to analyze'}
        
        # Get basic info
        version = self.get_dataweave_version()
        output_type = self.get_output_mimetype()
        input_types = self.get_input_types()
        variables = self.get_variables()
        functions = self.get_functions()
        
        # Analyze mapping complexity
        complexity_score = self._analyze_complexity()
        
        # Extract sample mapping
        mapping_sample = self._extract_mapping_sample()
        
        # File path info
        file_name = os.path.basename(self.file_path) if self.file_path else "embedded"
        file_path = self.file_path if self.file_path else ""
        
        return {
            'dw_version': version,
            'output_mime_type': output_type,
            'input_types': input_types,
            'variables': variables,
            'functions': functions,
            'complexity': complexity_score,
            'mapping_sample': mapping_sample,
            'code_preview': self._get_code_preview(),
            'file_name': file_name,
            'file_path': file_path
        }
    
    def _analyze_complexity(self) -> int:
        """
        Analyze the complexity of the transformation.
        
        Returns:
            Complexity score as an integer (higher = more complex)
        """
        if not self.content:
            return 0
        
        # Count conditionals
        if_count = len(re.findall(r'\bif\b', self.content))
        
        # Count loops
        map_count = len(re.findall(r'\bmap\b', self.content))
        filter_count = len(re.findall(r'\bfilter\b', self.content))
        reduce_count = len(re.findall(r'\breduce\b', self.content))
        
        # Count function calls
        func_calls = len(re.findall(r'\b[a-zA-Z_]\w*\(', self.content))
        
        # Count operators
        operators = len(re.findall(r'[+\-*/&|^~<>]', self.content))
        
        # Get max nesting level
        nesting = self._get_max_nesting_level()
        
        # Calculate complexity score
        score = (if_count * 2) + \
                (map_count + filter_count + reduce_count) * 3 + \
                (func_calls) + \
                (operators // 5) + \
                (nesting * 2)
        
        return score
    
    def _get_max_nesting_level(self) -> int:
        """
        Calculate the maximum nesting level.
        
        Returns:
            Maximum nesting depth
        """
        if not self.content:
            return 0
        
        # Count indentation or bracket nesting
        lines = self.content.split('\n')
        max_indent = 0
        
        for line in lines:
            indent = len(line) - len(line.lstrip())
            max_indent = max(max_indent, indent)
        
        # Estimate nesting level based on indentation
        return max(1, max_indent // 2)
    
    def _extract_mapping_sample(self) -> str:
        """
        Extract a sample of the mapping.
        
        Returns:
            String representation of sample mappings
        """
        if not self.content:
            return ""
        
        result = []
        
        # Look for field mappings (target: source pattern)
        mapping_matches = re.finditer(r'(\w+):\s*(\S+)', self.content)
        count = 0
        
        for match in mapping_matches:
            if count >= 5:  # Limit to 5 samples
                break
            
            target = match.group(1)
            source = match.group(2)
            
            result.append(f"{target}: {source}")
            count += 1
        
        if not result:
            return ""
        
        return "{\n  " + ",\n  ".join(result) + "\n}"
    
    def _get_code_preview(self, max_lines: int = 10) -> str:
        """
        Get a preview of the code (first N lines).
        
        Args:
            max_lines: Maximum number of lines to include
            
        Returns:
            Code preview
        """
        if not self.content:
            return ""
        
        lines = self.content.split('\n')
        if len(lines) <= max_lines:
            return self.content
        
        return '\n'.join(lines[:max_lines]) + "\n..."

    def extract_from_xml_files(self, xml_files):
        """
        Extract DataWeave transformations from XML files.
        
        Args:
            xml_files: List of XML file paths
            
        Returns:
            List of DataWeave transformation data dictionaries
        """
        transformations = []
        
        for xml_file in xml_files:
            try:
                # Read the XML file
                with open(xml_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Look for DataWeave code blocks in the XML
                # Common pattern: <![CDATA[%dw 2.0 ... ]]>
                dw_blocks = re.findall(r'<!\[CDATA\[(.*?)%dw\s+[\d\.]+\s+(.*?)\]\]>', content, re.DOTALL)
                
                for prefix, code in dw_blocks:
                    full_code = "%dw " + code.strip()
                    
                    # Extract info from the code
                    dw_data = self.extract_info(full_code)
                    dw_data['file_path'] = xml_file
                    transformations.append(dw_data)
                
                # Also look for ee:transform elements with inline DataWeave
                transform_blocks = re.findall(r'<ee:set-payload.*?>(.*?)</ee:set-payload>', content, re.DOTALL)
                transform_blocks.extend(re.findall(r'<ee:set-variable.*?>(.*?)</ee:set-variable>', content, re.DOTALL))
                
                for block in transform_blocks:
                    if '%dw' in block:
                        # Extract just the DataWeave code
                        match = re.search(r'<!\[CDATA\[(.*?)\]\]>', block, re.DOTALL)
                        if match:
                            dw_code = match.group(1).strip()
                            dw_data = self.extract_info(dw_code)
                            dw_data['file_path'] = xml_file
                            transformations.append(dw_data)
            
            except Exception as e:
                print(f"Error processing XML file {xml_file}: {e}")
        
        return transformations

    def extract_info(self, code):
        """
        Extract information from DataWeave code.
        
        Args:
            code: DataWeave code as string
            
        Returns:
            Dictionary with extracted information
        """
        result = {
            'code': code,
            'complexity': 0,
            'version': '2.0',  # Default version
            'output_type': 'application/json',  # Default output type
            'variables': [],
            'functions': [],
            'input_types': {},
            'mapping_sample': ''
        }
        
        if not code or not isinstance(code, str):
            return result
            
        try:
            # Extract DataWeave version
            version_match = re.search(r'%dw\s+([\d\.]+)', code)
            if version_match:
                result['version'] = version_match.group(1)
            
            # Extract output type
            output_match = re.search(r'output\s+([\w\/\-\+\.]+)', code)
            if output_match:
                result['output_type'] = output_match.group(1)
            
            # Extract variables
            var_matches = re.findall(r'var\s+(\w+)\s*=', code)
            result['variables'] = var_matches
            
            # Extract functions
            fun_matches = re.findall(r'fun\s+(\w+)\s*\(', code)
            result['functions'] = fun_matches
            
            # Extract input types if they exist
            input_type_matches = re.findall(r'%input\s+([\w]+)\s+(\w+\/[\w\-\+]+)', code)
            for var_name, var_type in input_type_matches:
                result['input_types'][var_name] = var_type
            
            # Calculate complexity based on various factors
            # 1. Number of lines
            lines = code.count('\n') + 1
            # 2. Number of variables
            vars_count = len(result['variables'])
            # 3. Number of functions
            funcs_count = len(result['functions'])
            # 4. Control structures
            if_count = code.count('if')
            for_count = code.count('for')
            while_count = code.count('while')
            match_count = code.count('match')
            
            # Calculate complexity score
            complexity = lines / 10  # Base is lines/10
            complexity += vars_count * 0.2
            complexity += funcs_count * 0.5
            complexity += (if_count + for_count + while_count + match_count) * 0.3
            
            # Cap complexity and round to 1 decimal place
            result['complexity'] = round(min(complexity, 10.0), 1)
            
            # Extract a code sample (first 5 non-empty lines after header)
            code_lines = code.split('\n')
            mapping_lines = []
            in_mapping = False
            for line in code_lines:
                # Skip header and empty lines while looking for mapping
                if not in_mapping:
                    if '---' in line:
                        in_mapping = True
                    continue
                
                # Add non-empty mapping lines
                if line.strip():
                    mapping_lines.append(line)
                    if len(mapping_lines) >= 5:
                        break
            
            if mapping_lines:
                result['mapping_sample'] = '\n'.join(mapping_lines)
            
            # Create a preview of the code (first 100 chars)
            result['code_preview'] = code[:200] + '...' if len(code) > 200 else code
            
        except Exception as e:
            print(f"Error analyzing DataWeave code: {e}")
            
        return result

def parse_dataweave_directory(directory_path: str) -> Dict[str, Any]:
    """
    Parse all DataWeave files in a directory and its subdirectories.
    
    Args:
        directory_path: Path to the directory to parse
        
    Returns:
        Dictionary with information about all transformations found
    """
    transformations = []
    versions = set()
    output_types = set()
    total_complexity = 0
    
    # Find standard .dwl files
    dwl_files = list(Path(directory_path).glob('**/*.dwl'))
    print(f"Found {len(dwl_files)} .dwl files")
    
    # Find autogenerated .wev files
    wev_files = list(Path(directory_path).glob('**/*.wev'))
    print(f"Found {len(wev_files)} .wev files")
    
    # Find XML files that might contain embedded DataWeave
    xml_files = list(Path(directory_path).glob('**/*.xml'))
    print(f"Searching {len(xml_files)} XML files for embedded DataWeave")
    
    # Process .dwl files
    for file_path in dwl_files:
        try:
            parser = DataWeaveParser(dw_file_path=str(file_path))
            summary = parser.get_transformation_summary()
            
            # Skip if there was an error
            if 'error' in summary:
                continue
                
            transformations.append(summary)
            
            if summary.get('dw_version'):
                versions.add(summary['dw_version'])
            if summary.get('output_mime_type'):
                output_types.add(summary['output_mime_type'])
            
            complexity = summary.get('complexity', 0)
            if isinstance(complexity, (int, float)):
                total_complexity += complexity
        except Exception as e:
            print(f"Error parsing DWL file {file_path}: {e}")
    
    # Process .wev files
    for file_path in wev_files:
        try:
            parser = DataWeaveParser(dw_file_path=str(file_path))
            summary = parser.get_transformation_summary()
            
            # Skip if there was an error
            if 'error' in summary:
                continue
                
            transformations.append(summary)
            
            if summary.get('dw_version'):
                versions.add(summary['dw_version'])
            if summary.get('output_mime_type'):
                output_types.add(summary['output_mime_type'])
            
            complexity = summary.get('complexity', 0)
            if isinstance(complexity, (int, float)):
                total_complexity += complexity
        except Exception as e:
            print(f"Error parsing WEV file {file_path}: {e}")
    
    # Process XML files for embedded DataWeave
    namespaces = {
        'mule': 'http://www.mulesoft.org/schema/mule/core',
        'dw': 'http://www.mulesoft.org/schema/mule/ee/dw',
        'ee': 'http://www.mulesoft.org/schema/mule/ee/core',
    }
    
    dw_count = 0
    for file_path in xml_files:
        try:
            tree = etree.parse(str(file_path))
            root = tree.getroot()
            
            # Find DataWeave transformations in the XML
            dw_elements = []
            
            # Look for ee:transform elements
            dw_elements.extend(root.xpath('//ee:transform', namespaces=namespaces))
            
            # Look for dw:transform elements (older style)
            dw_elements.extend(root.xpath('//dw:transform', namespaces=namespaces))
            
            # Look for ee:set-payload with DataWeave code
            dw_elements.extend(root.xpath('//ee:set-payload', namespaces=namespaces))
            
            for i, dw_elem in enumerate(dw_elements):
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
                    dw_count += 1
                    embedded_file_name = f"{os.path.basename(file_path)}_transform_{i+1}"
                    
                    # Create a parser with the content
                    parser = DataWeaveParser(dw_content=dw_code)
                    summary = parser.get_transformation_summary()
                    
                    # Skip if there was an error
                    if 'error' in summary:
                        continue
                        
                    summary['file_path'] = f"{file_path}#{embedded_file_name}"
                    transformations.append(summary)
                    
                    if summary.get('dw_version'):
                        versions.add(summary['dw_version'])
                    if summary.get('output_mime_type'):
                        output_types.add(summary['output_mime_type'])
                    
                    complexity = summary.get('complexity', 0)
                    if isinstance(complexity, (int, float)):
                        total_complexity += complexity
        except Exception as e:
            print(f"Error parsing XML file {file_path} for DataWeave: {e}")
    
    print(f"Found {dw_count} embedded DataWeave transformations in XML files")
    
    avg_complexity = total_complexity / len(transformations) if transformations else 0
    
    return {
        'transformations': transformations,
        'stats': {
            'total': len(transformations),
            'versions': list(versions),
            'output_types': list(output_types),
            'avg_complexity': avg_complexity
        }
    } 