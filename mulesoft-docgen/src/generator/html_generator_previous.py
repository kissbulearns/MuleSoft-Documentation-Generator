"""HTML documentation generator for MuleSoft interfaces.
This module generates HTML documentation from the parsed MuleSoft interfaces.
"""
import os
import shutil
import json
from pathlib import Path
from typing import Dict, List, Any
from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..model.interface import Interface, Flow
from ..parser.yaml_parser import parse_yaml_directory
from ..parser.dataweave_parser import parse_dataweave_directory
from ..parser.error_handler_parser import analyze_error_handling
from .flow_visualizer import FlowVisualizer

# Either metadata_parser or metadata_extractor can be used - both provide the extract_metadata function
# metadata_parser is the original, metadata_extractor is the extended version
from ..parser.metadata_parser import extract_metadata
# If you need more advanced metadata extraction, use this import instead:
# from ..parser.metadata_extractor import extract_metadata as extract_metadata_extended

from .flow_visualizer import generate_visualization

class HtmlGenerator:
    """HTML documentation generator for MuleSoft interfaces."""
    def __init__(self, template_dir: str = None):
        """
        Initialize the HTML generator.
        
        Args:
            template_dir: Directory containing Jinja2 templates
        """
        if template_dir is None:
            # Use default templates directory
            script_dir = os.path.dirname(os.path.abspath(__file__))
            template_dir = os.path.join(script_dir, 'templates')
        
        # Create templates directory if it doesn't exist
        os.makedirs(template_dir, exist_ok=True)
        
        # Create Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml']),
            extensions=['jinja2.ext.do']
        )
        
        # Add custom filters to handle both dict and object access
        self.env.filters['get_attr'] = self._get_attr_filter
        
        # Create default templates if they don't exist
        self._ensure_templates_exist(template_dir)
    
    def _ensure_templates_exist(self, template_dir: str) -> None:
        """
        Ensure that the required templates exist, create them if they don't.
        
        Args:
            template_dir: Directory to store templates
        """
        templates = {
            'index.html': self._get_index_template(),
            'interface.html': self._get_interface_template(),
            'flow.html': self._get_flow_template(),
            'style.css': self._get_css_template(),
            'configurations.html': self._get_configurations_template(),
            'dataweave.html': self._get_dataweave_template(),
            'flow_diagram.html': self._get_flow_diagram_template(),
            'error_handling.html': self._get_error_handling_template(),
            'metadata.html': self._get_metadata_template()
        }
        
        for filename, content in templates.items():
            file_path = os.path.join(template_dir, filename)
            if not os.path.exists(file_path):
                with open(file_path, 'w') as f:
                    f.write(content)
    
    def generate(self, interface, output_dir, xml_dir=None, jar_dir=None):
        """Generate HTML documentation for the interface.
        
        Args:
            interface: The interface to generate documentation for.
            output_dir: The output directory to write the documentation to.
            xml_dir: The directory containing the XML files to parse.
            jar_dir: The directory containing the JAR files to parse.
        
        Returns:
            None
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Initialize data structures
        flows = interface.flows
        configs = self._extract_config_data(xml_dir) if xml_dir else {}
        dw_transforms = self._extract_dataweave_data(xml_dir) if xml_dir else []
        error_handlers = self._analyze_error_handling(interface) if interface else {}
        metadata = self._extract_metadata(xml_dir, jar_dir) if xml_dir or jar_dir else {}
        
        # Generate flow diagrams
        flow_diagrams = {}
        if interface and interface.flows:
            flow_visualizer = FlowVisualizer()
            mermaid_diagram, flow_references = flow_visualizer.generate_flow_diagram(interface)
            flow_diagrams = {
                'mermaid_diagram': mermaid_diagram,
                'references': flow_references,
                'd3_data': self._generate_d3_data(interface)
            }
        
        # Generate index page
        index_html = self._generate_index_html(interface, flows, configs, dw_transforms, error_handlers, metadata)
        with open(os.path.join(output_dir, 'index.html'), 'w') as f:
            f.write(index_html)
        
        # Generate flow pages
        if flows:
            for flow in flows:
                flow_html = self._generate_flow_html(interface, flow)
                with open(os.path.join(output_dir, f'flow_{flow.id}.html'), 'w') as f:
                    f.write(flow_html)
        
        # Generate configurations page
        if configs:
            configs_html = self._generate_configs_html(interface, configs)
            with open(os.path.join(output_dir, 'configurations.html'), 'w') as f:
                f.write(configs_html)
        
        # Generate DataWeave transformations page
        if dw_transforms:
            dw_html = self._generate_dataweave_html(interface, dw_transforms)
            with open(os.path.join(output_dir, 'dataweave.html'), 'w') as f:
                f.write(dw_html)
        
        # Generate flow diagram page
        if flow_diagrams:
            flow_diagram_html = self._generate_flow_diagram_html(
                interface, 
                flow_diagrams.get('references', {}),
                flow_diagrams.get('mermaid_diagram', ''),
                flow_diagrams.get('d3_data', {})
            )
            with open(os.path.join(output_dir, 'flow_diagram.html'), 'w') as f:
                f.write(flow_diagram_html)
        
        # Generate error handling page
        if error_handlers:
            error_html = self._generate_error_handling_html(interface, error_handlers)
            with open(os.path.join(output_dir, 'error_handling.html'), 'w') as f:
                f.write(error_html)
        
        # Generate metadata page
        if metadata:
            metadata_html = self._generate_metadata_html(interface, metadata)
            with open(os.path.join(output_dir, 'metadata.html'), 'w') as f:
                f.write(metadata_html)
        
        # Copy static assets if needed
        self._copy_static_assets(output_dir)
    
    def _get_index_template(self) -> str:
        """Return the default index.html template."""
        return """<!DOCTYPE html>
<html lang="en">
<head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>MuleSoft Interfaces Documentation</title>
        <link rel="stylesheet" href="style.css">
</head>
<body>
        <header>
        <h1>MuleSoft Interfaces Documentation</h1>
        </header>
    
    <main>
        <section class="overview">
            <h2>Interfaces Overview</h2>
            <p>This documentation provides details about the MuleSoft interfaces in this application.</p>
            
            <table class="interfaces-table">
                <thead>
                    <tr>
                        <th>Interface Name</th>
                        <th>Purpose</th>
                        <th>Flows</th>
                        <th>Source Types</th>
                    </tr>
                </thead>
                <tbody>
                    {% for interface in interfaces %}
                    <tr>
                        <td><a href="interface_{{ interface.name.lower().replace(' ', '_') }}.html">{{ interface.name }}</a></td>
                        <td>{{ interface.infer_purpose() }}</td>
                        <td>{{ interface.flows|length }}</td>
                        <td>
                            {% set source_types = [] %}
                            {% for flow in interface.source_flows %}
                                {% if flow.source and flow.source.get('type') and flow.source.get('type') not in source_types %}
                                    {{ source_types.append(flow.source.get('type')) }}
                                {% endif %}
                            {% endfor %}
                            {{ source_types|join(', ') }}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </section>
    </main>
    
    <footer>
        <p>Generated with MuleSoft Documentation Generator</p>
    </footer>
</body>
</html>"""
    def _get_interface_template(self) -> str:
        """Return the default interface.html template."""
        return """<!DOCTYPE html>
<html lang="en">
<head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{{ interface.name }} - MuleSoft Interface Documentation</title>
        <link rel="stylesheet" href="style.css">
