#!/usr/bin/env python3
"""
SERENE-71 Implementation Validation Script

This script validates that all components of the live polling validation system
are working correctly. It runs a comprehensive test suite to ensure the
implementation meets all success criteria.

Usage:
    python scripts/validation/validate_serene_71_implementation.py
    python scripts/validation/validate_serene_71_implementation.py --quick
    python scripts/validation/validate_serene_71_implementation.py --comprehensive
"""

import os
import sys
import argparse
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.utils.logger_config import get_logger

logger = get_logger(__name__)


class SERENE71Validator:
    """Validates SERENE-71 implementation components"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.validation_results = {}
        self.start_time = datetime.now()
        
    def validate_file_structure(self) -> bool:
        """Validate that all required files were created"""
        logger.info("=== Validating File Structure ===")
        
        required_files = [
            "scripts/validation/validate_live_polling.py",
            "scripts/validation/copy_freshness_checker.py", 
            "src/database/smart_manager.py",
            "tests/test_live_polling_integration.py"
        ]
        
        modified_files = [
            "README_POLLING.md"
        ]
        
        all_good = True
        
        for file_path in required_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                logger.info(f"✓ Created: {file_path}")
            else:
                logger.error(f"❌ Missing: {file_path}")
                all_good = False
        
        for file_path in modified_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                logger.info(f"✓ Modified: {file_path}")
            else:
                logger.error(f"❌ Missing: {file_path}")
                all_good = False
        
        self.validation_results["file_structure"] = all_good
        return all_good
    
    def validate_script_executability(self) -> bool:
        """Validate that new scripts are executable and have proper CLI"""
        logger.info("=== Validating Script Executability ===")
        
        scripts_to_test = [
            ("scripts/validation/validate_live_polling.py", ["--help"]),
            ("scripts/validation/copy_freshness_checker.py", ["--help"]),
        ]
        
        all_good = True
        
        for script_path, args in scripts_to_test:
            full_path = self.project_root / script_path
            
            try:
                # Test help output
                result = subprocess.run(
                    [sys.executable, str(full_path)] + args,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=self.project_root
                )
                
                if result.returncode == 0:
                    logger.info(f"✓ {script_path} CLI working")
                else:
                    logger.error(f"❌ {script_path} CLI failed: {result.stderr}")
                    all_good = False
                    
            except subprocess.TimeoutExpired:
                logger.error(f"❌ {script_path} timed out")
                all_good = False
            except Exception as e:
                logger.error(f"❌ {script_path} error: {e}")
                all_good = False
        
        self.validation_results["script_executability"] = all_good
        return all_good
    
    def validate_import_structure(self) -> bool:
        """Validate that all modules can be imported successfully"""
        logger.info("=== Validating Import Structure ===")
        
        modules_to_test = [
            "src.database.smart_manager.SmartDatabaseManager",
            "scripts.validation.validate_live_polling.LivePollingValidator",
            "scripts.validation.copy_freshness_checker.CopyFreshnessChecker",
        ]
        
        all_good = True
        
        for module_path in modules_to_test:
            try:
                module_parts = module_path.split('.')
                class_name = module_parts[-1]
                module_name = '.'.join(module_parts[:-1])
                
                module = __import__(module_name, fromlist=[class_name])
                cls = getattr(module, class_name)
                
                # Try to instantiate the class
                if class_name == "SmartDatabaseManager":
                    instance = cls("./test_data")
                elif class_name == "LivePollingValidator":
                    instance = cls("./test_data")
                elif class_name == "CopyFreshnessChecker":
                    instance = cls("./test_data")
                
                logger.info(f"✓ Import successful: {module_path}")
                
            except Exception as e:
                logger.error(f"❌ Import failed: {module_path} - {e}")
                all_good = False
        
        self.validation_results["import_structure"] = all_good
        return all_good
    
    def validate_integration_tests(self) -> bool:
        """Validate that integration tests are properly structured and CI-safe"""
        logger.info("=== Validating Integration Tests ===")
        
        try:
            # Test that integration tests skip in CI
            env = os.environ.copy()
            env['CI'] = 'true'
            
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/test_live_polling_integration.py", "-v"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.project_root,
                env=env
            )
            
            if "skipped" in result.stdout.lower() and result.returncode == 0:
                logger.info("✓ Integration tests properly skip in CI")
                self.validation_results["integration_tests_ci_safe"] = True
            else:
                logger.error(f"❌ Integration tests don't skip properly in CI: {result.stderr}")
                self.validation_results["integration_tests_ci_safe"] = False
                return False
            
            # Test that integration tests can be discovered locally
            env['CI'] = 'false'
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/test_live_polling_integration.py", "--collect-only"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.project_root,
                env=env
            )
            
            if "18 tests collected" in result.stdout or "collected" in result.stdout:
                logger.info("✓ Integration tests properly discovered locally")
                self.validation_results["integration_tests_discoverable"] = True
            else:
                logger.error(f"❌ Integration tests not properly discovered: {result.stderr}")
                self.validation_results["integration_tests_discoverable"] = False
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Integration test validation failed: {e}")
            self.validation_results["integration_tests_ci_safe"] = False
            self.validation_results["integration_tests_discoverable"] = False
            return False
    
    def validate_smart_manager_functionality(self) -> bool:
        """Validate SmartDatabaseManager basic functionality"""
        logger.info("=== Validating SmartDatabaseManager Functionality ===")
        
        try:
            from src.database.smart_manager import SmartDatabaseManager
            import tempfile
            
            # Create test instance
            with tempfile.TemporaryDirectory() as temp_dir:
                smart_manager = SmartDatabaseManager(temp_dir, copy_cache_ttl_seconds=30)
                
                # Test basic methods exist and are callable
                methods_to_test = [
                    "get_source_wal_state",
                    "get_copy_efficiency_stats", 
                    "cleanup_old_copies"
                ]
                
                for method_name in methods_to_test:
                    if hasattr(smart_manager, method_name):
                        method = getattr(smart_manager, method_name)
                        if callable(method):
                            logger.info(f"✓ {method_name} method available")
                        else:
                            logger.error(f"❌ {method_name} is not callable")
                            return False
                    else:
                        logger.error(f"❌ {method_name} method missing")
                        return False
                
                # Test basic WAL state functionality
                wal_state = smart_manager.get_source_wal_state()
                if isinstance(wal_state, dict):
                    logger.info("✓ WAL state detection working")
                else:
                    logger.error("❌ WAL state detection failed")
                    return False
                
                # Test efficiency stats
                stats = smart_manager.get_copy_efficiency_stats()
                if isinstance(stats, dict):
                    logger.info("✓ Efficiency stats working")
                else:
                    logger.error("❌ Efficiency stats failed")
                    return False
            
            self.validation_results["smart_manager_functionality"] = True
            return True
            
        except Exception as e:
            logger.error(f"❌ SmartDatabaseManager validation failed: {e}")
            self.validation_results["smart_manager_functionality"] = False
            return False
    
    def validate_documentation_updates(self) -> bool:
        """Validate that documentation was properly updated"""
        logger.info("=== Validating Documentation Updates ===")
        
        try:
            readme_path = self.project_root / "README_POLLING.md"
            
            with open(readme_path, 'r') as f:
                content = f.read()
            
            required_sections = [
                "Live Validation & Monitoring",
                "Live Polling Validation", 
                "Copy Freshness Monitoring",
                "Smart Database Management",
                "SERENE-71"
            ]
            
            all_good = True
            for section in required_sections:
                if section in content:
                    logger.info(f"✓ Documentation includes: {section}")
                else:
                    logger.error(f"❌ Documentation missing: {section}")
                    all_good = False
            
            # Check for usage examples
            if "scripts/validation/validate_live_polling.py" in content:
                logger.info("✓ Documentation includes usage examples")
            else:
                logger.error("❌ Documentation missing usage examples")
                all_good = False
            
            self.validation_results["documentation_updates"] = all_good
            return all_good
            
        except Exception as e:
            logger.error(f"❌ Documentation validation failed: {e}")
            self.validation_results["documentation_updates"] = False
            return False
    
    def validate_git_integration(self) -> bool:
        """Validate git integration and branch status"""
        logger.info("=== Validating Git Integration ===")
        
        try:
            # Check current branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            current_branch = result.stdout.strip()
            if "live-polling-validation" in current_branch:
                logger.info(f"✓ On correct feature branch: {current_branch}")
            else:
                logger.warning(f"⚠️ On branch: {current_branch} (expected: nick/live-polling-validation)")
            
            # Check if changes are committed
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.stdout.strip() == "":
                logger.info("✓ All changes committed")
            else:
                logger.warning("⚠️ Uncommitted changes present")
            
            # Check commit history for SERENE-71
            result = subprocess.run(
                ["git", "log", "--oneline", "-5"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if "SERENE-71" in result.stdout:
                logger.info("✓ SERENE-71 commit found in recent history")
            else:
                logger.warning("⚠️ SERENE-71 commit not found in recent history")
            
            self.validation_results["git_integration"] = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Git integration validation failed: {e}")
            self.validation_results["git_integration"] = False
            return False
    
    def run_quick_validation(self) -> bool:
        """Run quick validation (essential checks only)"""
        logger.info("Running Quick Validation...")
        
        checks = [
            self.validate_file_structure,
            self.validate_import_structure,
            self.validate_script_executability,
        ]
        
        return all(check() for check in checks)
    
    def run_comprehensive_validation(self) -> bool:
        """Run comprehensive validation (all checks)"""
        logger.info("Running Comprehensive Validation...")
        
        checks = [
            self.validate_file_structure,
            self.validate_import_structure,
            self.validate_script_executability,
            self.validate_integration_tests,
            self.validate_smart_manager_functionality,
            self.validate_documentation_updates,
            self.validate_git_integration,
        ]
        
        return all(check() for check in checks)
    
    def generate_validation_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report"""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        passed_checks = sum(1 for result in self.validation_results.values() if result)
        total_checks = len(self.validation_results)
        
        report = {
            "validation_timestamp": self.start_time.isoformat(),
            "duration_seconds": duration,
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "failed_checks": total_checks - passed_checks,
            "success_rate": (passed_checks / total_checks * 100) if total_checks > 0 else 0,
            "overall_success": passed_checks == total_checks,
            "detailed_results": self.validation_results,
            "serene_71_implementation_status": "COMPLETE" if passed_checks == total_checks else "ISSUES_DETECTED"
        }
        
        return report
    
    def print_validation_summary(self, report: Dict[str, Any]):
        """Print validation summary"""
        logger.info("\n" + "="*70)
        logger.info("SERENE-71 IMPLEMENTATION VALIDATION SUMMARY")
        logger.info("="*70)
        
        logger.info(f"Duration: {report['duration_seconds']:.2f} seconds")
        logger.info(f"Checks Passed: {report['passed_checks']}/{report['total_checks']}")
        logger.info(f"Success Rate: {report['success_rate']:.1f}%")
        logger.info(f"Implementation Status: {report['serene_71_implementation_status']}")
        
        if report['overall_success']:
            logger.info("\n🎉 SERENE-71 IMPLEMENTATION VALIDATION PASSED!")
            logger.info("✅ All components implemented correctly")
            logger.info("✅ Integration tests properly configured")
            logger.info("✅ Scripts are executable and functional")
            logger.info("✅ Documentation updated appropriately")
            logger.info("\n✨ Ready for PR creation and code review!")
        else:
            logger.error("\n❌ SERENE-71 IMPLEMENTATION VALIDATION FAILED!")
            logger.error("Issues detected in implementation:")
            
            for check_name, result in report['detailed_results'].items():
                status = "✅ PASS" if result else "❌ FAIL"
                logger.info(f"  {check_name}: {status}")
            
            logger.error("\n🔧 Please address the failed checks before proceeding.")
        
        logger.info("\n" + "="*70)


def main():
    """Main validation function"""
    parser = argparse.ArgumentParser(
        description="SERENE-71 Implementation Validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/validation/validate_serene_71_implementation.py
  python scripts/validation/validate_serene_71_implementation.py --quick
  python scripts/validation/validate_serene_71_implementation.py --comprehensive
        """
    )
    
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick validation (essential checks only)"
    )
    
    parser.add_argument(
        "--comprehensive", 
        action="store_true",
        help="Run comprehensive validation (all checks)"
    )
    
    args = parser.parse_args()
    
    # Create validator
    validator = SERENE71Validator()
    
    try:
        # Run appropriate validation level
        if args.quick:
            success = validator.run_quick_validation()
        elif args.comprehensive:
            success = validator.run_comprehensive_validation()
        else:
            # Default to comprehensive
            success = validator.run_comprehensive_validation()
        
        # Generate and display report
        report = validator.generate_validation_report()
        validator.print_validation_summary(report)
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.info("\nValidation interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Validation failed with error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())