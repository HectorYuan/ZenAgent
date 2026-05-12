"""
代码注释检查器

检查代码注释率，确保符合规范(<15%)
"""

import os
import re
from typing import Dict, List, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CommentStats:
    """注释统计"""
    total_lines: int
    code_lines: int
    comment_lines: int
    blank_lines: int
    comment_rate: float
    file_path: str


class CommentChecker:
    """
    代码注释检查器
    
    功能:
    - 计算代码注释率
    - 识别调试注释残留
    - 生成统计报告
    """
    
    # 调试注释模式
    DEBUG_PATTERNS = [
        r'TODO.*debug',
        r'FIXME.*debug',
        r'XXX.*debug',
        r'HACK.*debug',
        r'print\s*\(',
        r'console\.log',
        r'logger\.debug',
        r'# DEBUG',
        r'// DEBUG',
        r'/\* DEBUG',
        r'-- DEBUG',
    ]
    
    # 调试注释正则
    DEBUG_REGEX = [re.compile(p, re.IGNORECASE) for p in DEBUG_PATTERNS]
    
    # 注释模式
    SINGLE_LINE_COMMENT = re.compile(r'^\s*#|^\s*//|--\s')
    MULTI_LINE_START = re.compile(r'/\*|^\s*"""')
    MULTI_LINE_END = re.compile(r'\*/|^\s*"""')
    
    def __init__(self, max_comment_rate: float = 0.15):
        """
        初始化检查器
        
        Args:
            max_comment_rate: 最大注释率 (默认15%)
        """
        self.max_comment_rate = max_comment_rate
        self.stats: List[CommentStats] = []
        self.debug_comments: List[Tuple[str, int, str]] = []
    
    def check_file(self, file_path: str) -> CommentStats:
        """
        检查单个文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            CommentStats: 注释统计
        """
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        code_lines = 0
        comment_lines = 0
        blank_lines = 0
        in_multiline_comment = False
        
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # 空行
            if not stripped:
                blank_lines += 1
                continue
            
            # 检查是否包含调试注释
            self._check_debug_comment(file_path, line_num, stripped)
            
            # 多行注释开始/结束
            if self.MULTI_LINE_START.search(stripped) and not in_multiline_comment:
                in_multiline_comment = True
                comment_lines += 1
                
                if self.MULTI_LINE_END.search(stripped):
                    in_multiline_comment = False
                continue
            
            if in_multiline_comment:
                comment_lines += 1
                
                if self.MULTI_LINE_END.search(stripped):
                    in_multiline_comment = False
                continue
            
            # 单行注释
            if self.SINGLE_LINE_COMMENT.match(stripped):
                comment_lines += 1
                continue
            
            # 代码行
            code_lines += 1
        
        # 计算注释率
        non_blank_lines = code_lines + comment_lines
        comment_rate = comment_lines / non_blank_lines if non_blank_lines > 0 else 0
        
        stats = CommentStats(
            total_lines=total_lines,
            code_lines=code_lines,
            comment_lines=comment_lines,
            blank_lines=blank_lines,
            comment_rate=comment_rate,
            file_path=file_path
        )
        
        self.stats.append(stats)
        return stats
    
    def _check_debug_comment(self, file_path: str, line_num: int, line: str):
        """检查调试注释"""
        for pattern in self.DEBUG_REGEX:
            if pattern.search(line):
                self.debug_comments.append((file_path, line_num, line.strip()))
                break
    
    def check_directory(self, directory: str, extensions: List[str] = None) -> Dict:
        """
        检查目录下所有文件
        
        Args:
            directory: 目录路径
            extensions: 要检查的文件扩展名
            
        Returns:
            汇总统计
        """
        if extensions is None:
            extensions = ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs']
        
        self.stats = []
        self.debug_comments = []
        
        for root, dirs, files in os.walk(directory):
            # 跳过特定目录
            dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'node_modules', 'venv', '.venv']]
            
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    file_path = os.path.join(root, file)
                    try:
                        self.check_file(file_path)
                    except Exception as e:
                        print(f"Error checking {file_path}: {e}")
        
        return self._generate_summary()
    
    def _generate_summary(self) -> Dict:
        """生成汇总统计"""
        total_files = len(self.stats)
        total_lines = sum(s.total_lines for s in self.stats)
        total_code_lines = sum(s.code_lines for s in self.stats)
        total_comment_lines = sum(s.comment_lines for s in self.stats)
        
        overall_rate = total_comment_lines / (total_code_lines + total_comment_lines) if (total_code_lines + total_comment_lines) > 0 else 0
        
        # 找出注释率过高的文件
        high_comment_files = [s for s in self.stats if s.comment_rate > self.max_comment_rate]
        
        # 找出注释率过低的文件
        low_comment_files = [s for s in self.stats if s.comment_rate < 0.05]
        
        return {
            'total_files': total_files,
            'total_lines': total_lines,
            'total_code_lines': total_code_lines,
            'total_comment_lines': total_comment_lines,
            'overall_comment_rate': overall_rate,
            'max_comment_rate': self.max_comment_rate,
            'pass': overall_rate <= self.max_comment_rate,
            'high_comment_files': high_comment_files,
            'low_comment_files': low_comment_files,
            'debug_comments': self.debug_comments
        }
    
    def generate_report(self, summary: Dict = None) -> str:
        """
        生成检查报告
        
        Args:
            summary: 汇总统计 (可选)
            
        Returns:
            报告文本
        """
        if summary is None:
            summary = self._generate_summary()
        
        lines = []
        lines.append("=" * 70)
        lines.append("代码注释检查报告")
        lines.append("=" * 70)
        lines.append("")
        
        # 总体统计
        lines.append("总体统计")
        lines.append("-" * 70)
        lines.append(f"  总文件数:        {summary['total_files']}")
        lines.append(f"  总代码行数:      {summary['total_code_lines']}")
        lines.append(f"  总注释行数:      {summary['total_comment_lines']}")
        lines.append(f"  总体注释率:      {summary['overall_comment_rate']:.2%}")
        lines.append(f"  最大允许注释率:  {summary['max_comment_rate']:.2%}")
        lines.append(f"  检查结果:        {'✓ 通过' if summary['pass'] else '✗ 未通过'}")
        lines.append("")
        
        # 调试注释检查
        if summary['debug_comments']:
            lines.append("调试注释残留")
            lines.append("-" * 70)
            for file_path, line_num, content in summary['debug_comments'][:20]:
                lines.append(f"  {file_path}:{line_num}")
                lines.append(f"    {content[:60]}...")
            if len(summary['debug_comments']) > 20:
                lines.append(f"  ... 共 {len(summary['debug_comments'])} 处")
            lines.append("")
        
        # 注释率过高文件
        if summary['high_comment_files']:
            lines.append("注释率过高文件 (>15%)")
            lines.append("-" * 70)
            for stat in sorted(summary['high_comment_files'], key=lambda s: s.comment_rate, reverse=True)[:10]:
                lines.append(f"  {stat.comment_rate:.2%} - {stat.file_path}")
                lines.append(f"    代码行: {stat.code_lines}, 注释行: {stat.comment_lines}")
            lines.append("")
        
        # 注释率过低文件
        if summary['low_comment_files']:
            lines.append("注释率过低文件 (<5%)")
            lines.append("-" * 70)
            for stat in sorted(summary['low_comment_files'], key=lambda s: s.comment_rate)[:10]:
                lines.append(f"  {stat.comment_rate:.2%} - {stat.file_path}")
            lines.append("")
        
        lines.append("=" * 70)
        
        return "\n".join(lines)


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="代码注释检查器")
    parser.add_argument("directory", nargs="?", default="./Agents/SwarmFly", help="要检查的目录")
    parser.add_argument("--max-rate", type=float, default=0.15, help="最大注释率 (默认0.15)")
    parser.add_argument("--extensions", nargs="+", default=['.py'], help="文件扩展名")
    parser.add_argument("--fail", action="store_true", help="注释率超标时返回错误码")
    
    args = parser.parse_args()
    
    checker = CommentChecker(max_comment_rate=args.max_rate)
    summary = checker.check_directory(args.directory, args.extensions)
    
    print(checker.generate_report(summary))
    
    if args.fail and not summary['pass']:
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