</head>
<body>
        <header>
        <h1>{{ interface.name }}</h1>
        <p class="breadcrumb"><a href="index.html">Home</a> &gt; {{ interface.name }}</p>
        </header>
    
    <main>
        <section class="interface-overview">
            <h2>Interface Overview</h2>
            <p>{{ interface.description or 'No description available.' }}</p>
            
            <div class="interface-details">
                <div class="detail-item">
                    <h3>Purpose</h3>
                    <p>{{ interface.infer_purpose() }}</p>
                </div>
                
                <div class="detail-item">
                    <h3>Flows</h3>
                    <p>Total: {{ interface.flows|length }}</p>
                    <p>Source Flows: {{ interface.source_flows|length }}</p>
                    <p>Sub-flows: {{ interface.subflows|length }}</p>
                </div>
            </div>
        </section>
        
        <section class="global-configs">
            <h2>Global Configurations</h2>
            {% if interface.global_configs %}
                <table class="configs-table">
                    <thead>
                        <tr>
                            <th>Configuration Name</th>
                            <th>Type</th>
                            <th>Details</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for name, config in interface.global_configs.items() %}
                        <tr>
                            <td>{{ name }}</td>
                            <td>{{ config.get('type', 'Unknown') }}</td>
                            <td>
                                {% if config.get('type') == 'file-config' %}
                                    File configuration
                                {% elif config.get('type') == 'sftp-config' %}
                                    SFTP connection to {{ config.get('connection', {}).get('host', 'unknown host') }}
                                {% elif config.get('type') == 'http-listener-config' %}
                                    HTTP listener on {{ config.get('host', 'unknown host') }}:{{ config.get('port', 'unknown port') }}
                                {% else %}
                                    {{ config }}
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            {% else %}
                <p>No global configurations found.</p>
            {% endif %}
        </section>
        
        <section class="source-flows">
            <h2>Source Flows</h2>
            {% if interface.source_flows %}
                <table class="flows-table">
                    <thead>
                        <tr>
                            <th>Flow Name</th>
                            <th>Source Type</th>
                            <th>Details</th>
                            <th>File</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for flow in interface.source_flows %}
                        <tr>
                            <td><a href="flow_{{ interface.name.lower().replace(' ', '_') }}_{{ flow.id.lower().replace(' ', '_') }}.html">{{ flow.id }}</a></td>
                            <td>{{ flow.source.get('type', 'Unknown') }}</td>
                            <td>
                                {% if flow.source.get('type') == 'file-listener' %}
                                    Directory: {{ flow.source.get('directory', 'Not specified') }}<br>
                                    Pattern: {{ flow.source.get('pattern', 'Not specified') }}
                                {% elif flow.source.get('type') == 'sftp-listener' %}
                                    Directory: {{ flow.source.get('directory', 'Not specified') }}<br>
                                    Pattern: {{ flow.source.get('pattern', 'Not specified') }}
                                {% elif flow.source.get('type') == 'http-listener' %}
                                    Path: {{ flow.source.get('path', 'Not specified') }}<br>
                                    Method: {{ flow.source.get('method', 'All methods') }}
                                {% elif flow.source.get('type') == 'scheduler' %}
                                    Frequency: {{ flow.source.get('frequency', 'Not specified') }}
                                {% else %}
                                    {{ flow.source }}
                                {% endif %}
                            </td>
                            <td>{{ flow.file_name }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            {% else %}
                <p>No source flows found.</p>
            {% endif %}
        </section>
        
        <section class="sub-flows">
            <h2>Sub-flows</h2>
            {% if interface.subflows %}
                <table class="flows-table">
                    <thead>
                        <tr>
                            <th>Sub-flow Name</th>
                            <th>Description</th>
                            <th>File</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for flow in interface.subflows %}
                        <tr>
                            <td><a href="flow_{{ interface.name.lower().replace(' ', '_') }}_{{ flow.id.lower().replace(' ', '_') }}.html">{{ flow.id }}</a></td>
                            <td>{{ flow.description }}</td>
                            <td>{{ flow.file_name }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            {% else %}
                <p>No sub-flows found.</p>
            {% endif %}
        </section>
    </main>
    
    <footer>
        <p>Generated with MuleSoft Documentation Generator</p>
    </footer>
</body>
</html>"""
    def _get_flow_template(self) -> str:
        """Return the default flow.html template."""
        return """<!DOCTYPE html>
<html lang="en">
<head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{{ flow|get_attr('id') }} - Flow Documentation</title>
        <link rel="stylesheet" href="../style.css">
</head>
<body>
        <header>
        <h1>{{ flow|get_attr('id') }}</h1>
        <p class="breadcrumb">
            <a href="index.html">Home</a> &gt; 
            <a href="interface_{{ interface.name.lower().replace(' ', '_') }}.html">{{ interface.name }}</a> &gt; 
            {{ flow|get_attr('id') }}
        </p>
        </header>
    
    <main>
        <section class="flow-overview">
            <h2>Flow Overview</h2>
            <div class="flow-details">
                <div class="detail-item">
                    <h3>Type</h3>
                    <p>{{ flow|get_attr('type') }}</p>
                </div>
                
                <div class="detail-item">
                    <h3>Description</h3>
                    <p>{{ flow|get_attr('description', 'No description available.') }}</p>
                </div>
                
                <div class="detail-item">
                    <h3>File</h3>
                    <p>{{ flow|get_attr('file_name', 'Unknown') }}</p>
                </div>
                
                {% if flow|get_attr('source_type') %}
                <div class="detail-item">
                    <h3>Source Type</h3>
                    <p>{{ flow|get_attr('source_type') }}</p>
                </div>
                {% endif %}
                
                {% if flow|get_attr('input_format') != 'Unknown' %}
                <div class="detail-item">
                    <h3>Input Format</h3>
                    <p>{{ flow|get_attr('input_format') }}</p>
                </div>
                {% endif %}
                
                {% if flow|get_attr('output_format') != 'Unknown' %}
                <div class="detail-item">
                    <h3>Output Format</h3>
                    <p>{{ flow|get_attr('output_format') }}</p>
                </div>
                {% endif %}
            </div>
        </section>
        
        {% if flow|get_attr('source') %}
        <section class="flow-source">
            <h2>Source Configuration</h2>
            <div class="source-details">
                {% if flow|get_attr('source.get.type') == 'file-listener' %}
                    <p><strong>Type:</strong> File Listener</p>
                    <p><strong>Directory:</strong> {{ flow|get_attr('source.get.directory', 'Not specified') }}</p>
                    <p><strong>Pattern:</strong> {{ flow|get_attr('source.get.pattern', 'Not specified') }}</p>
                {% elif flow|get_attr('source.get.type') == 'sftp-listener' %}
                    <p><strong>Type:</strong> SFTP Listener</p>
                    <p><strong>Directory:</strong> {{ flow|get_attr('source.get.directory', 'Not specified') }}</p>
                    <p><strong>Pattern:</strong> {{ flow|get_attr('source.get.pattern', 'Not specified') }}</p>
                {% elif flow|get_attr('source.get.type') == 'http-listener' %}
                    <p><strong>Type:</strong> HTTP Listener</p>
                    <p><strong>Path:</strong> {{ flow|get_attr('source.get.path', 'Not specified') }}</p>
                    <p><strong>Method:</strong> {{ flow|get_attr('source.get.method', 'All methods') }}</p>
                {% elif flow|get_attr('source.get.type') == 'scheduler' %}
                    <p><strong>Type:</strong> Scheduler</p>
                    <p><strong>Frequency:</strong> {{ flow|get_attr('source.get.frequency', 'Not specified') }}</p>
                {% else %}
                    <p><strong>Type:</strong> {{ flow|get_attr('source.get.type', 'Unknown') }}</p>
                    <p><strong>Attributes:</strong> 
                    {% for key, value in flow|get_attr('source.get.attributes', {}).items() %}
                        {{ key }}: {{ value }}{% if not loop.last %}, {% endif %}
                    {% endfor %}
                    </p>
                {% endif %}
            </div>
        </section>
        {% endif %}
        
        <section class="flow-processors">
            <h2>Flow Processors</h2>
            {% if flow|get_attr('processors') %}
            <ol class="processor-list">
                {% for processor in flow|get_attr('processors') %}
                <li class="processor">
                    <div class="processor-details">
                        <h3>{{ processor|get_attr('type', 'Unknown Processor') }}</h3>
                        
                        {% if processor|get_attr('type') == 'transform' and processor|get_attr('transformation') %}
                            <div class="transformation">
                                <p><strong>Transformation Type:</strong> {{ processor|get_attr('transformation.get.type', 'Unknown') }}</p>
                                <div class="code-block">
                                    <pre>{{ processor|get_attr('transformation.get.code', 'No code available') }}</pre>
                                </div>
                            </div>
                        {% endif %}
                        
                        {% if processor|get_attr('type') in ['file:write', 'sftp:write'] and processor|get_attr('file_operation') %}
                            <div class="file-operation">
                                <p><strong>Path:</strong> {{ processor|get_attr('file_operation.get.path', 'Not specified') }}</p>
                                <p><strong>Mode:</strong> {{ processor|get_attr('file_operation.get.mode', 'Overwrite') }}</p>
                            </div>
                        {% endif %}
                        
                        {% if processor|get_attr('type') == 'choice' and processor|get_attr('routes') %}
                            <div class="choice-router">
                                <p><strong>Routes:</strong></p>
                                <ul class="routes">
                                    {% for route in processor|get_attr('routes', []) %}
                                    <li>
                                        <p><strong>Condition:</strong> {{ route|get_attr('condition', 'Unknown') }}</p>
                                        {% if route|get_attr('processors') %}
                                            <p><strong>Processors:</strong></p>
                                            <ul class="nested-processors">
                                                {% for nested in route|get_attr('processors', []) %}
                                                <li>{{ nested|get_attr('type', 'Unknown') }}</li>
                                                {% endfor %}
                                            </ul>
                                        {% endif %}
                                    </li>
                                    {% endfor %}
                                </ul>
                            </div>
                        {% endif %}
                        
                        {% if processor|get_attr('attributes') and processor|get_attr('type') not in ['transform', 'file:write', 'sftp:write', 'choice'] %}
                            <div class="processor-attributes">
                                <p><strong>Attributes:</strong></p>
                                <ul>
                                    {% for key, value in processor|get_attr('attributes', {}).items() %}
                                    <li><strong>{{ key }}:</strong> {{ value }}</li>
                                    {% endfor %}
                                </ul>
                            </div>
                        {% endif %}
                    </div>
                </li>
                {% endfor %}
            </ol>
            {% else %}
            <p>No processors found in this flow.</p>
            {% endif %}
        </section>
    </main>
    
    <footer>
        <p>Generated with MuleSoft Documentation Generator</p>
    </footer>
</body>
</html>"""
    def _get_css_template(self) -> str:
        """Return the default CSS template."""
        return """/* MuleSoft Documentation Generator CSS */

/* General styles */
body {
    font-family: Arial, sans-serif;
    line-height: 1.6;
    color: #333;
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

header {
    margin-bottom: 30px;
    border-bottom: 2px solid #0072CE;
    padding-bottom: 10px;
}

h1 {
    color: #0072CE;
}

h2 {
    color: #0072CE;
    border-bottom: 1px solid #ddd;
    padding-bottom: 5px;
}

a {
    color: #0072CE;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

/* Tables */
table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 20px;
}

th, td {
    border: 1px solid #ddd;
    padding: 8px 12px;
    text-align: left;
}

th {
    background-color: #f2f2f2;
    color: #0072CE;
}

tr:nth-child(even) {
    background-color: #f9f9f9;
}

/* Interface details */
.interface-details, .flow-details {
    display: flex;
    flex-wrap: wrap;
    gap: 20px;
    margin-bottom: 20px;
}

.detail-item {
    flex: 1;
    min-width: 200px;
    border: 1px solid #ddd;
    padding: 10px;
    border-radius: 5px;
}

.detail-item h3 {
    margin-top: 0;
    color: #0072CE;
}

/* Flow processors */
.processor-list {
    list-style-type: none;
    padding: 0;
}

.processor {
    margin-bottom: 15px;
    border: 1px solid #ddd;
    padding: 10px;
    border-radius: 5px;
}

.processor h3 {
    margin-top: 0;
    color: #0072CE;
}

.code-block {
    background-color: #f5f5f5;
    padding: 10px;
    border-radius: 5px;
    overflow-x: auto;
}

pre {
    margin: 0;
    white-space: pre-wrap;
}

/* Breadcrumbs */
.breadcrumb {
    font-size: 0.9em;
    color: #666;
}

/* Footer */
footer {
    margin-top: 30px;
    padding-top: 10px;
    border-top: 1px solid #ddd;
    text-align: center;
    font-size: 0.9em;
    color: #666;
}

/* Choice router */
.routes {
    margin-top: 10px;
}

.nested-processors {
    margin-top: 5px;
    margin-bottom: 10px;
}

/* Source details */
.source-details {
    border: 1px solid #ddd;
    padding: 10px;
    border-radius: 5px;
    margin-bottom: 20px;
}

/* Responsive design */
@media (max-width: 768px) {
    .interface-details, .flow-details {
        flex-direction: column;
    }
    
    .detail-item {
        width: 100%;
    }
}"""
    def _get_attr_filter(self, obj, attr, default=''):
        """
        Get an attribute from an object, with a default value.
        Supports both dictionary access and object attribute access.
        Also supports nested attributes using dot notation.
        
        Args:
            obj: Object to get attribute from
            attr: Attribute name (can use dots for nested attributes)
            default: Default value if attribute not found
            
        Returns:
            Attribute value or default
        """
        if not obj:
            return default
            
        # Check if we're using dot notation for nested attributes
        if isinstance(attr, str) and '.' in attr:
            parts = attr.split('.')
            current = obj
            
            for part in parts:
                # Handle dictionary access
                if isinstance(current, dict) and part in current:
                    current = current[part]
                # Handle special case for 'get' method on dictionaries
                elif isinstance(current, dict) and part == 'get':
                    # Don't do anything, we'll handle the next part as a get() parameter
                    continue
                # Handle object attribute access
                elif hasattr(current, part):
                    current = getattr(current, part)
                # Handle failure
                else:
                    return default
                    
            return current
        
        # Simple case - no dots
        if isinstance(obj, dict):
            return obj.get(attr, default)
        elif hasattr(obj, attr):
            return getattr(obj, attr, default)
        return default

    def _get_configurations_template(self) -> str:
        """Return the default configurations.html template."""
        return """{% extends "base.html" %}

{% block title %}{{ interface.name }} - Environment Configurations{% endblock %}

{% block content %}
<div class="container">
  <div class="row mb-4">
    <div class="col">
      <h1>Environment Configurations</h1>
      <p class="lead">{{ interface.name }}</p>
      <p>This page documents the environment-specific configurations found in this MuleSoft application.</p>
    </div>
  </div>
  
  {% if config_data and config_data.environments %}
  <div class="row mb-4">
    <div class="col">
      <div class="card">
        <div class="card-header bg-light">
          <h5 class="mb-0">Available Environments</h5>
        </div>
        <div class="card-body">
          <div class="row">
            {% for env in config_data.environments %}
            <div class="col-md-3 col-sm-6">
              <div class="card mb-3">
                <div class="card-body text-center">
                  <h3>{{ env }}</h3>
                  <p class="text-muted mb-0">Environment</p>
                </div>
              </div>
            </div>
            {% endfor %}
          </div>
        </div>
      </div>
    </div>
  </div>
  
  <div class="row mb-4">
    <div class="col">
      <div class="card">
        <div class="card-header bg-light">
          <h5 class="mb-0">Configuration Properties</h5>
        </div>
        <div class="card-body">
          <div class="row mb-3">
            <div class="col">
              <div class="input-group">
                <span class="input-group-text"><i class="bi bi-search"></i></span>
                <input type="text" id="configSearch" class="form-control" placeholder="Search configurations...">
              </div>
            </div>
          </div>
          
          <div class="table-responsive">
            <table class="table table-striped table-hover">
              <thead>
                <tr>
                  <th>Property</th>
                  {% for env in config_data.environments %}
                  <th>{{ env }}</th>
                  {% endfor %}
                </tr>
              </thead>
              <tbody id="configTableBody">
                {% for key, values in config_data.properties.items() %}
                <tr class="config-row">
                  <td class="fw-bold">{{ key }}</td>
                  {% for env in config_data.environments %}
                  <td>
                    {% if env in values %}
                      {% if values[env]|string|length > 100 %}
                        <span class="badge bg-secondary" title="{{ values[env] }}">Long value</span>
                      {% elif "password" in key or "secret" in key or "key" in key %}
                        <span class="badge bg-warning">Secured</span>
                      {% else %}
                        {{ values[env] }}
                      {% endif %}
                    {% else %}
                      <span class="text-muted">Not set</span>
                    {% endif %}
                  </td>
                  {% endfor %}
                </tr>
                {% endfor %}
              </tbody>
            </table>
          </div>
          
          <div id="noResults" class="alert alert-info d-none">
            No configuration properties match your search.
          </div>
        </div>
      </div>
    </div>
  </div>
  
  {% if config_data.comparisons and config_data.comparisons|length > 0 %}
  <div class="row mb-4">
    <div class="col">
      <div class="card">
        <div class="card-header bg-light">
          <h5 class="mb-0">Environment Differences</h5>
        </div>
        <div class="card-body">
          {% for comp in config_data.comparisons %}
          <div class="card mb-3">
            <div class="card-header">
              <h6 class="mb-0">{{ comp.env1 }} vs {{ comp.env2 }}</h6>
            </div>
            <div class="card-body">
              {% if comp.differences|length > 0 %}
              <div class="table-responsive">
                <table class="table table-sm">
                  <thead>
                    <tr>
                      <th>Property</th>
                      <th>{{ comp.env1 }}</th>
                      <th>{{ comp.env2 }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {% for diff in comp.differences %}
                    <tr>
                      <td>{{ diff.key }}</td>
                      <td>
                        {% if diff.env1_value is none %}
                        <span class="badge bg-danger">Missing</span>
                        {% elif "password" in diff.key or "secret" in diff.key or "key" in diff.key %}
                        <span class="badge bg-warning">Secured</span>
                        {% else %}
                        {{ diff.env1_value }}
                        {% endif %}
                      </td>
                      <td>
                        {% if diff.env2_value is none %}
                        <span class="badge bg-danger">Missing</span>
                        {% elif "password" in diff.key or "secret" in diff.key or "key" in diff.key %}
                        <span class="badge bg-warning">Secured</span>
                        {% else %}
                        {{ diff.env2_value }}
                        {% endif %}
                      </td>
                    </tr>
                    {% endfor %}
                  </tbody>
                </table>
              </div>
              {% else %}
              <div class="alert alert-success">
                No differences found between these environments.
              </div>
              {% endif %}
            </div>
          </div>
          {% endfor %}
        </div>
      </div>
    </div>
  </div>
  {% endif %}
  
  {% if config_data.connections and config_data.connections|length > 0 %}
  <div class="row mb-4">
    <div class="col">
      <div class="card">
        <div class="card-header bg-light">
          <h5 class="mb-0">Connection Details</h5>
        </div>
        <div class="card-body">
          <div class="table-responsive">
            <table class="table table-striped">
              <thead>
                <tr>
                  <th>Connection</th>
                  <th>Type</th>
                  <th>Host</th>
                  <th>Port</th>
                  <th>Environment</th>
                </tr>
              </thead>
              <tbody>
                {% for conn in config_data.connections %}
                <tr>
                  <td>{{ conn.name }}</td>
                  <td>{{ conn.type }}</td>
                  <td>{{ conn.host }}</td>
                  <td>{{ conn.port }}</td>
                  <td>{{ conn.environment }}</td>
                </tr>
                {% endfor %}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
  {% endif %}
  
  {% else %}
  <div class="alert alert-info">
    <h4 class="alert-heading">No Configuration Data Available</h4>
    <p>No environment configuration files (YAML) were found for this MuleSoft application.</p>
    <hr>
    <p class="mb-0">Environment configuration files typically define properties for different environments (DEV, QA, PROD, etc.)</p>
  </div>
  {% endif %}
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {
  // Search functionality
  const searchInput = document.getElementById('configSearch');
  const tableBody = document.getElementById('configTableBody');
  const noResults = document.getElementById('noResults');
  const rows = tableBody ? tableBody.querySelectorAll('tr.config-row') : [];
  
  if (searchInput && rows.length > 0) {
    searchInput.addEventListener('keyup', function() {
      const searchTerm = this.value.toLowerCase();
      let matchCount = 0;
      
      rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        if (text.includes(searchTerm)) {
          row.style.display = '';
          matchCount++;
        } else {
          row.style.display = 'none';
        }
      });
      
      if (noResults) {
        if (matchCount === 0) {
          noResults.classList.remove('d-none');
        } else {
          noResults.classList.add('d-none');
        }
      }
    });
  }
});
</script>
{% endblock %}"""
    def _get_dataweave_template(self) -> str:
        """Return the default dataweave.html template."""
        return """{% extends "base.html" %}

