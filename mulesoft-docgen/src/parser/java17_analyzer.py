"""
Java 17 Compatibility Analyzer for MuleSoft Applications.

This module specifically focuses on analyzing MuleSoft interfaces for Java 17 compatibility
issues, with special attention to file-based integrations (SFTP, file operations)
that might be affected by the upgrade from MuleSoft 4.4 to 4.9.
"""

import os
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
import logging

# Define namespaces used in MuleSoft configuration files
NAMESPACES = {
    "mule": "http://www.mulesoft.org/schema/mule/core",
    "doc": "http://www.mulesoft.org/schema/mule/documentation",
    "sftp": "http://www.mulesoft.org/schema/mule/sftp",
    "file": "http://www.mulesoft.org/schema/mule/file",
    "ftp": "http://www.mulesoft.org/schema/mule/ftp",
    "java": "http://www.mulesoft.org/schema/mule/java",
    "ee": "http://www.mulesoft.org/schema/mule/ee/core",
    "scripting": "http://www.mulesoft.org/schema/mule/scripting",
    "vm": "http://www.mulesoft.org/schema/mule/vm",
    "http": "http://www.mulesoft.org/schema/mule/http",
    "jms": "http://www.mulesoft.org/schema/mule/jms"
}

# Java 17 problematic APIs and internal packages that affect file operations
JAVA17_PROBLEMATIC_IMPORTS = [
    # JDK Internal APIs that were restricted in Java 17
    "sun.misc.Unsafe",
    "sun.misc.BASE64Encoder",
    "sun.misc.BASE64Decoder",
    "sun.nio.ch",
    "sun.security.provider",
    "sun.security.x509",
    "sun.security.ssl",
    "sun.reflect",
    "sun.io",
    
    # Security Manager (deprecated in Java 17)
    "java.lang.SecurityManager",
    
    # Reflection APIs that might be affected by strong encapsulation
    "java.lang.reflect.AccessibleObject.setAccessible"
]

# File operation related classes that might be affected
FILE_OPERATION_CLASSES = [
    "java.io.File",
    "java.nio.file",
    "java.nio.channels",
    "javax.crypto",
    "org.bouncycastle",  # Often used with SFTP for crypto operations
    "com.jcraft.jsch",   # Common library for SFTP operations
    "org.apache.commons.net.ftp",
    "org.apache.commons.io"
]

