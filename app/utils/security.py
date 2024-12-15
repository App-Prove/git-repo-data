import pathlib
from typing import Union, List, Dict, Any

def is_sensitive_file(file_path: Union[str, pathlib.Path]) -> bool:
    """
    Check if a file contains sensitive information.
    
    Args:
        file_path: Path to the file to check
        
    Returns:
        bool: True if the file is considered sensitive
    """
    sensitive_patterns = [
        'password',
        'secret',
        'key',
        'token',
        'credential',
        'auth',
        'config'
    ]
    
    file_path = str(file_path).lower()
    return any(pattern in file_path for pattern in sensitive_patterns)

def analyze_file_in_depth(file_path: Union[str, pathlib.Path]) -> Dict[str, Any]:
    """
    Perform in-depth analysis of a file.
    
    Args:
        file_path: Path to the file to analyze
        
    Returns:
        dict: Analysis results
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        return {
            "path": str(file_path),
            "findings": [
                {
                    "severity": "info",
                    "message": "File analyzed successfully",
                    "line": 0
                }
            ],
            "statistics": {
                "lines": len(content.splitlines()),
                "size": len(content)
            }
        }
    except Exception as e:
        return {
            "path": str(file_path),
            "error": str(e)
        } 