{% block title %}{{ interface.name }} - DataWeave Transformations{% endblock %}

{% block content %}
<div class="container">
  <div class="row mb-4">
    <div class="col">
      <h1>DataWeave Transformations</h1>
      <p class="lead">{{ interface.name }}</p>
      <p>This page documents the DataWeave transformations used in this MuleSoft application.</p>
    </div>
  </div>
  
  {% if dataweave_data and dataweave_data.transformations and dataweave_data.transformations|length > 0 %}
  <div class="row mb-4">
    <div class="col">
      <div class="card">
        <div class="card-header bg-light d-flex justify-content-between align-items-center">
          <h5 class="mb-0">Transformations Overview</h5>
          <div class="input-group" style="max-width: 300px;">
            <input type="text" id="dwSearch" class="form-control form-control-sm" placeholder="Search transformations...">
            <span class="input-group-text"><i class="bi bi-search"></i></span>
          </div>
        </div>
        <div class="card-body">
          <div class="row mb-4">
            <div class="col-md-3 col-sm-6">
              <div class="card mb-3">
                <div class="card-body text-center">
                  <h3>{{ dataweave_data.transformations|length }}</h3>
                  <p class="text-muted mb-0">Total Transformations</p>
                </div>
              </div>
            </div>
            
            <div class="col-md-3 col-sm-6">
              <div class="card mb-3">
                <div class="card-body text-center">
                  <h3>{{ dataweave_data.stats.versions|length }}</h3>
                  <p class="text-muted mb-0">DataWeave Versions</p>
                </div>
              </div>
            </div>
            
            <div class="col-md-3 col-sm-6">
              <div class="card mb-3">
                <div class="card-body text-center">
                  <h3>{{ dataweave_data.stats.output_types|length }}</h3>
                  <p class="text-muted mb-0">Output Types</p>
                </div>
              </div>
            </div>
            
            <div class="col-md-3 col-sm-6">
              <div class="card mb-3">
                <div class="card-body text-center">
                  <h3>{{ dataweave_data.stats.avg_complexity|round(1) }}</h3>
                  <p class="text-muted mb-0">Avg. Complexity</p>
                </div>
              </div>
            </div>
          </div>
          
          <div class="accordion" id="dwAccordion">
            {% for transform in dataweave_data.transformations %}
            <div class="accordion-item dw-item">
              <h2 class="accordion-header" id="heading{{ loop.index }}">
                <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapse{{ loop.index }}" aria-expanded="false" aria-controls="collapse{{ loop.index }}">
                  <div class="d-flex justify-content-between align-items-center w-100 me-3">
                    <span>
                      <strong>{{ transform.file_path|replace('\\', '/')|split('/')|last }}</strong>
                      {% if transform.output_mime_type %}
                      <span class="badge bg-primary ms-2">{{ transform.output_mime_type }}</span>
                      {% endif %}
                    </span>
                    <span>
                      {% if transform.complexity >= 7 %}
                      <span class="badge bg-danger ms-1">High Complexity</span>
                      {% elif transform.complexity >= 4 %}
                      <span class="badge bg-warning ms-1">Medium Complexity</span>
                      {% else %}
                      <span class="badge bg-success ms-1">Low Complexity</span>
                      {% endif %}
                    </span>
                  </div>
                </button>
              </h2>
              <div id="collapse{{ loop.index }}" class="accordion-collapse collapse" aria-labelledby="heading{{ loop.index }}" data-bs-parent="#dwAccordion">
                <div class="accordion-body">
                  <div class="row mb-3">
                    <div class="col-md-6">
                      <h6 class="fw-bold">Details</h6>
                      <ul class="list-unstyled">
                        <li><strong>File:</strong> {{ transform.file_path }}</li>
                        <li><strong>Version:</strong> {{ transform.dw_version or 'Unknown' }}</li>
                        <li><strong>Output Type:</strong> {{ transform.output_mime_type or 'Unknown' }}</li>
                        <li><strong>Complexity:</strong> {{ transform.complexity }} / 10</li>
                      </ul>
                    </div>
                    
                    {% if transform.input_types %}
                    <div class="col-md-6">
                      <h6 class="fw-bold">Input Types</h6>
                      <ul class="list-unstyled">
                        {% for var_name, type_info in transform.input_types.items() %}
                        <li><strong>{{ var_name }}:</strong> {{ type_info }}</li>
                        {% endfor %}
                      </ul>
                    </div>
                    {% endif %}
                  </div>
                  
                  {% if transform.variables and transform.variables|length > 0 %}
                  <div class="row mb-3">
                    <div class="col">
                      <h6 class="fw-bold">Variables</h6>
                      <ul>
                        {% for var in transform.variables %}
                        <li>{{ var }}</li>
                        {% endfor %}
                      </ul>
                    </div>
                  </div>
                  {% endif %}
                  
                  {% if transform.functions and transform.functions|length > 0 %}
                  <div class="row mb-3">
                    <div class="col">
                      <h6 class="fw-bold">Functions</h6>
                      <ul>
                        {% for func in transform.functions %}
                        <li>{{ func }}</li>
                        {% endfor %}
                      </ul>
                    </div>
                  </div>
                  {% endif %}
                  
                  {% if transform.sample_mapping %}
                  <div class="row mb-3">
                    <div class="col">
                      <h6 class="fw-bold">Sample Mapping</h6>
                      <div class="code-block">
                        <pre><code class="dataweave">{{ transform.sample_mapping }}</code></pre>
                      </div>
                    </div>
                  </div>
                  {% endif %}
                  
                  {% if transform.code_preview %}
                  <div class="row">
                    <div class="col">
                      <h6 class="fw-bold">Code Preview</h6>
                      <div class="code-block">
                        <pre><code class="dataweave">{{ transform.code_preview }}</code></pre>
                      </div>
                    </div>
                  </div>
                  {% endif %}
                </div>
              </div>
            </div>
            {% endfor %}
          </div>
          
          <div id="noTransformations" class="alert alert-info d-none mt-3">
            No transformations match your search.
          </div>
        </div>
      </div>
    </div>
  </div>
  
  {% else %}
  <div class="alert alert-info">
    <h4 class="alert-heading">No DataWeave Transformations Found</h4>
    <p>No DataWeave transformations were found in this MuleSoft application.</p>
    <hr>
    <p class="mb-0">DataWeave transformations are typically found in .dwl files or embedded in XML configuration files.</p>
  </div>
  {% endif %}
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {
  // Search functionality for DataWeave transformations
  const searchInput = document.getElementById('dwSearch');
  const items = document.querySelectorAll('.dw-item');
  const noResults = document.getElementById('noTransformations');
  
  if (searchInput && items.length > 0) {
    searchInput.addEventListener('keyup', function() {
      const searchTerm = this.value.toLowerCase();
      let matchCount = 0;
      
      items.forEach(item => {
        const text = item.textContent.toLowerCase();
        if (text.includes(searchTerm)) {
          item.style.display = '';
          matchCount++;
        } else {
          item.style.display = 'none';
        }
      });
      
      if (noResults) {
        if (matchCount === 0) {
          noResults.classList.remove('d-none');
        } else {
          noResults.classList.add('d-none');
        }
      }
    });
  }
});
</script>
{% endblock %}"""
    def _get_flow_diagram_template(self) -> str:
        """Return the default flow_diagram.html template."""
        return """{% extends "base.html" %}

