"""
Module for generating visual representations of MuleSoft flows.

This module generates Mermaid.js diagrams to visualize flow relationships and dependencies
in MuleSoft applications.
"""

from typing import Dict, List, Any, Optional, Set, Tuple
import re


class FlowVisualizer:
    """Class for generating visual representations of MuleSoft flows."""
    
    def __init__(self):
        """Initialize the flow visualizer."""
        pass
        
    def generate_flow_diagram(self, interface) -> Tuple[str, Dict[str, List[str]]]:
        """
        Generate a Mermaid.js flowchart diagram for the flows in the interface.
        
        Args:
            interface: The interface object containing flows.
            
        Returns:
            Tuple containing:
                - The Mermaid.js flowchart diagram as a string
                - Dictionary of flow references (flow_id -> list of referenced flows)
        """
        if not interface or not hasattr(interface, 'flows') or not interface.flows:
            return "graph TD\nA[No flows found]", {}
        
        nodes = set()
        links = set()
        flow_references = {}
        
        # Use the most basic Mermaid syntax without complex features
        mermaid_diagram = []
        mermaid_diagram.append("graph TD")
        
        # Add nodes for each flow with simplest possible syntax
        for flow in interface.flows:
            if not hasattr(flow, 'id') or not flow.id:
                continue
                
            flow_id = self._sanitize_id(flow.id)
            
            # Skip if already processed
            if flow_id in nodes:
                continue
            
            # Determine node style based on flow type with minimal styling
            if hasattr(flow, 'is_subflow') and flow.is_subflow:
                # Subflow style - square brackets
                mermaid_diagram.append(f"{flow_id}[{self._escape_text(getattr(flow, 'name', flow.id))}]")
                mermaid_diagram.append(f"style {flow_id} fill:#e1f5fe,stroke:#0277bd")
            elif hasattr(flow, 'source') and flow.source:
                # Source flow style - rounded rectangle
                mermaid_diagram.append(f"{flow_id}({self._escape_text(getattr(flow, 'name', flow.id))})")
                mermaid_diagram.append(f"style {flow_id} fill:#e8f5e9,stroke:#2e7d32")
            else:
                # Regular flow style - rectangle
                mermaid_diagram.append(f"{flow_id}[{self._escape_text(getattr(flow, 'name', flow.id))}]")
                mermaid_diagram.append(f"style {flow_id} fill:#f9f9f9,stroke:#333")
            
            nodes.add(flow_id)
        
        # Add links for flow references
        for flow in interface.flows:
            if not hasattr(flow, 'id') or not flow.id:
                continue
                
            flow_id = self._sanitize_id(flow.id)
            references = []
            
            # Check for flow-ref processors
            if hasattr(flow, 'processors'):
                for processor in flow.processors:
                    ref_flow_name = None
                    
                    # Try different ways to get the reference name
                    if hasattr(processor, 'type') and processor.type == 'flow-ref':
                        if hasattr(processor, 'config') and hasattr(processor.config, 'name'):
                            ref_flow_name = processor.config.name
                        elif hasattr(processor, 'name'):
                            ref_flow_name = processor.name
                    
                    if ref_flow_name:
                        ref_flow_id = self._sanitize_id(ref_flow_name)
                        
                        # Only add links to known flows
                        if ref_flow_id in nodes:
                            link = f"{flow_id} --> {ref_flow_id}"
                            if link not in links:
                                mermaid_diagram.append(link)
                                links.add(link)
                                references.append(ref_flow_name)
            
            # Store references for this flow
            if references:
                flow_references[flow.id] = references
        
        return "\n".join(mermaid_diagram), flow_references
    
    def _sanitize_id(self, id_str: str) -> str:
        """
        Sanitize an ID for use in Mermaid.js diagrams.
        
        Args:
            id_str: The ID string to sanitize.
            
        Returns:
            Sanitized ID string.
        """
        if not id_str:
            return "unknown"
        
        # Convert to string first
        id_str = str(id_str)
        
        # Replace spaces, dashes and other special chars with underscore
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', id_str)
        
        # Ensure ID starts with a letter (Mermaid requirement)
        if sanitized and not sanitized[0].isalpha():
            sanitized = 'f_' + sanitized
        
        return sanitized
    
    def _escape_text(self, text: str) -> str:
        """
        Escape special characters in text for Mermaid diagrams.
        
        Args:
            text: The text to escape.
            
        Returns:
            Escaped text.
        """
        if not text:
            return "Unnamed Flow"
        
        # Convert to string
        text = str(text)
        
        # Keep the escaped text as simple as possible
        # Remove characters that could cause issues in Mermaid
        escaped = text.replace('"', '')
        escaped = escaped.replace('[', '(')
        escaped = escaped.replace(']', ')')
        escaped = escaped.replace('<', '(')
        escaped = escaped.replace('>', ')')
        escaped = escaped.replace('&', '+')
        escaped = escaped.replace('\\', '/')
        
        return escaped


