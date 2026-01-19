#!/bin/bash
# Quick script to run LLM evaluation tests

set -e

echo "=========================================="
echo "LLM-as-a-Judge Evaluation Runner"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: Please run this script from the chatbot-core directory"
    exit 1
fi

# Parse command line arguments
MODE=${1:-validate}

case $MODE in
    validate)
        echo "📋 Running dataset validation only..."
        echo ""
        pytest tests/evaluation/test_llm_evaluation.py::test_golden_dataset_structure -v
        pytest tests/evaluation/test_llm_evaluation.py::test_dataset_coverage -v
        echo ""
        echo "✅ Dataset validation complete!"
        ;;
    
    full)
        echo "🚀 Running full evaluation (requires LLM API key)..."
        echo ""
        
        if [ -z "$OPENAI_API_KEY" ]; then
            echo "⚠️  Warning: OPENAI_API_KEY not set"
            echo "   Set it with: export OPENAI_API_KEY='your-key-here'"
            echo ""
            read -p "Continue anyway? (y/N) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        fi
        
        RUN_EVALUATION=true pytest tests/evaluation/test_llm_evaluation.py::test_chatbot_evaluation_metrics -v
        echo ""
        echo "✅ Full evaluation complete!"
        echo "📊 Results saved to: data/evaluation/results/latest_evaluation.json"
        ;;
    
    all)
        echo "🔍 Running all evaluation tests..."
        echo ""
        RUN_EVALUATION=true pytest tests/evaluation/ -v
        ;;
    
    *)
        echo "Usage: $0 [validate|full|all]"
        echo ""
        echo "Modes:"
        echo "  validate  - Validate dataset structure only (default, no API key needed)"
        echo "  full      - Run full LLM evaluation (requires OPENAI_API_KEY)"
        echo "  all       - Run all evaluation tests"
        echo ""
        echo "Examples:"
        echo "  $0 validate"
        echo "  $0 full"
        echo "  OPENAI_API_KEY='sk-...' $0 full"
        exit 1
        ;;
esac