{% block title %}{{ interface.name }} - Flow Visualization{% endblock %}

{% block head %}
{{ super() }}
<script src="https://cdn.jsdelivr.net/npm/mermaid@9.4.3/dist/mermaid.min.js"></script>
<style>
  .diagram-container {
    background-color: white;
    overflow: auto;
    border-radius: 6px;
    border: 1px solid #ddd;
    margin-bottom: 30px;
  }
  .mermaid {
    padding: 20px;
  }
</style>
{% endblock %}

{% block content %}
<div class="container">
  <div class="row mb-4">
    <div class="col">
      <h1>Flow Visualization</h1>
      <p class="lead">{{ interface.name }}</p>
      <p>This page provides visual representations of the flows and their relationships within this MuleSoft interface.</p>
    </div>
  </div>

  {% if diagrams %}
  <div class="row mb-4">
    <div class="col">
      <div class="card">
        <div class="card-header bg-light">
          <h5 class="mb-0">Flow Diagram</h5>
        </div>
        <div class="card-body">
          <div class="controls">
            <div class="d-flex justify-content-end mb-2">
              <button id="zoomInMermaid" class="btn btn-sm btn-outline-secondary me-2">Zoom In</button>
              <button id="zoomOutMermaid" class="btn btn-sm btn-outline-secondary">Zoom Out</button>
            </div>
          </div>
          
          <div class="diagram-container">
            <div class="mermaid" id="mermaidDiagram">
              {{ mermaid_diagram }}
            </div>
          </div>
          
          <div class="mt-4">
            <h5>Legend</h5>
            <div class="row">
              <div class="col-md-3 col-sm-6">
                <div class="d-flex align-items-center mb-2">
                  <div style="width: 20px; height: 20px; background-color: #aaaaff; border: 1px solid #000066; margin-right: 10px;"></div>
                  <span>Standard Flow</span>
                </div>
              </div>
              <div class="col-md-3 col-sm-6">
                <div class="d-flex align-items-center mb-2">
                  <div style="width: 20px; height: 20px; background-color: #ffaaaa; border: 1px solid #660000; margin-right: 10px;"></div>
                  <span>Subflow</span>
                </div>
              </div>
              <div class="col-md-3 col-sm-6">
                <div class="d-flex align-items-center mb-2">
                  <div style="width: 20px; height: 20px; background-color: #aaffaa; border: 1px solid #006600; margin-right: 10px;"></div>
                  <span>Source Flow</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="row mb-4">
    <div class="col">
      <div class="card">
        <div class="card-header bg-light">
          <h5 class="mb-0">Flow Statistics</h5>
        </div>
        <div class="card-body">
          <div class="row">
            <div class="col-md-3 col-sm-6">
              <div class="card mb-3">
                <div class="card-body text-center">
                  <h3>{{ interface.flows|length }}</h3>
                  <p class="mb-0">Total Flows</p>
                </div>
              </div>
            </div>
            <div class="col-md-3 col-sm-6">
              <div class="card mb-3">
                <div class="card-body text-center">
                  <h3>{{ interface.source_flows|length }}</h3>
                  <p class="mb-0">Source Flows</p>
                </div>
              </div>
            </div>
            <div class="col-md-3 col-sm-6">
              <div class="card mb-3">
                <div class="card-body text-center">
                  <h3>{{ interface.get_subflows()|length }}</h3>
                  <p class="mb-0">Subflows</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
  {% else %}
  <div class="alert alert-info">
    <h4 class="alert-heading">No Flow Visualization Available</h4>
    <p>Flow visualization could not be generated for this MuleSoft interface.</p>
  </div>
  {% endif %}
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {
  // Initialize Mermaid
  mermaid.initialize({
    startOnLoad: true,
    theme: 'default',
    securityLevel: 'loose',
    flowchart: {
      htmlLabels: true,
      curve: 'linear'
    }
  });
  
  // Force render the Mermaid diagram after initialization
  setTimeout(function() {
    mermaid.init(undefined, document.querySelector('.mermaid'));
  }, 500);
  
  // Mermaid-related functionality
  let mermaidScale = 1.0;
  document.getElementById("zoomInMermaid").addEventListener("click", function() {
    mermaidScale *= 1.2;
    document.querySelector('.mermaid svg').style.transform = `scale(${mermaidScale})`;
  });
  
  document.getElementById("zoomOutMermaid").addEventListener("click", function() {
    mermaidScale /= 1.2;
    document.querySelector('.mermaid svg').style.transform = `scale(${mermaidScale})`;
  });
});
</script>
{% endblock %}"""
    def _get_error_handling_template(self) -> str:
        """Return the default error_handling.html template."""
        return """{% extends "base.html" %}

