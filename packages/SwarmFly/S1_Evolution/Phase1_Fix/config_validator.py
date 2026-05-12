"""
配置文件验证器

检测YAML/JSON配置中的重复键和其他问题
"""

import yaml
import json
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidationIssue:
    """验证问题"""
    file_path: str
    issue_type: str
    message: str
    line_number: Optional[int] = None
    severity: str = "error"  # error, warning, info


@dataclass
class ValidationResult:
    """验证结果"""
    file_path: str
    is_valid: bool
    issues: List[ValidationIssue]
    duplicate_keys: List[Tuple[str, Any]]


class ConfigValidator:
    """
    配置文件验证器
    
    功能:
    - 检测YAML/JSON配置中的重复键
    - 验证配置格式
    - 检查配置完整性
    """
    
    def __init__(self):
        self.issues: List[ValidationIssue] = []
    
    def validate_file(self, file_path: str) -> ValidationResult:
        """
        验证配置文件
        
        Args:
            file_path: 配置文件路径
            
        Returns:
            ValidationResult: 验证结果
        """
        self.issues = []
        
        if not os.path.exists(file_path):
            issue = ValidationIssue(
                file_path=file_path,
                issue_type="FILE_NOT_FOUND",
                message=f"Configuration file not found: {file_path}",
                severity="error"
            )
            self.issues.append(issue)
            return ValidationResult(
                file_path=file_path,
                is_valid=False,
                issues=self.issues,
                duplicate_keys=[]
            )
        
        # 根据文件扩展名选择解析器
        ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if ext in ['.yaml', '.yml']:
                return self._validate_yaml(file_path)
            elif ext == '.json':
                return self._validate_json(file_path)
            else:
                issue = ValidationIssue(
                    file_path=file_path,
                    issue_type="UNSUPPORTED_FORMAT",
                    message=f"Unsupported file format: {ext}",
                    severity="warning"
                )
                self.issues.append(issue)
                return ValidationResult(
                    file_path=file_path,
                    is_valid=True,
                    issues=self.issues,
                    duplicate_keys=[]
                )
        except Exception as e:
            issue = ValidationIssue(
                file_path=file_path,
                issue_type="PARSE_ERROR",
                message=f"Failed to parse configuration: {str(e)}",
                severity="error"
            )
            self.issues.append(issue)
            return ValidationResult(
                file_path=file_path,
                is_valid=False,
                issues=self.issues,
                duplicate_keys=[]
            )
    
    def _validate_yaml(self, file_path: str) -> ValidationResult:
        """验证YAML文件"""
        duplicate_keys = []
        
        # 使用SafeLoader读取
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                content = yaml.safe_load(f)
            except yaml.YAMLError as e:
                issue = ValidationIssue(
                    file_path=file_path,
                    issue_type="YAML_SYNTAX_ERROR",
                    message=f"YAML syntax error: {str(e)}",
                    severity="error"
                )
                self.issues.append(issue)
                return ValidationResult(
                    file_path=file_path,
                    is_valid=False,
                    issues=self.issues,
                    duplicate_keys=[]
                )
        
        # 检测重复键
        duplicate_keys = self._detect_duplicate_keys_yaml(file_path)
        
        if duplicate_keys:
            for key, value in duplicate_keys:
                issue = ValidationIssue(
                    file_path=file_path,
                    issue_type="DUPLICATE_KEY",
                    message=f"Duplicate key found: '{key}' = {value}",
                    severity="error"
                )
                self.issues.append(issue)
        
        return ValidationResult(
            file_path=file_path,
            is_valid=len(self.issues) == 0,
            issues=self.issues,
            duplicate_keys=duplicate_keys
        )
    
    def _validate_json(self, file_path: str) -> ValidationResult:
        """验证JSON文件"""
        duplicate_keys = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                content = json.load(f)
            except json.JSONDecodeError as e:
                issue = ValidationIssue(
                    file_path=file_path,
                    issue_type="JSON_SYNTAX_ERROR",
                    message=f"JSON syntax error: {str(e)}",
                    severity="error"
                )
                self.issues.append(issue)
                return ValidationResult(
                    file_path=file_path,
                    is_valid=False,
                    issues=self.issues,
                    duplicate_keys=[]
                )
        
        # JSON标准不允许重复键，但某些解析器可能宽容处理
        # 重新解析文本以检测
        duplicate_keys = self._detect_duplicate_keys_json(file_path)
        
        if duplicate_keys:
            for key, value in duplicate_keys:
                issue = ValidationIssue(
                    file_path=file_path,
                    issue_type="DUPLICATE_KEY",
                    message=f"Duplicate key found: '{key}' = {value}",
                    severity="error"
                )
                self.issues.append(issue)
        
        return ValidationResult(
            file_path=file_path,
            is_valid=len(self.issues) == 0,
            issues=self.issues,
            duplicate_keys=duplicate_keys
        )
    
    def _detect_duplicate_keys_yaml(self, file_path: str) -> List[Tuple[str, Any]]:
        """
        检测YAML文件中的重复键
        
        使用文本解析方式检测重复键
        """
        duplicate_keys = []
        seen_keys = {}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        current_path = []
        
        for line_num, line in enumerate(lines, 1):
            # 跳过注释和空行
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            
            # 计算缩进
            indent = len(line) - len(line.lstrip())
            
            # 调整当前路径深度
            expected_indent = len(current_path) * 2
            while indent < expected_indent and current_path:
                current_path.pop()
                expected_indent -= 2
            
            # 解析键值对
            if ':' in line:
                key_part = line.split(':')[0].strip()
                
                if key_part:
                    # 构建完整路径
                    full_key = '/'.join(current_path + [key_part]) if current_path else key_part
                    
                    if full_key in seen_keys:
                        duplicate_keys.append((full_key, seen_keys[full_key]))
                    else:
                        seen_keys[full_key] = line_num
        
        return duplicate_keys
    
    def _detect_duplicate_keys_json(self, file_path: str) -> List[Tuple[str, Any]]:
        """
        检测JSON文件中的重复键
        
        JSON标准不允许重复键，但以防万一
        """
        duplicate_keys = []
        seen_keys = {}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        import re
        
        # 简单的键提取（可能有嵌套）
        key_pattern = r'"([^"]+)"\s*:'
        
        for match in re.finditer(key_pattern, content):
            key = match.group(1)
            pos = match.start()
            
            if key in seen_keys:
                duplicate_keys.append((key, seen_keys[key]))
            else:
                seen_keys[key] = pos
        
        return duplicate_keys
    
    def validate_directory(self, directory: str, recursive: bool = True) -> List[ValidationResult]:
        """
        验证目录下的所有配置文件
        
        Args:
            directory: 目录路径
            recursive: 是否递归子目录
            
        Returns:
            验证结果列表
        """
        results = []
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith(('.yaml', '.yml', '.json')):
                    file_path = os.path.join(root, file)
                    result = self.validate_file(file_path)
                    results.append(result)
            
            if not recursive:
                break
        
        return results
    
    def generate_report(self, results: List[ValidationResult]) -> str:
        """
        生成验证报告
        
        Args:
            results: 验证结果列表
            
        Returns:
            报告文本
        """
        total_files = len(results)
        valid_files = sum(1 for r in results if r.is_valid)
        invalid_files = total_files - valid_files
        total_duplicates = sum(len(r.duplicate_keys) for r in results)
        
        report = []
        report.append("=" * 60)
        report.append("配置文件验证报告")
        report.append("=" * 60)
        report.append(f"总文件数: {total_files}")
        report.append(f"有效文件: {valid_files}")
        report.append(f"无效文件: {invalid_files}")
        report.append(f"重复键总数: {total_duplicates}")
        report.append("-" * 60)
        
        for result in results:
            if not result.is_valid or result.duplicate_keys:
                report.append(f"\n文件: {result.file_path}")
                report.append(f"状态: {'✓ 有效' if result.is_valid else '✗ 无效'}")
                
                for issue in result.issues:
                    report.append(f"  [{issue.severity.upper()}] {issue.message}")
        
        report.append("=" * 60)
        
        return "\n".join(report)


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="配置文件验证器")
    parser.add_argument("path", help="配置文件或目录路径")
    parser.add_argument("-r", "--recursive", action="store_true", help="递归处理子目录")
    parser.add_argument("--fix", action="store_true", help="自动修复重复键")
    
    args = parser.parse_args()
    
    validator = ConfigValidator()
    
    if os.path.isdir(args.path):
        results = validator.validate_directory(args.path, recursive=args.recursive)
    else:
        results = [validator.validate_file(args.path)]
    
    # 打印报告
    print(validator.generate_report(results))
    
    # 如果有无效文件，返回错误码
    if any(not r.is_valid for r in results):
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
