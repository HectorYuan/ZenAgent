"""
Feature Flag命名检查脚本

检测代码中的不一致命名
"""

import re
import os
from typing import List, Tuple

# 匹配驼峰命名
CAMEL_CASE_PATTERN = re.compile(r'[a-z]+[A-Z]')
# 匹配混合命名（数字+字母）
MIXED_CASE_PATTERN = re.compile(r'[a-z][A-Z]')

# 正确的SCREAMING_SNAKE_CASE模式
CORRECT_PATTERN = re.compile(r'^[A-Z][A-Z0-9_]*[A-Z0-9]$')

FEATURE_FLAG_KEYWORDS = [
    'enable', 'disable', 'feature', 'mode', 'flag',
    'swarm', 'agent', 'router', 'cache'
]


def check_feature_flag_naming(text: str, file_path: str) -> List[Tuple[str, str]]:
    """
    检查Feature Flag命名
    
    Args:
        text: 待检查文本
        file_path: 文件路径
        
    Returns:
        问题列表 [(错误类型, 描述)]
    """
    issues = []
    lines = text.split('\n')
    
    for line_num, line in enumerate(lines, 1):
        # 跳过注释
        if line.strip().startswith('#'):
            continue
        
        # 检查驼峰命名
        camel_matches = CAMEL_CASE_PATTERN.findall(line)
        for match in camel_matches:
            if any(kw in match.lower() for kw in FEATURE_FLAG_KEYWORDS):
                issues.append((
                    'CAMEL_CASE',
                    f"{file_path}:{line_num} - Found camelCase '{match}'"
                ))
        
        # 检查混合命名
        for keyword in FEATURE_FLAG_KEYWORDS:
            pattern = rf'\b{keyword}[A-Z]'
            mixed_matches = re.findall(pattern, line, re.IGNORECASE)
            for match in mixed_matches:
                issues.append((
                    'MIXED_CASE',
                    f"{file_path}:{line_num} - Found mixed case '{match}'"
                ))
    
    return issues


def scan_directory(directory: str, extensions: List[str] = ['.py', '.yaml', '.yml']) -> List[Tuple[str, str]]:
    """
    扫描目录检查Feature Flag命名
    
    Args:
        directory: 目录路径
        extensions: 检查的文件扩展名
        
    Returns:
        问题列表
    """
    all_issues = []
    
    for root, dirs, files in os.walk(directory):
        # 跳过特定目录
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'node_modules', 'venv']]
        
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                file_path = os.path.join(root, file)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    issues = check_feature_flag_naming(content, file_path)
                    all_issues.extend(issues)
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
    
    return all_issues


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Feature Flag命名检查")
    parser.add_argument("directory", nargs="?", default="./Agents/SwarmFly", help="要检查的目录")
    parser.add_argument("--extensions", nargs="+", default=['.py', '.yaml', '.yml'], help="文件扩展名")
    
    args = parser.parse_args()
    
    issues = scan_directory(args.directory, args.extensions)
    
    if issues:
        print(f"Found {len(issues)} naming issues:\n")
        for issue_type, message in issues:
            print(f"[{issue_type}] {message}")
        return 1
    else:
        print("No naming issues found.")
        return 0


if __name__ == "__main__":
    exit(main())