{% block title %}{{ interface.name }} - Error Handling{% endblock %}

{% block content %}
<div class="container">
  <div class="row mb-4">
    <div class="col">
      <h1>Error Handling</h1>
      <p class="lead">{{ interface.name }}</p>
      <p>This page documents the error handling configurations in this MuleSoft application.</p>
    </div>
  </div>
  
  {% if error_data %}
  <div class="row mb-4">
    <div class="col">
      <div class="card">
        <div class="card-header bg-light">
          <h5 class="mb-0">Error Handling Overview</h5>
        </div>
        <div class="card-body">
          <div class="row">
            <div class="col-md-4">
              <div class="card text-center">
                <div class="card-body">
                  <h2 class="card-title">{{ len(interface.flows) }}</h2>
                  <p class="card-text">Total Flows</p>
                </div>
              </div>
            </div>
            <div class="col-md-4">
              <div class="card text-center">
                <div class="card-body">
                  <h2 class="card-title">{{ sum(1 for flow in interface.flows if flow.id in error_handlers) }}</h2>
                  <p class="card-text">Flows with Error Handlers</p>
                </div>
              </div>
            </div>
            <div class="col-md-4">
              <div class="card text-center">
                <div class="card-body">
                  <h2 class="card-title">{{ len(interface.flows) - sum(1 for flow in interface.flows if flow.id in error_handlers) }}</h2>
                  <p class="card-text">Flows without Error Handlers</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
  
  <div class="mb-4">
    <div class="input-group">
      <span class="input-group-text">Filter</span>
      <input type="text" id="flowFilter" class="form-control" placeholder="Type to filter flows...">
      <button class="btn btn-outline-secondary" type="button" id="showAllBtn">All</button>
      <button class="btn btn-outline-secondary" type="button" id="showWithHandlersBtn">With Handlers</button>
      <button class="btn btn-outline-secondary" type="button" id="showWithoutHandlersBtn">Without Handlers</button>
    </div>
  </div>
  
  <div class="row" id="flowList">