def generate_flow_visualization(interface: Any) -> Tuple[str, Dict[str, List[str]]]:
    """
    Generate a visual representation of flows and their relationships.
    
    Args:
        interface: Interface object containing flows
        
    Returns:
        A tuple containing:
            - Mermaid.js flowchart diagram as a string
            - Dictionary of flow references
    """
    visualizer = FlowVisualizer()
    return visualizer.generate_flow_diagram(interface)


def generate_visualization(interface: Any, output_dir: str) -> Dict[str, str]:
    """
    Generate flow visualization files and return file paths.
    
    This is an adapter function that makes generate_flow_visualization
    compatible with how it's called in html_generator.py.
    
    Args:
        interface: Interface object containing flows
        output_dir: Directory to save visualization files
        
    Returns:
        Dictionary with paths to generated visualization files
    """
    import os
    import json
    
    # Generate the diagram and references
    diagram_content, flow_references = generate_flow_visualization(interface)
    
    # Create file paths
    mermaid_file = os.path.join('static', 'flow_diagram.mmd')
    d3_file = os.path.join('static', 'flow_data.json')
    
    # Create output directory
    static_dir = os.path.join(output_dir, 'static')
    os.makedirs(static_dir, exist_ok=True)
    
    # Write mermaid diagram to file
    with open(os.path.join(output_dir, mermaid_file), 'w') as f:
        f.write(diagram_content)
    
    # Create D3 visualization data
    flow_data = {
        "nodes": [],
        "links": []
    }
    
    # Add nodes (flows)
    node_map = {}
    for i, flow in enumerate(interface.flows):
        # Check if flow is a dict or an object
        if isinstance(flow, dict):
            flow_id = flow.get('id', 'unknown')
            is_subflow = flow.get('type') == 'sub-flow'
            source = flow.get('source')
        else:
            # Assuming it's an object with attributes
            flow_id = getattr(flow, 'id', 'unknown')
            is_subflow = getattr(flow, 'is_subflow', False)
            source = getattr(flow, 'source', None)
            
        node_type = "subflow" if is_subflow else "flow"
        if source:
            node_type = "source"
        
        node_map[flow_id] = i
        flow_data["nodes"].append({
            "id": i,
            "name": flow_id,
            "type": node_type
        })
    
    # Add links based on references
    for source_id, targets in flow_references.items():
        if source_id in node_map:
            source_idx = node_map[source_id]
            for target_id in targets:
                if target_id in node_map:
                    target_idx = node_map[target_id]
                    flow_data["links"].append({
                        "source": source_idx,
                        "target": target_idx
                    })
    
    # Write D3 data to file
    with open(os.path.join(output_dir, d3_file), 'w') as f:
        json.dump(flow_data, f)
    
    return {
        "mermaid": mermaid_file,
        "d3": d3_file
    }


if __name__ == '__main__':
    # Example code for testing
    class DummyFlow:
        def __init__(self, id, is_subflow=False, source=None, processors=None):
            self.id = id
            self.is_subflow = is_subflow
            self.source = source
            self.processors = processors or []
    
    class DummyInterface:
        def __init__(self, name, flows):
            self.name = name
            self.flows = flows
    
    # Create some example flows
    flows = [
        DummyFlow("MainFlow", source={"type": "http"}, processors=[
            {"type": "flow-ref", "name": "ProcessorFlow"},
            {"type": "logger", "message": "Log message"}
        ]),
        DummyFlow("ProcessorFlow", processors=[
            {"type": "flow-ref", "name": "SubflowA"},
            {"type": "transform", "data": "Some data"}
        ]),
        DummyFlow("SubflowA", is_subflow=True, processors=[
            {"type": "logger", "message": "In subflow"}
        ]),
        DummyFlow("ErrorFlow", processors=[])
    ]
    
    # Create interface
    interface = DummyInterface("Example Interface", flows)
    
    # Generate diagram
    diagram, references = generate_flow_visualization(interface)
    
    # Print result
    print("Mermaid Diagram:")
    print(diagram)
    print("\nFlow References:")
    for flow, refs in references.items():
        print(f"{flow} -> {', '.join(refs) if refs else 'None'}") 