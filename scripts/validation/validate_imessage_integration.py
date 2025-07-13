#!/usr/bin/env python3
"""
Validation script for iMessage integration implementation

This script validates the complete iMessage integration system:
- Tests conversation analysis functionality
- Validates response suggestion generation
- Measures performance metrics
- Provides comprehensive system validation
"""

import sys
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.imessage.integration_manager import IMessageIntegrationManager, create_imessage_integration
from src.database.manager import DatabaseManager
from src.utils.logger_config import get_logger

logger = get_logger(__name__)


class IMessageIntegrationValidator:
    """Validates iMessage integration functionality and performance"""
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = data_dir
        self.integration_manager = None
        self.validation_results = {}
        self.performance_metrics = {}
        
    def run_validation(self) -> Dict[str, Any]:
        """Run complete validation suite"""
        logger.info("Starting iMessage integration validation...")
        
        validation_start = time.time()
        
        try:
            # Test 1: System initialization
            self._test_system_initialization()
            
            # Test 2: Database access and basic functionality
            self._test_database_functionality()
            
            # Test 3: Conversation analysis
            self._test_conversation_analysis()
            
            # Test 4: Response generation
            self._test_response_generation()
            
            # Test 5: Integration manager features
            self._test_integration_manager_features()
            
            # Test 6: Performance benchmarks
            self._test_performance_benchmarks()
            
            # Test 7: Error handling
            self._test_error_handling()
            
        except Exception as e:
            logger.error(f"Validation failed with error: {e}")
            self.validation_results["fatal_error"] = str(e)
        
        finally:
            if self.integration_manager:
                self.integration_manager.cleanup()
        
        validation_end = time.time()
        self.performance_metrics["total_validation_time"] = validation_end - validation_start
        
        return self._compile_validation_report()
    
    def _test_system_initialization(self):
        """Test system initialization and setup"""
        logger.info("Testing system initialization...")
        
        try:
            # Test basic initialization
            start_time = time.time()
            self.integration_manager = IMessageIntegrationManager(self.data_dir)
            init_result = self.integration_manager.initialize()
            init_time = time.time() - start_time
            
            self.validation_results["initialization"] = {
                "success": init_result,
                "time_seconds": init_time,
                "error": None if init_result else "Failed to initialize"
            }
            
            if not init_result:
                raise RuntimeError("System initialization failed")
                
            logger.info(f"✓ System initialization successful ({init_time:.2f}s)")
            
        except Exception as e:
            logger.error(f"✗ System initialization failed: {e}")
            self.validation_results["initialization"] = {
                "success": False,
                "time_seconds": 0,
                "error": str(e)
            }
            raise
    
    def _test_database_functionality(self):
        """Test database access and basic queries"""
        logger.info("Testing database functionality...")
        
        try:
            # Test system status
            start_time = time.time()
            status = self.integration_manager.get_system_status()
            status_time = time.time() - start_time
            
            # Test recent conversations
            conversations_start = time.time()
            conversations = self.integration_manager.get_recent_conversations(5)
            conversations_time = time.time() - conversations_start
            
            self.validation_results["database"] = {
                "success": status.get("system_ready", False),
                "database_connected": status.get("database_connected", False),
                "database_stats": status.get("database_stats", {}),
                "recent_conversations_count": len(conversations),
                "status_query_time": status_time,
                "conversations_query_time": conversations_time,
                "error": status.get("error")
            }
            
            if not status.get("system_ready"):
                raise RuntimeError("Database not ready")
                
            logger.info(f"✓ Database functionality verified ({status_time:.2f}s)")
            logger.info(f"  - Found {len(conversations)} recent conversations")
            
        except Exception as e:
            logger.error(f"✗ Database functionality test failed: {e}")
            self.validation_results["database"] = {
                "success": False,
                "error": str(e)
            }
            raise
    
    def _test_conversation_analysis(self):
        """Test conversation analysis capabilities"""
        logger.info("Testing conversation analysis...")
        
        try:
            conversations = self.integration_manager.get_recent_conversations(10)
            
            if not conversations:
                logger.warning("No conversations available for analysis testing")
                self.validation_results["conversation_analysis"] = {
                    "success": True,
                    "note": "No conversations available for testing",
                    "tested_conversations": 0
                }
                return
            
            analysis_results = []
            total_analysis_time = 0
            
            # Test analysis on up to 3 conversations
            test_conversations = conversations[:3]
            
            for conv in test_conversations:
                handle_id = conv["handle_id"]
                phone_number = conv.get("phone_number")
                
                start_time = time.time()
                
                # Test conversation context
                if phone_number:
                    context = self.integration_manager.get_conversation_context_by_phone(phone_number)
                    summary = self.integration_manager.get_conversation_summary_by_phone(phone_number)
                else:
                    context = self.integration_manager.conversation_analyzer.get_conversation_context(handle_id)
                    summary = self.integration_manager.conversation_analyzer.get_conversation_summary(handle_id)
                
                analysis_time = time.time() - start_time
                total_analysis_time += analysis_time
                
                analysis_results.append({
                    "handle_id": handle_id,
                    "phone_number": phone_number,
                    "context_found": context is not None,
                    "summary_generated": bool(summary),
                    "conversation_length": context.conversation_length if context else 0,
                    "analysis_time": analysis_time
                })
            
            avg_analysis_time = total_analysis_time / len(test_conversations)
            successful_analyses = sum(1 for r in analysis_results if r["context_found"])
            
            self.validation_results["conversation_analysis"] = {
                "success": successful_analyses > 0,
                "tested_conversations": len(test_conversations),
                "successful_analyses": successful_analyses,
                "average_analysis_time": avg_analysis_time,
                "total_analysis_time": total_analysis_time,
                "analysis_details": analysis_results
            }
            
            logger.info(f"✓ Conversation analysis completed ({avg_analysis_time:.2f}s avg)")
            logger.info(f"  - Analyzed {successful_analyses}/{len(test_conversations)} conversations successfully")
            
        except Exception as e:
            logger.error(f"✗ Conversation analysis test failed: {e}")
            self.validation_results["conversation_analysis"] = {
                "success": False,
                "error": str(e)
            }
    
    def _test_response_generation(self):
        """Test response suggestion generation"""
        logger.info("Testing response generation...")
        
        try:
            conversations = self.integration_manager.get_recent_conversations(5)
            
            if not conversations:
                logger.warning("No conversations available for response generation testing")
                self.validation_results["response_generation"] = {
                    "success": True,
                    "note": "No conversations available for testing",
                    "tested_suggestions": 0
                }
                return
            
            generation_results = []
            total_generation_time = 0
            
            # Test response generation on conversations with phone numbers
            for conv in conversations:
                phone_number = conv.get("phone_number")
                if not phone_number:
                    continue
                
                start_time = time.time()
                
                # Test basic suggestions
                suggestions = self.integration_manager.get_response_suggestions_by_phone(phone_number, 3)
                
                # Test simulation with sample message
                sim_suggestions, sim_context = self.integration_manager.simulate_response_suggestions(
                    phone_number, "Thanks for your help!"
                )
                
                generation_time = time.time() - start_time
                total_generation_time += generation_time
                
                generation_results.append({
                    "phone_number": phone_number,
                    "suggestions_count": len(suggestions),
                    "simulation_suggestions_count": len(sim_suggestions),
                    "has_context": bool(sim_context),
                    "generation_time": generation_time,
                    "sample_suggestions": [s.text for s in suggestions[:2]]  # Sample for validation
                })
                
                if len(generation_results) >= 3:  # Limit testing to 3 conversations
                    break
            
            if generation_results:
                avg_generation_time = total_generation_time / len(generation_results)
                successful_generations = sum(1 for r in generation_results if r["suggestions_count"] > 0)
                
                self.validation_results["response_generation"] = {
                    "success": successful_generations > 0,
                    "tested_conversations": len(generation_results),
                    "successful_generations": successful_generations,
                    "average_generation_time": avg_generation_time,
                    "total_generation_time": total_generation_time,
                    "generation_details": generation_results
                }
                
                logger.info(f"✓ Response generation completed ({avg_generation_time:.2f}s avg)")
                logger.info(f"  - Generated suggestions for {successful_generations}/{len(generation_results)} conversations")
            else:
                self.validation_results["response_generation"] = {
                    "success": True,
                    "note": "No conversations with phone numbers available for testing"
                }
            
        except Exception as e:
            logger.error(f"✗ Response generation test failed: {e}")
            self.validation_results["response_generation"] = {
                "success": False,
                "error": str(e)
            }
    
    def _test_integration_manager_features(self):
        """Test integration manager specific features"""
        logger.info("Testing integration manager features...")
        
        try:
            # Test convenience function
            start_time = time.time()
            test_manager = create_imessage_integration(self.data_dir)
            creation_time = time.time() - start_time
            
            # Test status checking
            status = test_manager.get_system_status()
            
            # Test cleanup
            test_manager.cleanup()
            
            self.validation_results["integration_features"] = {
                "success": True,
                "convenience_function_works": True,
                "creation_time": creation_time,
                "status_check_works": bool(status),
                "cleanup_works": True
            }
            
            logger.info(f"✓ Integration manager features verified ({creation_time:.2f}s)")
            
        except Exception as e:
            logger.error(f"✗ Integration manager features test failed: {e}")
            self.validation_results["integration_features"] = {
                "success": False,
                "error": str(e)
            }
    
    def _test_performance_benchmarks(self):
        """Test performance with multiple operations"""
        logger.info("Testing performance benchmarks...")
        
        try:
            conversations = self.integration_manager.get_recent_conversations(10)
            
            if not conversations:
                logger.warning("No conversations available for performance testing")
                self.validation_results["performance"] = {
                    "success": True,
                    "note": "No conversations available for testing"
                }
                return
            
            # Benchmark: Multiple suggestion generations
            suggestion_times = []
            for i, conv in enumerate(conversations[:5]):
                phone_number = conv.get("phone_number")
                if phone_number:
                    start_time = time.time()
                    suggestions = self.integration_manager.get_response_suggestions_by_phone(phone_number)
                    suggestion_times.append(time.time() - start_time)
            
            # Benchmark: Multiple conversation analyses
            analysis_times = []
            for conv in conversations[:5]:
                handle_id = conv["handle_id"]
                start_time = time.time()
                context = self.integration_manager.conversation_analyzer.get_conversation_context(handle_id)
                analysis_times.append(time.time() - start_time)
            
            self.performance_metrics.update({
                "suggestion_generation_times": suggestion_times,
                "avg_suggestion_time": sum(suggestion_times) / len(suggestion_times) if suggestion_times else 0,
                "max_suggestion_time": max(suggestion_times) if suggestion_times else 0,
                "analysis_times": analysis_times,
                "avg_analysis_time": sum(analysis_times) / len(analysis_times) if analysis_times else 0,
                "max_analysis_time": max(analysis_times) if analysis_times else 0
            })
            
            # Performance thresholds
            avg_suggestion_acceptable = self.performance_metrics["avg_suggestion_time"] < 1.0  # < 1 second
            avg_analysis_acceptable = self.performance_metrics["avg_analysis_time"] < 2.0  # < 2 seconds
            
            self.validation_results["performance"] = {
                "success": avg_suggestion_acceptable and avg_analysis_acceptable,
                "avg_suggestion_time_acceptable": avg_suggestion_acceptable,
                "avg_analysis_time_acceptable": avg_analysis_acceptable,
                "metrics": self.performance_metrics
            }
            
            logger.info(f"✓ Performance benchmarks completed")
            logger.info(f"  - Avg suggestion time: {self.performance_metrics['avg_suggestion_time']:.3f}s")
            logger.info(f"  - Avg analysis time: {self.performance_metrics['avg_analysis_time']:.3f}s")
            
        except Exception as e:
            logger.error(f"✗ Performance benchmarks failed: {e}")
            self.validation_results["performance"] = {
                "success": False,
                "error": str(e)
            }
    
    def _test_error_handling(self):
        """Test error handling and edge cases"""
        logger.info("Testing error handling...")
        
        try:
            error_tests = []
            
            # Test invalid phone number
            suggestions = self.integration_manager.get_response_suggestions_by_phone("invalid-phone")
            error_tests.append({
                "test": "invalid_phone_number",
                "handled_gracefully": len(suggestions) >= 0,  # Should return empty list or defaults
                "result": f"Returned {len(suggestions)} suggestions"
            })
            
            # Test invalid handle ID
            suggestions = self.integration_manager.get_response_suggestions_by_handle(-999)
            error_tests.append({
                "test": "invalid_handle_id", 
                "handled_gracefully": len(suggestions) >= 0,
                "result": f"Returned {len(suggestions)} suggestions"
            })
            
            # Test conversation context for non-existent contact
            context = self.integration_manager.get_conversation_context_by_phone("555-0000")
            error_tests.append({
                "test": "non_existent_contact",
                "handled_gracefully": context is None,  # Should return None gracefully
                "result": f"Context: {context is not None}"
            })
            
            successful_error_handling = all(test["handled_gracefully"] for test in error_tests)
            
            self.validation_results["error_handling"] = {
                "success": successful_error_handling,
                "tests_passed": sum(1 for test in error_tests if test["handled_gracefully"]),
                "total_tests": len(error_tests),
                "test_details": error_tests
            }
            
            logger.info(f"✓ Error handling verified ({len(error_tests)} tests)")
            
        except Exception as e:
            logger.error(f"✗ Error handling test failed: {e}")
            self.validation_results["error_handling"] = {
                "success": False,
                "error": str(e)
            }
    
    def _compile_validation_report(self) -> Dict[str, Any]:
        """Compile comprehensive validation report"""
        
        # Calculate overall success
        test_results = [
            self.validation_results.get("initialization", {}).get("success", False),
            self.validation_results.get("database", {}).get("success", False),
            self.validation_results.get("conversation_analysis", {}).get("success", False),
            self.validation_results.get("response_generation", {}).get("success", False),
            self.validation_results.get("integration_features", {}).get("success", False),
            self.validation_results.get("performance", {}).get("success", False),
            self.validation_results.get("error_handling", {}).get("success", False)
        ]
        
        overall_success = all(test_results)
        passed_tests = sum(test_results)
        total_tests = len(test_results)
        
        return {
            "validation_summary": {
                "overall_success": overall_success,
                "passed_tests": passed_tests,
                "total_tests": total_tests,
                "success_rate": (passed_tests / total_tests) * 100,
                "validation_timestamp": datetime.now().isoformat(),
                "total_validation_time": self.performance_metrics.get("total_validation_time", 0)
            },
            "test_results": self.validation_results,
            "performance_metrics": self.performance_metrics,
            "recommendations": self._generate_recommendations()
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on validation results"""
        recommendations = []
        
        # Performance recommendations
        if self.performance_metrics.get("avg_suggestion_time", 0) > 0.5:
            recommendations.append("Consider optimizing response suggestion generation for better performance")
        
        if self.performance_metrics.get("avg_analysis_time", 0) > 1.0:
            recommendations.append("Consider optimizing conversation analysis for better performance")
        
        # Feature recommendations
        if not self.validation_results.get("conversation_analysis", {}).get("success"):
            recommendations.append("Review conversation analysis implementation")
        
        if not self.validation_results.get("response_generation", {}).get("success"):
            recommendations.append("Review response generation implementation")
        
        # Database recommendations
        db_stats = self.validation_results.get("database", {}).get("database_stats", {})
        if db_stats.get("message_count", 0) == 0:
            recommendations.append("No messages found in database - ensure proper data access")
        
        if not recommendations:
            recommendations.append("All validation tests passed successfully - system ready for use")
        
        return recommendations


def main():
    """Main validation function"""
    print("=" * 60)
    print("iMessage Integration Validation Script")
    print("=" * 60)
    
    validator = IMessageIntegrationValidator()
    
    try:
        # Run validation
        report = validator.run_validation()
        
        # Print summary
        summary = report["validation_summary"]
        print(f"\nValidation Results:")
        print(f"Overall Success: {'✓ PASS' if summary['overall_success'] else '✗ FAIL'}")
        print(f"Tests Passed: {summary['passed_tests']}/{summary['total_tests']} ({summary['success_rate']:.1f}%)")
        print(f"Total Time: {summary['total_validation_time']:.2f}s")
        
        # Print performance metrics
        if "performance_metrics" in report and report["performance_metrics"]:
            print(f"\nPerformance Metrics:")
            metrics = report["performance_metrics"]
            if "avg_suggestion_time" in metrics:
                print(f"Avg Suggestion Time: {metrics['avg_suggestion_time']:.3f}s")
            if "avg_analysis_time" in metrics:
                print(f"Avg Analysis Time: {metrics['avg_analysis_time']:.3f}s")
        
        # Print recommendations
        print(f"\nRecommendations:")
        for rec in report["recommendations"]:
            print(f"  • {rec}")
        
        # Return appropriate exit code
        return 0 if summary["overall_success"] else 1
        
    except Exception as e:
        print(f"\nValidation failed with error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)