"""
    for flow in interface.flows:
        has_handler = flow.id in error_handlers
        badge = '<span class="badge bg-success">Has Error Handler</span>' if has_handler else '<span class="badge bg-danger">No Error Handler</span>'
        flow_type = flow.flow_type if hasattr(flow, 'flow_type') else 'flow'
        
        html += f"""
            <div class="col-md-6 flow-item" data-has-handler="{str(has_handler).lower()}">
                <div class="card flow-card">
                    <div class="card-header">
                        <div class="d-flex justify-content-between align-items-center">
                            <h5 class="mb-0">{flow.id}</h5>
                            {badge}
                        </div>
                    </div>
                    <div class="card-body">
                        <p><strong>Type:</strong> {flow_type}</p>
"""
        if has_handler:
            handler = error_handlers[flow.id]
            html += f"""
                        <div class="error-handler-details">
                            <h6>Error Handler Details:</h6>
                            <p><strong>Type:</strong> {handler.get('type', 'Unknown')}</p>
"""
            if 'when_expressions' in handler and handler['when_expressions']:
                html += """
                            <p><strong>When Expressions:</strong></p>
                            <ul>
"""
                for expr in handler['when_expressions']:
                    html += f"""
                                <li>{expr}</li>
"""
                html += """
                            </ul>
"""
            html += """
                        </div>
"""
        html += f"""
                        <div class="mt-3">
                            <a href="flow_{flow.id}.html" class="btn btn-sm btn-primary flow-link">
                                View Flow Details
                            </a>
                        </div>
                    </div>
                </div>
            </div>
"""
    html += """
        </div>
    </div>

    <footer class="container">
        <p class="text-center text-muted">&copy; Generated with MuleSoft Documentation Generator</p>
    </footer>
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const flowFilter = document.getElementById('flowFilter');
            const flowItems = document.querySelectorAll('.flow-item');
            const showAllBtn = document.getElementById('showAllBtn');
            const showWithHandlersBtn = document.getElementById('showWithHandlersBtn');
            const showWithoutHandlersBtn = document.getElementById('showWithoutHandlersBtn');
            
            function filterFlows(filter) {{
                const searchText = flowFilter.value.toLowerCase();
                
                flowItems.forEach(item => {{
                    const flowName = item.querySelector('h5').textContent.toLowerCase();
                    const hasHandler = item.getAttribute('data-has-handler') === 'true';
                    
                    let show = flowName.includes(searchText);
                    
                    if (filter === 'with' && !hasHandler) show = false;
                    if (filter === 'without' && hasHandler) show = false;
                    
                    item.style.display = show ? '' : 'none';
                }});
            }}
            
            flowFilter.addEventListener('keyup', () => filterFlows('all'));
            
            showAllBtn.addEventListener('click', () => {{
                flowFilter.value = '';
                filterFlows('all');
            }});
            
            showWithHandlersBtn.addEventListener('click', () => {{
                flowFilter.value = '';
                filterFlows('with');
            }});
            
            showWithoutHandlersBtn.addEventListener('click', () => {{
                flowFilter.value = '';
                filterFlows('without');
            }});
        }});
    </script>
</body>
</html>"""
            return html

    def _get_metadata_template(self) -> str:
        """Return the default metadata.html template."""
        return """{% extends "base.html" %}

{% block title %}{{ interface.name }} - Application Metadata{% endblock %}

