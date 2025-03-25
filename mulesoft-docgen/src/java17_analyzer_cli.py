#!/usr/bin/env python
"""
Java 17 Compatibility Analyzer CLI for MuleSoft Applications.

This script provides a command-line interface for analyzing MuleSoft applications
for Java 17 compatibility issues when upgrading from MuleSoft 4.4 to 4.9.

Usage:
    python java17_analyzer_cli.py --input=/path/to/mulesoft_apps --output=/path/to/report.json
"""

import os
import sys
import argparse
import json
from datetime import datetime
from pathlib import Path

from .parser.java17_analyzer import analyze_interfaces

def main():
    """Run the Java 17 compatibility analyzer CLI."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Analyze MuleSoft interfaces for Java 17 compatibility issues"
    )
    parser.add_argument(
        "--input", 
        required=True, 
        help="Path to directory containing MuleSoft JAR files or a single JAR file"
    )
    parser.add_argument(
        "--output", 
        default=None, 
        help="Path to write the detailed JSON report (optional)"
    )
    parser.add_argument(
        "--html", 
        action="store_true", 
        help="Generate HTML report in addition to JSON"
    )
    args = parser.parse_args()
    
    # Default JSON output path if not specified
    if not args.output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = f"java17_analysis_{timestamp}.json"
    
    # Run analysis
    print(f"Analyzing MuleSoft interfaces in '{args.input}' for Java 17 compatibility...")
    results = analyze_interfaces(args.input, args.output)
    
    # Print summary to console
    summary = results.get("summary", {})
    total = summary.get("total_interfaces", 0)
    simple = summary.get("complexity_distribution", {}).get("simple", 0)
    medium = summary.get("complexity_distribution", {}).get("medium", 0)
    hard = summary.get("complexity_distribution", {}).get("hard", 0)
    
    print("\n===== JAVA 17 COMPATIBILITY ANALYSIS SUMMARY =====")
    print(f"Total interfaces analyzed: {total}")
    print(f"Simple (No changes needed): {simple} ({simple/total*100:.1f}% if total > 0 else 0}%)")
    print(f"Medium (Some changes needed): {medium} ({medium/total*100:.1f}% if total > 0 else 0}%)")
    print(f"Hard (Significant changes needed): {hard} ({hard/total*100:.1f}% if total > 0 else 0}%)")
    print("\nFile-based connector usage:")
    print(f"  - File connectors: {summary.get('file_connectors_count', 0)}")
    print(f"  - SFTP connectors: {summary.get('sftp_connectors_count', 0)}")
    print(f"  - FTP connectors: {summary.get('ftp_connectors_count', 0)}")
    print(f"Custom Java component count: {summary.get('custom_java_count', 0)}")
    print(f"JDK internal API usage count: {summary.get('jdk_internal_usage_count', 0)}")
    print(f"\nDetailed report saved to: {args.output}")
    
    # Generate HTML report if requested
    if args.html:
        html_path = args.output.replace(".json", ".html")
        _generate_html_report(results, html_path)
        print(f"HTML report saved to: {html_path}")
    
    return 0

def _generate_html_report(results: dict, output_path: str) -> None:
    """
    Generate an HTML report from the analysis results.
    
    Args:
        results: Analysis results dictionary
        output_path: Path to write the HTML report
    """
    summary = results.get("summary", {})
    interfaces = results.get("interfaces", {})
    
    # Create a simple HTML report
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MuleSoft Java 17 Compatibility Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
        h1, h2, h3 {{ color: #444; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .summary {{ background-color: #f5f5f5; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .chart {{ height: 20px; background-color: #ddd; border-radius: 10px; overflow: hidden; margin: 10px 0; }}
        .chart-segment {{ height: 100%; float: left; }}
        .simple {{ background-color: #4CAF50; }}
        .medium {{ background-color: #FFC107; }}
        .hard {{ background-color: #F44336; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
        th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f2f2f2; }}
        tr:hover {{ background-color: #f5f5f5; }}
        .badge {{ padding: 5px 10px; border-radius: 10px; color: white; font-size: 0.8em; }}
        .badge-simple {{ background-color: #4CAF50; }}
        .badge-medium {{ background-color: #FFC107; color: black; }}
        .badge-hard {{ background-color: #F44336; }}
        .details {{ margin-top: 10px; padding: 10px; background-color: #f9f9f9; border-left: 3px solid #ccc; }}
        .toggleDetails {{ cursor: pointer; color: #0066cc; }}
        .hidden {{ display: none; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>MuleSoft Java 17 Compatibility Report</h1>
        <p>Analysis completed on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        
        <div class="summary">
            <h2>Summary</h2>
            <p>Total interfaces analyzed: <strong>{summary.get('total_interfaces', 0)}</strong></p>
            
            <div class="chart">
                <div class="chart-segment simple" style="width: {simple/total*100 if total > 0 else 0}%"></div>
                <div class="chart-segment medium" style="width: {medium/total*100 if total > 0 else 0}%"></div>
                <div class="chart-segment hard" style="width: {hard/total*100 if total > 0 else 0}%"></div>
            </div>
            
            <ul>
                <li><span class="badge badge-simple">Simple</span> No changes needed: {simple} ({simple/total*100:.1f}% if total > 0 else 0}%)</li>
                <li><span class="badge badge-medium">Medium</span> Some changes needed: {medium} ({medium/total*100:.1f}% if total > 0 else 0}%)</li>
                <li><span class="badge badge-hard">Hard</span> Significant changes needed: {hard} ({hard/total*100:.1f}% if total > 0 else 0}%)</li>
            </ul>
            
            <h3>Connector Usage</h3>
            <ul>
                <li>File connectors: {summary.get('file_connectors_count', 0)}</li>
                <li>SFTP connectors: {summary.get('sftp_connectors_count', 0)}</li>
                <li>FTP connectors: {summary.get('ftp_connectors_count', 0)}</li>
            </ul>
            
            <h3>Java Usage</h3>
            <ul>
                <li>Custom Java components: {summary.get('custom_java_count', 0)}</li>
                <li>JDK internal API usage: {summary.get('jdk_internal_usage_count', 0)}</li>
            </ul>
        </div>
        
        <h2>Interface Details</h2>
        <table>
            <tr>
                <th>Interface</th>
                <th>Complexity</th>
                <th>File Connectors</th>
                <th>SFTP Connectors</th>
                <th>Custom Java</th>
                <th>Details</th>
            </tr>
    """
    
    # Add interface details
    for jar_name, data in interfaces.items():
        complexity = data.get("complexity", "unknown")
        badge_class = f"badge-{complexity}"
        
        html_content += f"""
            <tr>
                <td>{jar_name}</td>
                <td><span class="badge {badge_class}">{complexity.capitalize()}</span></td>
                <td>{len(data.get('file_connectors', []))}</td>
                <td>{len(data.get('sftp_connectors', []))}</td>
                <td>{len(data.get('custom_java_components', []))}</td>
                <td><span class="toggleDetails" onclick="toggleDetails('{jar_name}')">Show details</span></td>
            </tr>
            <tr id="{jar_name}_details" class="hidden">
                <td colspan="6">
                    <div class="details">
        """
        
        # Add potential issues if any
        potential_issues = data.get("potential_issues", [])
        if potential_issues:
            html_content += "<h4>Potential Issues</h4><ul>"
            for issue in potential_issues:
                html_content += f"""
                    <li>
                        <strong>{issue.get('issue', '')}</strong>: {issue.get('description', '')}
                        <br/>Impact: {issue.get('impact', '')}
                        <br/>Remediation: {issue.get('remediation', '')}
                    </li>
                """
            html_content += "</ul>"
        
        # Add SFTP connectors if any
        sftp_connectors = data.get("sftp_connectors", [])
        if sftp_connectors:
            html_content += "<h4>SFTP Connectors</h4><ul>"
            for connector in sftp_connectors[:5]:  # Limit to first 5 for brevity
                html_content += f"<li>{connector.get('element', '').split('}')[-1]} in {os.path.basename(connector.get('file', ''))}</li>"
            if len(sftp_connectors) > 5:
                html_content += f"<li>... and {len(sftp_connectors) - 5} more</li>"
            html_content += "</ul>"
        
        # Add custom Java components if any
        custom_java = data.get("custom_java_components", [])
        if custom_java:
            html_content += "<h4>Custom Java Components</h4><ul>"
            for component in custom_java[:5]:  # Limit to first 5 for brevity
                html_content += f"<li>{component.get('class', '')} in {os.path.basename(component.get('file', ''))}</li>"
            if len(custom_java) > 5:
                html_content += f"<li>... and {len(custom_java) - 5} more</li>"
            html_content += "</ul>"
        
        # Close details section
        html_content += """
                    </div>
                </td>
            </tr>
        """
    
    # Close HTML
    html_content += """
        </table>
    </div>
    
    <script>
        function toggleDetails(id) {
            const details = document.getElementById(id + '_details');
            if (details.classList.contains('hidden')) {
                details.classList.remove('hidden');
            } else {
                details.classList.add('hidden');
            }
        }
    </script>
</body>
</html>
    """
    
    # Write HTML to file
    try:
        with open(output_path, "w") as f:
            f.write(html_content)
    except Exception as e:
        print(f"Error writing HTML report: {e}")

if __name__ == "__main__":
    sys.exit(main()) 