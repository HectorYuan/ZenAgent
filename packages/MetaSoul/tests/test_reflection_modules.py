"""Reflection 模块测试 (M10)"""
import pytest
from packages.MetaSoul.reflection.experience_analyzer import ExperienceAnalyzer
from packages.MetaSoul.reflection.insight_extractor import InsightExtractor
from packages.MetaSoul.reflection.pattern_recognizer import PatternRecognizer
from packages.MetaSoul.reflection.reflector import Reflector, ReflectionDepth

class TestExperienceAnalyzer:
    def test_init(self):
        analyzer = ExperienceAnalyzer()
        assert analyzer is not None

class TestInsightExtractor:
    def test_init(self):
        extractor = InsightExtractor()
        assert extractor is not None

class TestPatternRecognizer:
    def test_init(self):
        recognizer = PatternRecognizer()
        assert recognizer is not None

class TestReflector:
    def test_init(self):
        reflector = Reflector()
        assert reflector is not None

    def test_reflect_surface(self):
        reflector = Reflector()
        result = reflector.reflect(
            {"context": "test", "result": "ok"},
            depth=ReflectionDepth.SURFACE
        )
        assert isinstance(result, dict)