{% block content %}
<div class="container">
  <div class="row mb-4">
    <div class="col">
      <h1>Application Metadata</h1>
      <p class="lead">{{ interface.name }}</p>
      <p>This page provides metadata about this MuleSoft application extracted from various sources including the manifest file, POM file, and other configuration elements.</p>
    </div>
  </div>
  
  {% if metadata %}
  <!-- Application Information -->
  {% if metadata.app_info %}
  <div class="row mb-4">
    <div class="col">
      <div class="card">
        <div class="card-header bg-light">
          <h5 class="mb-0">Application Information</h5>
        </div>
        <div class="card-body">
          <div class="row">
            {% if metadata.app_info.name %}
            <div class="col-md-4">
              <div class="mb-3">
                <h6 class="fw-bold">Name</h6>
                <p>{{ metadata.app_info.name }}</p>
              </div>
            </div>
            {% endif %}
            
            {% if metadata.app_info.version %}
            <div class="col-md-4">
              <div class="mb-3">
                <h6 class="fw-bold">Version</h6>
                <p>{{ metadata.app_info.version }}</p>
              </div>
            </div>
            {% endif %}
            
            {% if metadata.app_info.vendor %}
            <div class="col-md-4">
              <div class="mb-3">
                <h6 class="fw-bold">Vendor</h6>
                <p>{{ metadata.app_info.vendor }}</p>
              </div>
            </div>
            {% endif %}
          </div>
          
          <div class="row">
            {% if metadata.app_info.min_mule_version %}
            <div class="col-md-4">
              <div class="mb-3">
                <h6 class="fw-bold">Min Mule Version</h6>
                <p>{{ metadata.app_info.min_mule_version }}</p>
              </div>
            </div>
            {% endif %}
            
            {% if metadata.app_info.description %}
            <div class="col-md-8">
              <div class="mb-3">
                <h6 class="fw-bold">Description</h6>
                <p>{{ metadata.app_info.description }}</p>
              </div>
            </div>
            {% endif %}
          </div>
        </div>
      </div>
    </div>
  </div>
  {% endif %}
  
  <!-- Maven Project Information -->
  {% if metadata.maven_info %}
  <div class="row mb-4">
    <div class="col">
      <div class="card">
        <div class="card-header bg-light">
          <h5 class="mb-0">Maven Information</h5>
        </div>
        <div class="card-body">
          <div class="row">
            <div class="col-md-3">
              <div class="mb-3">
                <h6 class="fw-bold">Group ID</h6>
                <p>{{ metadata.maven_info.group_id }}</p>
              </div>
            </div>
            
            <div class="col-md-3">
              <div class="mb-3">
                <h6 class="fw-bold">Artifact ID</h6>
                <p>{{ metadata.maven_info.artifact_id }}</p>
              </div>
            </div>
            
            <div class="col-md-3">
              <div class="mb-3">
                <h6 class="fw-bold">Version</h6>
                <p>{{ metadata.maven_info.version }}</p>
              </div>
            </div>
            
            <div class="col-md-3">
              <div class="mb-3">
                <h6 class="fw-bold">Packaging</h6>
                <p>{{ metadata.maven_info.packaging }}</p>
              </div>
            </div>
          </div>
          
          {% if metadata.maven_info.properties %}
          <div class="row mt-3">
            <div class="col-12">
              <h6 class="fw-bold">Properties</h6>
              <div class="table-responsive">
                <table class="table table-sm table-striped">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Value</th>
                    </tr>
                  </thead>
                  <tbody>
                    {% for name, value in metadata.maven_info.properties.items() %}
                    <tr>
                      <td>{{ name }}</td>
                      <td>{{ value }}</td>
                    </tr>
                    {% endfor %}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
          {% endif %}
        </div>
      </div>
    </div>
  </div>
  {% endif %}
  
  <!-- Build Information -->
  {% if metadata.build_info %}
  <div class="row mb-4">
    <div class="col">
      <div class="card">
        <div class="card-header bg-light">
          <h5 class="mb-0">Build Information</h5>
        </div>
        <div class="card-body">
          <div class="row">
            {% if metadata.build_info.built_by %}
            <div class="col-md-4">
              <div class="mb-3">
                <h6 class="fw-bold">Built By</h6>
                <p>{{ metadata.build_info.built_by }}</p>
              </div>
            </div>
            {% endif %}
            
            {% if metadata.build_info.build_date %}
            <div class="col-md-4">
              <div class="mb-3">
                <h6 class="fw-bold">Build Date</h6>
                <p>{{ metadata.build_info.build_date }}</p>
              </div>
            </div>
            {% endif %}
            
            {% if metadata.build_info.build_jdk %}
            <div class="col-md-4">
              <div class="mb-3">
                <h6 class="fw-bold">Build JDK</h6>
                <p>{{ metadata.build_info.build_jdk }}</p>
              </div>
            </div>
            {% endif %}
          </div>
        </div>
      </div>
    </div>
  </div>
  {% endif %}
  
  <!-- Dependencies -->
  {% if metadata.dependencies and metadata.dependencies|length > 0 %}
  <div class="row mb-4">
    <div class="col">
      <div class="card">
        <div class="card-header bg-light d-flex justify-content-between align-items-center">
          <h5 class="mb-0">Dependencies</h5>
          <div class="input-group" style="max-width: 300px;">
            <input type="text" id="dependencySearch" class="form-control form-control-sm" placeholder="Search dependencies...">
            <span class="input-group-text"><i class="bi bi-search"></i></span>
          </div>
        </div>
        <div class="card-body">
          <div class="table-responsive">
            <table class="table table-sm table-striped">
              <thead>
                <tr>
                  <th>Group ID</th>
                  <th>Artifact ID</th>
                  <th>Version</th>
                  <th>Scope</th>
                </tr>
              </thead>
              <tbody id="dependenciesTableBody">
                {% for dep in metadata.dependencies %}
                <tr class="dependency-row">
                  <td>{{ dep.group_id }}</td>
                  <td>{{ dep.artifact_id }}</td>
                  <td>{{ dep.version }}</td>
                  <td>{% if dep.scope %}<span class="badge bg-secondary">{{ dep.scope }}</span>{% endif %}</td>
                </tr>
                {% endfor %}
              </tbody>
            </table>
          </div>
          <div id="noDependencies" class="alert alert-info d-none">
            No dependencies match your search.
          </div>
        </div>
      </div>
    </div>
  </div>
  {% endif %}
  
  <!-- Mule Plugin Information -->
  {% if metadata.plugins and metadata.plugins|length > 0 %}
  <div class="row mb-4">
    <div class="col">
      <div class="card">
        <div class="card-header bg-light">
          <h5 class="mb-0">Mule Plugins</h5>
        </div>
        <div class="card-body">
          <div class="table-responsive">
            <table class="table table-sm table-striped">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Version</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                {% for plugin in metadata.plugins %}
                <tr>
                  <td>{{ plugin.name }}</td>
                  <td>{{ plugin.version }}</td>
                  <td>{{ plugin.description }}</td>
                </tr>
                {% endfor %}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
  {% endif %}
  
  <!-- Secure Properties -->
  {% if metadata.secure_properties and metadata.secure_properties|length > 0 %}
  <div class="row mb-4">
    <div class="col">
      <div class="card">
        <div class="card-header bg-light">
          <h5 class="mb-0">Secure Properties</h5>
        </div>
        <div class="card-body">
          <div class="table-responsive">
            <table class="table table-sm table-striped">
              <thead>
                <tr>
                  <th>Property Name</th>
                  <th>Value</th>
                  <th>File</th>
                </tr>
              </thead>
              <tbody>
                {% for prop in metadata.secure_properties %}
                <tr>
                  <td>{{ prop.name }}</td>
                  <td><span class="badge bg-warning">Secured</span></td>
                  <td>{{ prop.file }}</td>
                </tr>
                {% endfor %}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
  {% endif %}
  
  {% else %}
  <div class="alert alert-info">
    <h4 class="alert-heading">No Metadata Available</h4>
    <p>No metadata could be extracted for this MuleSoft application.</p>
    <hr>
    <p class="mb-0">Metadata is typically extracted from JAR manifest files, pom.xml, and other configuration files.</p>
  </div>
  {% endif %}
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {
  // Dependency search functionality
  const searchInput = document.getElementById('dependencySearch');
  const tableBody = document.getElementById('dependenciesTableBody');
  const noResults = document.getElementById('noDependencies');
  
  if (searchInput && tableBody) {
    const rows = tableBody.querySelectorAll('tr.dependency-row');
    
    searchInput.addEventListener('keyup', function() {
      const searchTerm = this.value.toLowerCase();
      let matchCount = 0;
      
      rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        if (text.includes(searchTerm)) {
          row.style.display = '';
          matchCount++;
        } else {
          row.style.display = 'none';
        }
      });
      
      if (noResults) {
        if (matchCount === 0) {
          noResults.classList.remove('d-none');
        } else {
          noResults.classList.add('d-none');
        }
      }
    });
  }
});
</script>
{% endblock %}"""
    def _generate_dataweave_html(self, interface, transformations):
        """Generate HTML for DataWeave transformations."""
        # Calculate statistics outside of f-strings to avoid backslash issues
        total_transformations = len(transformations)
        avg_lines = 0
        avg_complexity = 0
        max_complexity = 0
        
        if transformations:
            # Calculate average lines of code
            total_lines = sum(len(t.get('code', '').split('\n')) for t in transformations)
            avg_lines = total_lines / total_transformations
            
            # Calculate average complexity
            total_complexity = sum(t.get('complexity', 0) for t in transformations)
            avg_complexity = total_complexity / total_transformations
            
            # Get maximum complexity
            max_complexity = max((t.get('complexity', 0) for t in transformations), default=0)
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{interface.name} - DataWeave Transformations</title>
    
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- jQuery -->
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <!-- Bootstrap Bundle with Popper -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <!-- Highlight.js for code highlighting -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/styles/default.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/highlight.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/languages/json.min.js"></script>
    
    <style>
        body {{
            padding-top: 20px;
            padding-bottom: 40px;
        }}
        
        .transformation-card {{
            margin-bottom: 15px;
        }}
        
        .code-block {{
            background-color: #f5f5f5;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
        }}
        
        .transformation-body {{
            display: none;
        }}
        
        .transformation-header {{
            cursor: pointer;
        }}
        
        .transformation-header:hover {{
            background-color: #f8f9fa;
        }}
        
        footer {{
            margin-top: 2rem;
            padding-top: 1rem;
            border-top: 1px solid #eee;
        }}
        
        .badge {{
            margin-left: 5px;
        }}
        
        .stats-card {{
            margin-bottom: 20px;
        }}
        
        .search-container {{
            margin-bottom: 20px;
        }}
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-light bg-light mb-4">
        <div class="container">
            <a class="navbar-brand" href="index.html">
                MuleSoft Documentation
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="index.html">Home</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="configurations.html">Configurations</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link active" href="dataweave.html">DataWeave</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="flow_diagram.html">Flow Diagrams</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="error_handling.html">Error Handling</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="metadata.html">Metadata</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <h1>DataWeave Transformations</h1>
        
        <div class="card stats-card">
            <div class="card-header">
                <h5 class="mb-0">Transformation Statistics</h5>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-3">
                        <div class="card text-center">
                            <div class="card-body">
                                <h5 class="card-title">{total_transformations}</h5>
                                <p class="card-text">Total Transformations</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card text-center">
                            <div class="card-body">
                                <h5 class="card-title">{avg_lines:.1f}</h5>
                                <p class="card-text">Avg. Lines of Code</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card text-center">
                            <div class="card-body">
                                <h5 class="card-title">{avg_complexity:.1f}</h5>
                                <p class="card-text">Avg. Complexity</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card text-center">
                            <div class="card-body">
                                <h5 class="card-title">{max_complexity}</h5>
                                <p class="card-text">Max Complexity</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="search-container">
            <input type="text" id="transformationSearch" class="form-control" placeholder="Search transformations...">
        </div>
        
        <div class="accordion" id="transformationsAccordion">
"""
    for i, transform in enumerate(transformations):
        name = transform.get('name', f"Transformation {i+1}")
        flow_name = transform.get('flow_name', 'Unknown')
        processor = transform.get('processor', 'Unknown')
        complexity = transform.get('complexity', 0)
        code = transform.get('code', '')
        if code:
            code = code.replace('\\', '\\\\').replace('{', '{{').replace('}', '}}')
        
        complexity_badge = ""
        if complexity > 7:
            complexity_badge = f'<span class="badge bg-danger">High Complexity: {complexity}</span>'
        elif complexity > 4:
            complexity_badge = f'<span class="badge bg-warning text-dark">Medium Complexity: {complexity}</span>'
        else:
            complexity_badge = f'<span class="badge bg-success">Low Complexity: {complexity}</span>'
        
        html += f"""
        <div class="card transformation-card" data-name="{name}" data-flow="{flow_name}" data-processor="{processor}">
            <div class="card-header transformation-header" id="heading{i}" data-bs-toggle="collapse" data-bs-target="#collapse{i}">
                <div class="d-flex justify-content-between align-items-center">
                    <h5 class="mb-0">{name}</h5>
                    <div>
                        <span class="badge bg-primary">{flow_name}</span>
                        <span class="badge bg-secondary">{processor}</span>
                        {complexity_badge}
                    </div>
                </div>
            </div>
            <div id="collapse{i}" class="collapse" data-bs-parent="#transformationsAccordion">
                <div class="card-body">
                    <h6>Code:</h6>
                    <pre class="code-block"><code class="language-dataweave">{code}</code></pre>
                    
                    <div class="row mt-3">
                        <div class="col-md-6">
                            <h6>Flow:</h6>
                            <p><a href="flow_{flow_name}.html" class="btn btn-sm btn-outline-primary">View Flow Details</a></p>
                        </div>
                        <div class="col-md-6">
                            <h6>Processor:</h6>
                            <p>{processor}</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
"""
    html += """
        </div>
    </div>

    <footer class="container">
        <p class="text-center text-muted">&copy; Generated with MuleSoft Documentation Generator</p>
    </footer>
    
    <script>
        // Initialize syntax highlighting
        document.addEventListener('DOMContentLoaded', function() {{{{
            document.querySelectorAll('pre code').forEach((block) => {{{{
                hljs.highlightElement(block);
            }}}});
            
            // Search functionality
            const searchInput = document.getElementById('transformationSearch');
            const transformationCards = document.querySelectorAll('.transformation-card');
            
            searchInput.addEventListener('keyup', function() {{{{
                const searchText = this.value.toLowerCase();
                
                transformationCards.forEach(card => {{{{
                    const name = card.getAttribute('data-name').toLowerCase();
                    const flow = card.getAttribute('data-flow').toLowerCase();
                    const processor = card.getAttribute('data-processor').toLowerCase();
                    
                    if (name.includes(searchText) || flow.includes(searchText) || processor.includes(searchText)) {{{{
                        card.style.display = '';
                    }}}} else {{{{
                        card.style.display = 'none';
                    }}}}
                }}}});
            }}}});
            
            // Click to expand
            document.querySelectorAll('.transformation-header').forEach(header => {{{{
                header.addEventListener('click', function() {{{{
                    const collapseElem = this.nextElementSibling;
                    const isCollapsed = !collapseElem.classList.contains('show');
                    
                    if (isCollapsed) {{{{
                        collapseElem.classList.add('show');
                    }}}} else {{{{
                        collapseElem.classList.remove('show');
                    }}}}
                }}}});
            }}}});
        }}}});
    </script>
</body>
</html>"""
            return html

    def _simplify_dataweave_data(self, dw_data):
        """Simplify and sanitize DataWeave data for safe HTML generation."""
        result = {'transformations': [], 'stats': {}}
        
        # Handle stats
        if 'stats' in dw_data:
            stats = dw_data['stats']
            result['stats'] = {
                'total': stats.get('total', 0),
                'avg_complexity': float(stats.get('avg_complexity', 0)),
                'versions': [str(v) for v in stats.get('versions', [])],
                'output_types': [str(t) for t in stats.get('output_types', [])]
            }
        
        # Handle transformations
        if 'transformations' in dw_data:
            for transform in dw_data['transformations']:
                if not isinstance(transform, dict):
                    continue
                    
                clean_transform = {
                    'file_name': str(transform.get('file_name', 'Unnamed')),
                    'file_path': str(transform.get('file_path', '')),
                    'dw_version': str(transform.get('dw_version', 'Unknown')),
                    'output_mime_type': str(transform.get('output_mime_type', 'Unknown'))
                }
                
                # Handle code preview separately to avoid f-string issues with backslashes
                code_preview = str(transform.get('code_preview', ''))
                clean_transform['code_preview'] = code_preview.replace('<', '&lt;').replace('>', '&gt;')
                
                # Convert complexity to a number
                try:
                    clean_transform['complexity'] = float(transform.get('complexity', 0))
                except (ValueError, TypeError):
                    clean_transform['complexity'] = 0
                
                result['transformations'].append(clean_transform)
        
        return result

    def _generate_flow_diagram_html(self, interface, diagrams, mermaid_diagram, d3_data):
        """Generate HTML for flow diagram visualization."""
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{interface.name} - Flow Diagrams</title>
    
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- jQuery -->
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <!-- Bootstrap Bundle with Popper -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <!-- Mermaid JS -->
    <script src="https://cdn.jsdelivr.net/npm/mermaid@9.4.3/dist/mermaid.min.js"></script>
    
    <style>
        body {{
            padding-top: 20px;
            padding-bottom: 40px;
        }}
        
        footer {{
            margin-top: 2rem;
            padding-top: 1rem;
            border-top: 1px solid #eee;
        }}
        
        .diagram-container {{
            overflow: auto;
            max-width: 100%;
        }}
        
        .controls {{
            margin-bottom: 15px;
            text-align: right;
        }}
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-light bg-light mb-4">
        <div class="container">
            <a class="navbar-brand" href="index.html">
                MuleSoft Documentation
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="index.html">Home</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="configurations.html">Configurations</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="dataweave.html">DataWeave</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link active" href="flow_diagram.html">Flow Diagrams</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="error_handling.html">Error Handling</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="metadata.html">Metadata</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <h1>Flow Diagram</h1>
        
        <div class="card mb-4">
            <div class="card-header">
                <div class="d-flex justify-content-between align-items-center">
                    <h5 class="mb-0">Flow Relationships</h5>
                    <div class="controls">
                        <button class="btn btn-sm btn-outline-secondary" id="zoomIn">Zoom In</button>
                        <button class="btn btn-sm btn-outline-secondary" id="zoomOut">Zoom Out</button>
                        <button class="btn btn-sm btn-outline-primary" id="resetZoom">Reset</button>
                    </div>
                </div>
            </div>
            <div class="card-body">
                <div class="diagram-container">
                    <div class="mermaid" id="flowDiagram">
{mermaid_diagram}
                    </div>
                </div>
            </div>
        </div>
    </div>

    <footer class="container">
        <p class="text-center text-muted">&copy; Generated with MuleSoft Documentation Generator</p>
    </footer>
    
    <script>
        /* Initialize mermaid */
        mermaid.initialize({{{{{{ 
            startOnLoad: true,
            securityLevel: 'loose',
            theme: 'default'
        }}}}}});
        
        document.addEventListener('DOMContentLoaded', function() {{{{{{
            /* Wait a bit for mermaid to render */
            setTimeout(function() {{{{{{
                const diagram = document.querySelector('#flowDiagram');
                let zoom = 1;
                
                document.getElementById('zoomIn').addEventListener('click', function() {{{{{{
                    zoom *= 1.2;
                    diagram.style.transform = `scale(${{{{{{zoom}}}}}})`;
                    diagram.style.transformOrigin = 'top left';
                }}}}}});
                
                document.getElementById('zoomOut').addEventListener('click', function() {{{{{{
                    zoom *= 0.8;
                    diagram.style.transform = `scale(${{{{{{zoom}}}}}})`;
                    diagram.style.transformOrigin = 'top left';
                }}}}}});
                
                document.getElementById('resetZoom').addEventListener('click', function() {{{{{{
                    zoom = 1;
                    diagram.style.transform = `scale(1)`;
                }}}}}});
            }}}}}}, 500);
        }}}}}});
    </script>
</body>
</html>"""
            return html

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