"""
Phase 3: 框架整合测试

测试整合组件的功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
import unittest
from datetime import datetime
from enum import Enum


# ============== 导入整合模块 ==============

from swarmfly_integration import (
    ConfigManager,
    LifecycleManager,
    UnifiedLogger,
    MetricsExporter,
    MainController,
    SwarmFlyAdapter,
    ComponentState,
    ComponentType,
    ComponentInfo
)


class TestConfigManager(unittest.TestCase):
    """配置管理器测试"""
    
    def setUp(self):
        self.config_manager = ConfigManager()
    
    def test_load_default_config(self):
        """测试加载默认配置"""
        async def run():
            config = await self.config_manager.load()
            self.assertIn("swarmfly", config)
            return True
        
        self.assertTrue(asyncio.run(run()))
    
    def test_get_config_item(self):
        """测试获取配置项"""
        async def run():
            await self.config_manager.load()
            enabled = self.config_manager.get("swarmfly.enabled")
            self.assertTrue(enabled)
            return True
        
        self.assertTrue(asyncio.run(run()))
    
    def test_get_nested_config(self):
        """测试获取嵌套配置项"""
        async def run():
            await self.config_manager.load()
            base_url = self.config_manager.get("evolve_engine.base_url")
            self.assertEqual(base_url, "http://localhost:8080/api/evolve")
            return True
        
        self.assertTrue(asyncio.run(run()))
    
    def test_get_default_value(self):
        """测试获取默认值"""
        async def run():
            await self.config_manager.load()
            value = self.config_manager.get("nonexistent.key", "default")
            self.assertEqual(value, "default")
            return True
        
        self.assertTrue(asyncio.run(run()))


class TestLifecycleManager(unittest.TestCase):
    """生命周期管理器测试"""
    
    def setUp(self):
        self.lifecycle = LifecycleManager()
    
    def test_register_component(self):
        """测试注册组件"""
        info = self.lifecycle.register_component(
            "test_component",
            ComponentType.SERVICE,
            "1.0.0"
        )
        self.assertEqual(info.name, "test_component")
        self.assertEqual(info.version, "1.0.0")
        self.assertEqual(info.state, ComponentState.INITIALIZING)
    
    def test_register_with_dependencies(self):
        """测试注册带依赖的组件"""
        info = self.lifecycle.register_component(
            "dependent_component",
            ComponentType.SERVICE,
            "1.0.0",
            dependencies=["parent_component"]
        )
        self.assertIn("parent_component", info.dependencies)
    
    def test_get_component_state(self):
        """测试获取组件状态"""
        self.lifecycle.register_component("test_comp", ComponentType.CORE)
        state = self.lifecycle.get_component_state("test_comp")
        self.assertEqual(state, ComponentState.INITIALIZING)
    
    def test_get_component_state_not_found(self):
        """测试获取不存在的组件状态"""
        state = self.lifecycle.get_component_state("nonexistent")
        self.assertIsNone(state)
    
    def test_initialize_and_shutdown(self):
        """测试初始化和关闭"""
        async def run():
            self.lifecycle.register_component("test_comp", ComponentType.CORE)
            await self.lifecycle.initialize()
            self.assertEqual(self.lifecycle.state, ComponentState.RUNNING)
            
            await self.lifecycle.shutdown()
            self.assertEqual(self.lifecycle.state, ComponentState.STOPPED)
            return True
        
        self.assertTrue(asyncio.run(run()))
    
    def test_get_uptime(self):
        """测试获取运行时间"""
        async def run():
            await self.lifecycle.initialize()
            await asyncio.sleep(0.01)
            uptime = self.lifecycle.get_uptime()
            self.assertGreater(uptime, 0)
            return True
        
        self.assertTrue(asyncio.run(run()))


class TestMetricsExporter(unittest.TestCase):
    """指标导出器测试"""
    
    def setUp(self):
        self.metrics = MetricsExporter()
    
    def test_increment_counter(self):
        """测试递增计数器"""
        self.metrics.increment("test_counter")
        self.assertEqual(self.metrics.get_counter("test_counter"), 1)
        
        self.metrics.increment("test_counter", 5)
        self.assertEqual(self.metrics.get_counter("test_counter"), 6)
    
    def test_set_gauge(self):
        """测试设置仪表值"""
        self.metrics.gauge("test_gauge", 100.5)
        self.assertEqual(self.metrics.get_metric("test_gauge"), 100.5)
    
    def test_observe_histogram(self):
        """测试观察直方图值"""
        self.metrics.observe("test_histogram", 10.0)
        self.metrics.observe("test_histogram", 20.0)
        self.metrics.observe("test_histogram", 30.0)
        
        stats = self.metrics.get_histogram_stats("test_histogram")
        self.assertEqual(stats["count"], 3)
        self.assertEqual(stats["sum"], 60.0)
        self.assertAlmostEqual(stats["mean"], 20.0)
    
    def test_histogram_percentiles(self):
        """测试直方图百分位"""
        for i in range(100):
            self.metrics.observe("percentile_test", float(i))
        
        stats = self.metrics.get_histogram_stats("percentile_test")
        self.assertIn("p50", stats)
        self.assertIn("p95", stats)
        self.assertIn("p99", stats)
    
    def test_export_prometheus_format(self):
        """测试导出Prometheus格式"""
        self.metrics.gauge("test_metric", 42.0)
        self.metrics.increment("test_counter", 10)
        
        output = self.metrics.export_prometheus()
        self.assertIn("test_metric 42.0", output)
        self.assertIn("test_counter_total 10", output)
    
    def test_reset_metrics(self):
        """测试重置指标"""
        self.metrics.gauge("test_metric", 100.0)
        self.metrics.increment("test_counter", 50)
        
        self.metrics.reset()
        
        self.assertIsNone(self.metrics.get_metric("test_metric"))
        self.assertEqual(self.metrics.get_counter("test_counter"), 0)


class TestMainController(unittest.TestCase):
    """主控制器测试"""
    
    def setUp(self):
        # 创建新实例用于测试
        MainController._instance = None
        MainController._initialized = False
        self.controller = MainController()
    
    def test_singleton_pattern(self):
        """测试单例模式"""
        controller1 = MainController()
        controller2 = MainController()
        self.assertIs(controller1, controller2)
    
    def test_start_and_stop(self):
        """测试启动和停止"""
        async def run():
            await self.controller.start()
            self.assertTrue(self.controller.is_running)
            self.assertEqual(self.controller.lifecycle_manager.state, ComponentState.RUNNING)
            
            await self.controller.stop()
            self.assertFalse(self.controller.is_running)
            return True
        
        self.assertTrue(asyncio.run(run()))
    
    def test_health_status(self):
        """测试健康状态"""
        async def run():
            await self.controller.start()
            health = self.controller.get_health_status()
            
            self.assertEqual(health["status"], "healthy")
            self.assertIn("uptime", health)
            self.assertIn("components", health)
            self.assertIn("swarmfly_core", health["components"])
            
            await self.controller.stop()
            return True
        
        self.assertTrue(asyncio.run(run()))
    
    def test_metrics_export(self):
        """测试指标导出"""
        async def run():
            await self.controller.start()
            metrics = self.controller.get_metrics()
            
            self.assertIn("system", metrics)
            self.assertIn("prometheus", metrics)
            # 检查prometheus输出中包含start_time
            self.assertIn("start_time", metrics["prometheus"])
            
            await self.controller.stop()
            return True
        
        self.assertTrue(asyncio.run(run()))


class TestSwarmFlyAdapter(unittest.TestCase):
    """SwarmFly适配器测试"""
    
    def setUp(self):
        # 重置控制器
        MainController._instance = None
        MainController._initialized = False
        self.adapter = SwarmFlyAdapter()
    
    def test_register_and_unregister(self):
        """测试注册和注销"""
        async def run():
            await self.adapter.register()
            self.assertTrue(self.adapter.controller.is_running)
            
            await self.adapter.unregister()
            self.assertFalse(self.adapter.controller.is_running)
            return True
        
        self.assertTrue(asyncio.run(run()))
    
    def test_health_check_function(self):
        """测试健康检查函数"""
        async def run():
            await self.adapter.register()
            
            health_check = self.adapter.get_health_check()
            result = await health_check()
            
            self.assertEqual(result["status"], "healthy")
            
            await self.adapter.unregister()
            return True
        
        self.assertTrue(asyncio.run(run()))


class TestComponentIntegration(unittest.TestCase):
    """组件集成测试"""
    
    def setUp(self):
        # 重置控制器
        MainController._instance = None
        MainController._initialized = False
    
    def test_full_integration_flow(self):
        """完整集成流程测试"""
        async def run():
            # 1. 创建控制器
            controller = MainController()
            
            # 2. 加载配置
            await controller.config_manager.load()
            
            # 3. 注册组件
            controller.lifecycle_manager.register_component(
                "integration_test",
                ComponentType.SERVICE,
                "1.0.0"
            )
            
            # 4. 记录指标
            controller.metrics.gauge("test_metric", 100.0)
            controller.metrics.increment("test_counter")
            
            # 5. 启动
            await controller.lifecycle_manager.initialize()
            controller._running = True  # 标记为运行中
            
            # 6. 验证状态
            health = controller.get_health_status()
            self.assertEqual(health["status"], "healthy")
            
            # 7. 关闭
            await controller.lifecycle_manager.shutdown()
            
            return True
        
        self.assertTrue(asyncio.run(run()))


if __name__ == "__main__":
    # 运行测试
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试
    suite.addTests(loader.loadTestsFromTestCase(TestConfigManager))
    suite.addTests(loader.loadTestsFromTestCase(TestLifecycleManager))
    suite.addTests(loader.loadTestsFromTestCase(TestMetricsExporter))
    suite.addTests(loader.loadTestsFromTestCase(TestMainController))
    suite.addTests(loader.loadTestsFromTestCase(TestSwarmFlyAdapter))
    suite.addTests(loader.loadTestsFromTestCase(TestComponentIntegration))
    
    # 运行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出总结
    print("\n" + "="*60)
    print("Phase 3 框架整合测试结果总结")
    print("="*60)
    print(f"测试用例: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print("="*60)
