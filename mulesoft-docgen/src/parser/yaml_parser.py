"""
YAML configuration parser for MuleSoft environment files.
This module extracts configuration information from YAML files.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional

class YamlConfigParser:
    """Parser for MuleSoft YAML configuration files."""
    
    def __init__(self, yaml_file_path: str):
        """
        Initialize with a YAML file path.
        
        Args:
            yaml_file_path: Path to the YAML configuration file
        """
        self.yaml_file_path = yaml_file_path
        self.config = None
        self.parse()
    
    def parse(self) -> None:
        """Parse the YAML file and load the configuration."""
        try:
            with open(self.yaml_file_path, 'r') as file:
                self.config = yaml.safe_load(file)
        except Exception as e:
            print(f"Error parsing YAML file {self.yaml_file_path}: {e}")
            self.config = {}
    
    def get_environment_name(self) -> str:
        """
        Extract environment name from the file name.
        
        Returns:
            Environment name (e.g., DEV, UAT, PROD)
        """
        file_name = os.path.basename(self.yaml_file_path)
        env_name = os.path.splitext(file_name)[0]
        return env_name.upper()
    
    def get_all_configurations(self) -> Dict[str, Any]:
        """
        Get all configurations from the YAML file.
        
        Returns:
            Dictionary of all configurations
        """
        return self.config or {}
    
    def get_connection_details(self) -> Dict[str, Dict[str, Any]]:
        """
        Extract connection details from the configuration.
        
        Returns:
            Dictionary of connection details
        """
        result = {}
        
        if not self.config:
            return result
        
        # Look for common connection patterns in MuleSoft YAML files
        for key, value in self.config.items():
            # SFTP connection details
            if 'sftp' in key.lower() and isinstance(value, dict):
                connection_type = 'SFTP'
                result[key] = {
                    'type': connection_type,
                    'details': value
                }
            
            # Database connection details
            elif any(db_term in key.lower() for db_term in ['db', 'database', 'jdbc']) and isinstance(value, dict):
                connection_type = 'Database'
                result[key] = {
                    'type': connection_type,
                    'details': value
                }
            
            # HTTP/API connection details
            elif any(http_term in key.lower() for http_term in ['http', 'api', 'rest', 'soap']) and isinstance(value, dict):
                connection_type = 'HTTP/API'
                result[key] = {
                    'type': connection_type,
                    'details': value
                }
            
            # File system details
            elif any(file_term in key.lower() for file_term in ['file', 'directory', 'path']) and isinstance(value, (dict, str)):
                connection_type = 'File System'
                if isinstance(value, str):
                    result[key] = {
                        'type': connection_type,
                        'details': {'path': value}
                    }
                else:
                    result[key] = {
                        'type': connection_type,
                        'details': value
                    }
        
        return result
    
    def get_credentials(self, sanitize: bool = True) -> Dict[str, Dict[str, Any]]:
        """
        Extract credential information (sanitized by default).
        
        Args:
            sanitize: Whether to mask credential values
        
        Returns:
            Dictionary of credential information
        """
        result = {}
        
        if not self.config:
            return result
        
        # Look for credential patterns
        for key, value in self.config.items():
            if any(cred_term in key.lower() for cred_term in ['user', 'username', 'password', 'credential', 'secret', 'key', 'token', 'auth']):
                if isinstance(value, dict):
                    sanitized_value = {}
                    for k, v in value.items():
                        if sanitize and any(secret_term in k.lower() for secret_term in ['password', 'secret', 'key', 'token']):
                            sanitized_value[k] = '********'
                        else:
                            sanitized_value[k] = v
                    result[key] = sanitized_value
                else:
                    if sanitize and any(secret_term in key.lower() for secret_term in ['password', 'secret', 'key', 'token']):
                        result[key] = '********'
                    else:
                        result[key] = value
        
        return result
    
    def get_property_categories(self) -> Dict[str, Dict[str, Any]]:
        """
        Categorize properties by their likely purpose.
        
        Returns:
            Dictionary of categorized properties
        """
        categories = {
            'Connections': {},
            'Endpoints': {},
            'Security': {},
            'File Paths': {},
            'Timeouts': {},
            'Features': {},
            'Other': {}
        }
        
        if not self.config:
            return categories
        
        for key, value in self.config.items():
            # Connection properties
            if any(conn_term in key.lower() for conn_term in ['host', 'port', 'url', 'connection', 'server']):
                categories['Connections'][key] = value
            
            # Endpoint properties
            elif any(endpoint_term in key.lower() for endpoint_term in ['endpoint', 'api', 'path', 'route']):
                categories['Endpoints'][key] = value
            
            # Security properties
            elif any(security_term in key.lower() for security_term in ['auth', 'token', 'key', 'secret', 'password', 'user', 'cert']):
                if isinstance(value, str) and any(secret_term in key.lower() for secret_term in ['password', 'secret', 'key', 'token']):
                    categories['Security'][key] = '********'
                else:
                    categories['Security'][key] = value
            
            # File path properties
            elif any(file_term in key.lower() for file_term in ['file', 'path', 'directory', 'folder']):
                categories['File Paths'][key] = value
            
            # Timeout properties
            elif any(timeout_term in key.lower() for timeout_term in ['timeout', 'interval', 'delay', 'ttl']):
                categories['Timeouts'][key] = value
            
            # Feature flags or toggles
            elif any(feature_term in key.lower() for feature_term in ['feature', 'flag', 'toggle', 'enable', 'disable']):
                categories['Features'][key] = value
            
            # Everything else
            else:
                categories['Other'][key] = value
        
        # Remove empty categories
        return {k: v for k, v in categories.items() if v}
    
def compare_environments(env1_file: str, env2_file: str) -> Dict[str, Any]:
    """
    Compare two environment configurations and highlight differences.
    
    Args:
        env1_file: Path to first environment file
        env2_file: Path to second environment file
    
    Returns:
        Dictionary with comparison results
    """
    parser1 = YamlConfigParser(env1_file)
    parser2 = YamlConfigParser(env2_file)
    
    env1_name = parser1.get_environment_name()
    env2_name = parser2.get_environment_name()
    
    env1_config = parser1.get_all_configurations()
    env2_config = parser2.get_all_configurations()
    
    # Find keys in both configurations
    all_keys = set(env1_config.keys()).union(set(env2_config.keys()))
    
    result = {
        'env1': {
            'name': env1_name,
            'file': os.path.basename(env1_file)
        },
        'env2': {
            'name': env2_name,
            'file': os.path.basename(env2_file)
        },
        'only_in_env1': {},
        'only_in_env2': {},
        'different_values': {},
        'identical': {}
    }
    
    for key in all_keys:
        # Keys only in env1
        if key in env1_config and key not in env2_config:
            result['only_in_env1'][key] = env1_config[key]
            continue
        
        # Keys only in env2
        if key in env2_config and key not in env1_config:
            result['only_in_env2'][key] = env2_config[key]
            continue
        
        # Keys in both but with different values
        if env1_config[key] != env2_config[key]:
            result['different_values'][key] = {
                env1_name: env1_config[key],
                env2_name: env2_config[key]
            }
        else:
            # Keys with identical values
            result['identical'][key] = env1_config[key]
    
    return result

def parse_yaml_directory(directory_path: str) -> Dict[str, Any]:
    """
    Parse all YAML files in a directory.
    
    Args:
        directory_path: Path to directory containing YAML files
    
    Returns:
        Dictionary with environment configurations and comparisons
    """
    result = {
        'environments': {},
        'comparisons': []
    }
    
    yaml_files = []
    
    # Find YAML files
    for file_path in Path(directory_path).glob('*.yaml'):
        yaml_files.append(str(file_path))
    
    for file_path in Path(directory_path).glob('*.yml'):
        yaml_files.append(str(file_path))
    
    # Parse each YAML file
    for yaml_file in yaml_files:
        parser = YamlConfigParser(yaml_file)
        env_name = parser.get_environment_name()
        
        result['environments'][env_name] = {
            'file': os.path.basename(yaml_file),
            'configurations': parser.get_all_configurations(),
            'connections': parser.get_connection_details(),
            'credentials': parser.get_credentials(),
            'categories': parser.get_property_categories()
        }
    
    # Generate comparisons if multiple environments exist
    env_names = list(result['environments'].keys())
    if len(env_names) > 1:
        for i in range(len(env_names)):
            for j in range(i+1, len(env_names)):
                env1 = env_names[i]
                env2 = env_names[j]
                
                env1_file = next(file for file in yaml_files if parser.get_environment_name() == env1)
                env2_file = next(file for file in yaml_files if parser.get_environment_name() == env2)
                
                comparison = compare_environments(env1_file, env2_file)
                result['comparisons'].append(comparison)
    
    return result 