class Java17Analyzer:
    """Analyzes MuleSoft applications for Java 17 compatibility issues, focusing on file operations."""
    
    def __init__(self):
        """Initialize the analyzer."""
        self.logger = logging.getLogger(__name__)
        self.jdk_internal_usage = []
        self.file_connectors = []
        self.sftp_connectors = []
        self.ftp_connectors = []
        self.custom_java_components = []
        self.security_manager_usage = []
        self.custom_classes = set()
        self.problematic_imports = []
        self.file_operations = []
        
    def analyze_jar(self, jar_path: str) -> Dict[str, Any]:
        """
        Analyze a MuleSoft application JAR file for Java 17 compatibility issues.
        
        Args:
            jar_path: Path to the JAR file
            
        Returns:
            A dictionary containing analysis results
        """
        self.logger.info(f"Analyzing JAR file: {jar_path}")
        
        # Extract JAR file to a temporary directory
        extract_dir = self._extract_jar(jar_path)
        if not extract_dir:
            return {"status": "error", "message": "Failed to extract JAR file"}
        
        # Analyze XML configuration files
        mule_files = list(Path(extract_dir).glob("**/*.xml"))
        for mule_file in mule_files:
            self._analyze_mule_config(str(mule_file))
        
        # Analyze Java class files for JDK internal API usage
        class_files = list(Path(extract_dir).glob("**/*.class"))
        for class_file in class_files:
            self._scan_class_file(str(class_file))
            
        # Check for Java source files (might be included in some deployments)
        java_files = list(Path(extract_dir).glob("**/*.java"))
        for java_file in java_files:
            self._scan_java_source(str(java_file))
        
        # Check for specific libraries related to file operations
        self._check_dependencies(extract_dir)
        
        # Classify the complexity of the required changes
        complexity = self._classify_complexity()
        
        # Generate detailed report
        return {
            "status": "success",
            "complexity": complexity,
            "file_connectors": self.file_connectors,
            "sftp_connectors": self.sftp_connectors,
            "ftp_connectors": self.ftp_connectors,
            "custom_java_components": self.custom_java_components,
            "jdk_internal_usage": self.jdk_internal_usage,
            "security_manager_usage": self.security_manager_usage,
            "problematic_imports": self.problematic_imports,
            "file_operations": self.file_operations,
            "custom_classes": list(self.custom_classes),
            "potential_issues": self._identify_potential_issues()
        }
    
    def _extract_jar(self, jar_path: str) -> str:
        """
        Extract JAR file to a temporary directory.
        
        Args:
            jar_path: Path to the JAR file
            
        Returns:
            Path to the extracted directory, or None if extraction failed
        """
        try:
            # Create a temporary directory using the JAR file name
            jar_name = os.path.basename(jar_path).replace(".jar", "")
            extract_dir = f"temp_{jar_name}"
            os.makedirs(extract_dir, exist_ok=True)
            
            # Extract the JAR file
            with zipfile.ZipFile(jar_path, "r") as jar_file:
                jar_file.extractall(extract_dir)
            
            return extract_dir
        except Exception as e:
            self.logger.error(f"Failed to extract JAR file: {e}")
            return None
    
    def _analyze_mule_config(self, config_file: str) -> None:
        """
        Analyze a MuleSoft configuration file for file operation components.
        
        Args:
            config_file: Path to the MuleSoft configuration file
        """
        try:
            tree = ET.parse(config_file)
            root = tree.getroot()
            
            # Register namespaces
            for prefix, uri in NAMESPACES.items():
                ET.register_namespace(prefix, uri)
            
            # Check for File connectors
            for element in root.findall(".//*[@connector-ref]"):
                connector_ref = element.get("connector-ref", "")
                if connector_ref and "file" in connector_ref.lower():
                    self.file_connectors.append({
                        "file": config_file,
                        "connector": connector_ref,
                        "element": element.tag
                    })
            
            # Check for SFTP connectors
            for element in root.findall(".//{http://www.mulesoft.org/schema/mule/sftp}*"):
                self.sftp_connectors.append({
                    "file": config_file,
                    "element": element.tag,
                    "attributes": {k: v for k, v in element.attrib.items()}
                })
            
            # Also check for SFTP connector via connector attributes
            for element in root.findall(".//*[@connector-ref]"):
                connector_ref = element.get("connector-ref", "")
                if connector_ref and "sftp" in connector_ref.lower():
                    self.sftp_connectors.append({
                        "file": config_file,
                        "connector": connector_ref,
                        "element": element.tag
                    })
                    
            # Check for FTP connectors
            for element in root.findall(".//{http://www.mulesoft.org/schema/mule/ftp}*"):
                self.ftp_connectors.append({
                    "file": config_file,
                    "element": element.tag,
                    "attributes": {k: v for k, v in element.attrib.items()}
                })
            
            # Check for custom Java components
            for element in root.findall(".//{http://www.mulesoft.org/schema/mule/java}*"):
                class_name = element.get("class", "")
                if class_name:
                    self.custom_java_components.append({
                        "file": config_file,
                        "class": class_name,
                        "element": element.tag
                    })
                    self.custom_classes.add(class_name)
            
            # Check for Java components via class attribute
            for element in root.findall(".//*[@class]"):
                class_name = element.get("class", "")
                if class_name:
                    self.custom_java_components.append({
                        "file": config_file,
                        "class": class_name,
                        "element": element.tag
                    })
                    self.custom_classes.add(class_name)
                    
            # Check for scripting components
            for element in root.findall(".//{http://www.mulesoft.org/schema/mule/scripting}*"):
                engine = element.get("engine", "")
                if engine:
                    code_element = element.find(".//scripting:code")
                    code = code_element.text if code_element is not None else ""
                    if code and any(api in code for api in JAVA17_PROBLEMATIC_IMPORTS):
                        self.problematic_imports.append({
                            "file": config_file,
                            "element": element.tag,
                            "engine": engine,
                            "apis": [api for api in JAVA17_PROBLEMATIC_IMPORTS if api in code]
                        })
                    
                    # Check specifically for file operations in scripts
                    if code and any(file_class in code for file_class in FILE_OPERATION_CLASSES):
                        self.file_operations.append({
                            "file": config_file,
                            "element": element.tag,
                            "engine": engine,
                            "classes": [fc for fc in FILE_OPERATION_CLASSES if fc in code]
                        })
            
        except Exception as e:
            self.logger.error(f"Failed to analyze MuleSoft configuration file {config_file}: {e}")
    
    def _scan_class_file(self, class_file: str) -> None:
        """
        Scan a Java class file for JDK internal API usage.
        This is a simplified approach - a proper bytecode analyzer would be more accurate.
        
        Args:
            class_file: Path to the Java class file
        """
        try:
            with open(class_file, "rb") as f:
                content = f.read()
                
                # Convert bytes to string for simple string matching
                content_str = str(content)
                
                # Check for usage of JDK internal APIs
                for api in JAVA17_PROBLEMATIC_IMPORTS:
                    api_encoded = api.replace(".", "/")
                    if api_encoded in content_str:
                        self.jdk_internal_usage.append({
                            "file": class_file,
                            "api": api
                        })
                
                # Check for SecurityManager usage
                if "SecurityManager" in content_str:
                    self.security_manager_usage.append({
                        "file": class_file
                    })
                
                # Check for file operation classes
                for file_class in FILE_OPERATION_CLASSES:
                    file_class_encoded = file_class.replace(".", "/")
                    if file_class_encoded in content_str:
                        self.file_operations.append({
                            "file": class_file,
                            "class": file_class
                        })
                        
        except Exception as e:
            self.logger.error(f"Failed to scan class file {class_file}: {e}")
    
    def _scan_java_source(self, java_file: str) -> None:
        """
        Scan a Java source file for JDK internal API usage.
        
        Args:
            java_file: Path to the Java source file
        """
        try:
            with open(java_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                
                # Check for import statements of JDK internal APIs
                import_pattern = r"import\s+(static\s+)?([^;]+)"
                for match in re.finditer(import_pattern, content):
                    import_stmt = match.group(2).strip()
                    
                    for api in JAVA17_PROBLEMATIC_IMPORTS:
                        if api in import_stmt or (api.split(".")[0] + ".") in import_stmt:
                            self.problematic_imports.append({
                                "file": java_file,
                                "import": import_stmt,
                                "api": api
                            })
                
                # Check for SecurityManager usage
                if "SecurityManager" in content or "System.getSecurityManager()" in content:
                    self.security_manager_usage.append({
                        "file": java_file
                    })
                
                # Check for file operation classes
                for file_class in FILE_OPERATION_CLASSES:
                    if file_class in content or file_class.split(".")[-1] in content:
                        self.file_operations.append({
                            "file": java_file,
                            "class": file_class
                        })
                        
        except Exception as e:
            self.logger.error(f"Failed to scan Java source file {java_file}: {e}")
    
    def _check_dependencies(self, extract_dir: str) -> None:
        """
        Check JAR dependencies for potential Java 17 compatibility issues.
        
        Args:
            extract_dir: Path to the extracted JAR directory
        """
        pom_file = Path(extract_dir) / "META-INF" / "maven" / "pom.xml"
        if pom_file.exists():
            try:
                tree = ET.parse(str(pom_file))
                root = tree.getroot()
                
                # Extract namespace
                ns = {"": root.tag.split("}")[0].strip("{")} if "}" in root.tag else {}
                
                # Check for dependencies that might have Java 17 compatibility issues
                for dependency in root.findall(".//dependency", ns):
                    group_id = dependency.find("groupId", ns)
                    artifact_id = dependency.find("artifactId", ns)
                    
                    if group_id is not None and artifact_id is not None:
                        group_id_text = group_id.text
                        artifact_id_text = artifact_id.text
                        
                        # Known problematic dependencies
                        problematic_deps = [
                            ("com.jcraft", "jsch"),  # Older versions have Java 17 issues
                            ("commons-net", "commons-net"),  # Older versions might have issues
                            ("sun.misc", ""),  # Any direct dependency on sun.misc
                            ("com.sun", ""),  # Any direct dependency on com.sun
                        ]
                        
                        for prob_group, prob_artifact in problematic_deps:
                            if prob_group in group_id_text and (not prob_artifact or prob_artifact in artifact_id_text):
                                self.problematic_imports.append({
                                    "file": str(pom_file),
                                    "dependency": f"{group_id_text}:{artifact_id_text}",
                                    "reason": "Potential Java 17 compatibility issue"
                                })
                                
            except Exception as e:
                self.logger.error(f"Failed to parse POM file: {e}")
    
    def _classify_complexity(self) -> str:
        """
        Classify the complexity of required changes based on analysis results.
        
        Returns:
            Complexity level: "simple", "medium", or "hard"
        """
        # Hard: JDK internal API usage or SecurityManager usage
        if self.jdk_internal_usage or self.security_manager_usage or self.problematic_imports:
            return "hard"
        
        # Medium: Custom Java components or file operations using affected classes
        if self.custom_java_components or self.file_operations:
            return "medium"
        
        # Simple: Only standard MuleSoft connectors
        if self.file_connectors or self.sftp_connectors or self.ftp_connectors:
            # Even with just connectors, check if they use configurations that might be affected
            for connector in self.sftp_connectors:
                # SFTP with non-standard configurations might be affected
                attrs = connector.get("attributes", {})
                if "identityFile" in attrs or "passphrase" in attrs:
                    return "medium"
            
            return "simple"
        
        # If we couldn't detect anything, assume simple
        return "simple"
    
    def _identify_potential_issues(self) -> List[Dict[str, str]]:
        """
        Identify potential Java 17 compatibility issues and provide remediation advice.
        
        Returns:
            List of potential issues with remediation steps
        """
        issues = []
        
        # JDK Internal API usage issues
        if self.jdk_internal_usage:
            issues.append({
                "issue": "JDK Internal API Usage",
                "description": "The application uses JDK internal APIs that are restricted in Java 17",
                "impact": "High - Application will fail to run on Java 17",
                "remediation": "Replace usage of internal APIs with standard public APIs"
            })
        
        # SecurityManager usage issues
        if self.security_manager_usage:
            issues.append({
                "issue": "SecurityManager Usage",
                "description": "The application uses SecurityManager which is deprecated in Java 17",
                "impact": "Medium - Will work but with deprecation warnings, may break in future Java versions",
                "remediation": "Update security approach to use Java 17 recommended security practices"
            })
        
        # SFTP connector issues
        if self.sftp_connectors:
            issues.append({
                "issue": "SFTP Connector Configuration",
                "description": "SFTP connectors may need configuration changes for Java 17 compatibility",
                "impact": "Medium - May encounter certificate or cryptography issues",
                "remediation": "Update to latest SFTP connector versions and test thoroughly"
            })
        
        # File operation issues
        if self.file_operations:
            issues.append({
                "issue": "File Operation API Changes",
                "description": "File operations might be affected by Java NIO changes in Java 17",
                "impact": "Medium - Some file operations may behave differently",
                "remediation": "Review and test file operations thoroughly, especially around permissions and symbolic links"
            })
        
        # Problematic imports
        if self.problematic_imports:
            issues.append({
                "issue": "Problematic Library Dependencies",
                "description": "The application uses libraries with known Java 17 compatibility issues",
                "impact": "High - Application may fail at runtime",
                "remediation": "Upgrade to the latest versions of these dependencies that support Java 17"
            })
        
        return issues

def analyze_interfaces(input_path: str, output_path: str = None) -> Dict[str, Any]:
    """
    Analyze MuleSoft interfaces for Java 17 compatibility.
    
    Args:
        input_path: Path to the directory containing MuleSoft JAR files
        output_path: Path to write the detailed report (optional)
        
    Returns:
        A dictionary containing analysis results
    """
    analyzer = Java17Analyzer()
    results = {}
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("java17_analyzer")
    
    # Check if input path is a directory or a single JAR file
    if os.path.isdir(input_path):
        # Analyze all JAR files in the directory
        jar_files = list(Path(input_path).glob("**/*.jar"))
        
        if not jar_files:
            logger.warning(f"No JAR files found in {input_path}")
            return {"status": "error", "message": "No JAR files found"}
        
        # Analyze each JAR file
        for jar_file in jar_files:
            jar_name = os.path.basename(str(jar_file))
            results[jar_name] = analyzer.analyze_jar(str(jar_file))
            
    elif os.path.isfile(input_path) and input_path.endswith(".jar"):
        # Analyze a single JAR file
        jar_name = os.path.basename(input_path)
        results[jar_name] = analyzer.analyze_jar(input_path)
        
    else:
        logger.error(f"Invalid input path: {input_path}")
        return {"status": "error", "message": "Invalid input path"}
    
    # Generate summary
    summary = {
        "total_interfaces": len(results),
        "complexity_distribution": {
            "simple": sum(1 for jar, data in results.items() if data.get("complexity") == "simple"),
            "medium": sum(1 for jar, data in results.items() if data.get("complexity") == "medium"),
            "hard": sum(1 for jar, data in results.items() if data.get("complexity") == "hard")
        },
        "file_connectors_count": sum(len(data.get("file_connectors", [])) for data in results.values()),
        "sftp_connectors_count": sum(len(data.get("sftp_connectors", [])) for data in results.values()),
        "ftp_connectors_count": sum(len(data.get("ftp_connectors", [])) for data in results.values()),
        "custom_java_count": sum(len(data.get("custom_java_components", [])) for data in results.values()),
        "jdk_internal_usage_count": sum(len(data.get("jdk_internal_usage", [])) for data in results.values()),
    }
    
    # Format final results
    final_results = {
        "summary": summary,
        "interfaces": results
    }
    
    # Write detailed report to file if output path is specified
    if output_path:
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w") as f:
                import json
                json.dump(final_results, f, indent=2)
            logger.info(f"Detailed report written to {output_path}")
        except Exception as e:
            logger.error(f"Failed to write report: {e}")
    
    return final_results 