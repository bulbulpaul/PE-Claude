#!/usr/bin/env python3
"""
Master test runner for all PE-GPT integration tests

This script runs all integration test suites and generates a comprehensive report:
- Basic functionality tests
- Multi-topology integration tests
- PFC integration tests
- Main integration tests (if available)
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from typing import Dict, List, Any


class MasterTestRunner:
    """
    Master test runner that executes all integration test suites
    """
    
    def __init__(self):
        self.test_suites = []
        self.results = {}
        self.start_time = None
        self.end_time = None
        
    def discover_test_suites(self):
        """Discover all available test suites"""
        test_files = [
            ("Basic Functionality", "tests/test_basic_functionality.py"),
            ("Multi-Topology Integration", "tests/test_multi_topology_integration.py"),
            ("PFC Integration", "tests/test_pfc_integration.py"),
            ("Main Integration", "tests/test_integration.py"),
            ("PFC Development System", "core/pfc_dev/test_integration.py"),
        ]
        
        for name, path in test_files:
            if os.path.exists(path):
                self.test_suites.append((name, path))
                print(f"✅ Found: {name} ({path})")
            else:
                print(f"⏭️ Skipped: {name} (file not found)")
        
        print(f"\nTotal test suites found: {len(self.test_suites)}")
        print()
    
    def run_test_suite(self, name: str, path: str) -> Dict[str, Any]:
        """Run a single test suite"""
        print("=" * 70)
        print(f"Running: {name}")
        print("=" * 70)
        
        try:
            # Run the test script
            result = subprocess.run(
                [sys.executable, path],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            # Parse output
            output = result.stdout
            error_output = result.stderr
            return_code = result.returncode
            
            # Print output
            print(output)
            if error_output:
                print("STDERR:", error_output)
            
            # Try to load JSON results if available
            json_results = None
            result_files = [
                "tests/basic_test_results.json",
                "tests/multi_topology_integration_results.json",
                "tests/integration_test_results.json",
                "tests/main_integration_test_results.json"
            ]
            
            for result_file in result_files:
                if os.path.exists(result_file):
                    try:
                        with open(result_file, 'r') as f:
                            json_results = json.load(f)
                        break
                    except:
                        pass
            
            return {
                "name": name,
                "path": path,
                "success": return_code == 0,
                "return_code": return_code,
                "output": output,
                "error_output": error_output,
                "json_results": json_results
            }
            
        except subprocess.TimeoutExpired:
            print(f"❌ Test suite timed out after 5 minutes")
            return {
                "name": name,
                "path": path,
                "success": False,
                "return_code": -1,
                "output": "",
                "error_output": "Test timed out",
                "json_results": None
            }
        except Exception as e:
            print(f"❌ Error running test suite: {e}")
            return {
                "name": name,
                "path": path,
                "success": False,
                "return_code": -1,
                "output": "",
                "error_output": str(e),
                "json_results": None
            }
    
    def run_all_tests(self):
        """Run all discovered test suites"""
        self.start_time = datetime.now()
        
        print("🧪 Starting Master Test Runner")
        print("=" * 70)
        print(f"Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        print()
        
        # Discover test suites
        self.discover_test_suites()
        
        if not self.test_suites:
            print("❌ No test suites found!")
            return
        
        # Run each test suite
        for name, path in self.test_suites:
            result = self.run_test_suite(name, path)
            self.results[name] = result
            print()
        
        self.end_time = datetime.now()
        
        # Generate summary report
        self.generate_summary_report()
    
    def generate_summary_report(self):
        """Generate comprehensive summary report"""
        print("=" * 70)
        print("🏁 MASTER TEST SUMMARY")
        print("=" * 70)
        
        # Time information
        duration = self.end_time - self.start_time
        print(f"Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"End Time: {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total Duration: {duration.total_seconds():.2f} seconds")
        print()
        
        # Test suite results
        total_suites = len(self.results)
        passed_suites = sum(1 for r in self.results.values() if r["success"])
        failed_suites = total_suites - passed_suites
        
        print(f"Test Suites Run: {total_suites}")
        print(f"Passed: {passed_suites} ✅")
        print(f"Failed: {failed_suites} ❌")
        print(f"Success Rate: {(passed_suites/total_suites*100):.1f}%" if total_suites > 0 else "0%")
        print()
        
        # Detailed results per suite
        print("📋 Detailed Results by Suite:")
        print("-" * 70)
        
        for name, result in self.results.items():
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(f"{status}: {name}")
            
            # If JSON results available, show detailed stats
            if result["json_results"]:
                json_res = result["json_results"]
                if "total_tests" in json_res:
                    print(f"    Total Tests: {json_res['total_tests']}")
                    print(f"    Passed: {json_res.get('passed_tests', 0)}")
                    print(f"    Failed: {json_res.get('failed_tests', 0)}")
                    print(f"    Success Rate: {json_res.get('success_rate', 0):.1f}%")
                
                # Performance metrics if available
                if "performance_metrics" in json_res:
                    print(f"    Performance Metrics:")
                    for metric, value in json_res["performance_metrics"].items():
                        print(f"      {metric}: {value}")
                
                # Requirements coverage if available
                if "requirements_coverage" in json_res:
                    print(f"    Requirements Coverage:")
                    for req, passed in json_res["requirements_coverage"].items():
                        status_icon = "✅" if passed else "❌"
                        print(f"      {status_icon} {req}")
            
            print()
        
        # Overall assessment
        print("=" * 70)
        if failed_suites == 0:
            print("🎯 OVERALL ASSESSMENT: ✅ ALL TEST SUITES PASSED")
            print()
            print("🚀 The PE-GPT multi-topology system is working correctly!")
            print("💡 All integration tests passed successfully.")
        else:
            print("🎯 OVERALL ASSESSMENT: ❌ SOME TEST SUITES FAILED")
            print()
            print("⚠️ Failed test suites:")
            for name, result in self.results.items():
                if not result["success"]:
                    print(f"  - {name}")
            print()
            print("💡 Review the detailed results above to identify and fix issues.")
        print("=" * 70)
        
        # Save comprehensive report
        self.save_comprehensive_report()
    
    def save_comprehensive_report(self):
        """Save comprehensive test report to file"""
        report = {
            "test_run_info": {
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat(),
                "duration_seconds": (self.end_time - self.start_time).total_seconds()
            },
            "summary": {
                "total_suites": len(self.results),
                "passed_suites": sum(1 for r in self.results.values() if r["success"]),
                "failed_suites": sum(1 for r in self.results.values() if not r["success"]),
                "success_rate": (sum(1 for r in self.results.values() if r["success"]) / len(self.results) * 100) if self.results else 0
            },
            "test_suites": {}
        }
        
        for name, result in self.results.items():
            report["test_suites"][name] = {
                "success": result["success"],
                "return_code": result["return_code"],
                "json_results": result["json_results"]
            }
        
        report_file = "tests/comprehensive_test_report.json"
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Comprehensive report saved to: {report_file}")
        except Exception as e:
            print(f"\n⚠️ Could not save comprehensive report: {e}")


def main():
    """Main function"""
    print("🔧 PE-GPT Master Integration Test Runner")
    print("Running all integration test suites...")
    print()
    
    # Check if running in correct directory
    if not os.path.exists("main.py"):
        print("❌ Error: Please run this script from the PE-GPT root directory")
        sys.exit(1)
    
    # Run all tests
    runner = MasterTestRunner()
    runner.run_all_tests()
    
    # Exit with appropriate code
    all_passed = all(r["success"] for r in runner.results.values())
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
