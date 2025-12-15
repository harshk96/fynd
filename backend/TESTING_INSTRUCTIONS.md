# Comprehensive Prompting Methods Testing

## Overview
This script tests 5 different prompting methods with 3 different sample sizes (200, 300, 400) to find the best approach.

## Methods Being Tested

1. **Direct Prompting** - Simple, straightforward approach
2. **Chain-of-Thought (COT)** - Step-by-step reasoning
3. **Template Few-Shot** - Structured rubric with examples
4. **Rule-Based** - Explicit keyword-based rules
5. **Tree-of-Thoughts (TOT)** - Multiple reasoning paths, select best
6. **Token Attention** - Key phrase extraction

## Sample Sizes
- 200 samples
- 300 samples  
- 400 samples

**Total: 18 test runs (6 methods × 3 sample sizes)**

## How to Run

```bash
cd backend
python test_prompting_methods.py
```

**Estimated Time:** 2-3 hours (depending on API response time)

## Output Files

1. **prompting_methods_comparison.csv** - Main comparison table with all results
2. **test_results_*.csv** - Individual results for each method and sample size

## After Testing

Once testing is complete, run:

```bash
python apply_best_method.py
```

This will:
- Read the comparison table
- Identify the best method (highest accuracy with good JSON validity)
- Show which method to apply

Then manually update `main.py`'s `predict_rating()` function with the best method's implementation.

## Current Status

The test script is ready. Run it to get comprehensive results!

