# MuleSoft Documentation Generator

A comprehensive tool for generating documentation from MuleSoft applications, providing detailed insights into interfaces, flows, and configurations.

## Features

- **XML Parsing**: Extract configurations from MuleSoft XML files
- **JAR Processing**: Analyze MuleSoft applications packaged as JAR files
- **Flow Analysis**: Identify flows, subflows, and their relationships
- **Visual Flow Diagrams**: Generate visual representations of flow relationships
- **Environment Configuration**: Compare configuration across different environments (UAT, PROD, etc.)
- **DataWeave Transformations**: Document and analyze data transformations
- **Error Handling Analysis**: Review error handling strategies throughout the application
- **Metadata Extraction**: Document application metadata, dependencies, and build information
- **HTML Documentation**: Generate comprehensive, interactive HTML documentation

## Prerequisites

- Python 3.7 or higher
- Required Python packages (automatically installed during setup):
  - lxml: XML parsing
  - jinja2: HTML template rendering
  - pathlib: File path operations
  - pyyaml: YAML configuration file parsing
  - pygments: Syntax highlighting for code examples
  - requests: HTTP requests for additional features
  - rich: Enhanced terminal output

## Installation

1. Clone this repository or download the source code
2. Install required packages:

```bash
pip install -r requirements.txt
```

## Usage

### Documenting MuleSoft XML Files

Generate documentation from a directory containing MuleSoft XML configuration files:

```bash
python src/main.py --input=path/to/xml/directory --output=path/to/output/directory --name="Interface Name"
```

### Documenting MuleSoft JAR File

Generate documentation from a packaged MuleSoft application:

```bash
python src/main.py --input=path/to/mulesoft.jar --output=path/to/output/directory --name="Interface Name"
```

## Generated Documentation

The documentation generator produces a comprehensive HTML website with the following sections:

- **Home Page**: Overview of the MuleSoft application with summary statistics
- **Flow Documentation**: Detailed information about each flow, including processors, inputs, and outputs
- **Flow Visualization**: Interactive diagrams showing flow relationships and dependencies
- **Environment Configurations**: Comparison of configuration properties across environments
- **DataWeave Transformations**: Analysis of data transformations with complexity metrics
- **Error Handling**: Documentation of error handling strategies
- **Application Metadata**: Details about the application, its dependencies, and build information

## Advanced Usage

### Additional Options

```bash
python src/main.py --help

# Options:
#   --input PATH          Path to MuleSoft XML files directory or JAR file
#   --output PATH         Path to output directory for generated documentation
#   --name TEXT           Name of the interface (e.g., "Customer Onboarding API")
#   --include-code        Include source code in the documentation
#   --detailed-analysis   Perform detailed analysis (slower but more comprehensive)
#   --help                Show this help message and exit
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Java 17 Compatibility Analyzer

The MuleSoft Documentation Generator now includes a Java 17 compatibility analyzer to help with migrating from MuleSoft 4.4 to 4.9, which requires Java 17.

### Features

- **File-based Integration Focus**: Specifically analyzes SFTP, FTP, and File connectors for Java 17 compatibility
- **Custom Java Detection**: Identifies custom Java code that might be affected by Java 17 changes
- **JDK Internal API Detection**: Finds usage of JDK internal APIs that are restricted in Java 17
- **Complexity Classification**: Classifies each interface as:
  - **Simple**: Standard MuleSoft connectors with no custom Java (little to no changes needed)
  - **Medium**: Contains custom Java or file operations that might need adjustments
  - **Hard**: Uses JDK internal APIs or deprecated features that require significant changes
- **Remediation Guidance**: Provides specific recommendations for fixing identified issues
- **HTML Reports**: Generates visual HTML reports with interactive interface details

### Usage

```bash
# Analyze a directory containing MuleSoft JAR files
python -m mulesoft-docgen.src.java17_analyzer_cli --input=/path/to/mulesoft_jars --output=report.json --html
```

### Example Output

The analyzer generates both JSON and HTML reports detailing compatibility issues. The HTML report includes:

- Summary of all analyzed interfaces with complexity distribution
- Detailed breakdown of each interface's connectors and Java usage
- Specific issues identified with impact assessment and remediation steps
- Interactive details for each interface

This tool is particularly helpful for creating accurate upgrade estimates when planning a MuleSoft 4.4 to 4.9 migration.
