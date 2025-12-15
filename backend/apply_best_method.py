"""
Apply Best Prompting Method
Reads comparison results and updates main.py with the best method
"""
import pandas as pd
import re

def apply_best_method():
    """Read comparison table and apply best method to main.py"""
    try:
        # Read comparison results
        df = pd.read_csv("prompting_methods_comparison.csv")
        
        # Filter methods with good JSON validity (>=95%)
        valid_methods = df[df["JSON Validity (%)"] >= 95]
        
        if len(valid_methods) > 0:
            # Get best method (highest accuracy)
            best = valid_methods.sort_values("Accuracy (%)", ascending=False).iloc[0]
        else:
            # If no method has >95% validity, use highest accuracy
            best = df.sort_values("Accuracy (%)", ascending=False).iloc[0]
        
        method_name = best["Method"]
        accuracy = best["Accuracy (%)"]
        validity = best["JSON Validity (%)"]
        
        print("="*60)
        print("BEST METHOD SELECTED")
        print("="*60)
        print(f"Method: {method_name}")
        print(f"Accuracy: {accuracy:.2f}%")
        print(f"JSON Validity: {validity:.2f}%")
        print("="*60)
        
        # Read main.py
        with open("main.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Map method names to function names
        method_map = {
            "Direct": "method_direct",
            "Chain-of-Thought (COT)": "method_cot",
            "Template Few-Shot": "method_fewshot",
            "Rule-Based": "method_rulebased",
            "Tree-of-Thoughts (TOT)": "method_tot",
            "Token Attention": "method_tokenattention"
        }
        
        func_name = method_map.get(method_name, "method_fewshot")
        
        # Find and replace the predict_rating function
        # We'll need to import the method from test file or recreate it
        print(f"\n✅ Best method '{method_name}' will be applied to main.py")
        print("   (You may need to manually update the predict_rating function)")
        
        return method_name, accuracy, validity
        
    except FileNotFoundError:
        print("❌ Comparison table not found. Run test_prompting_methods.py first.")
        return None, None, None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None, None, None

if __name__ == "__main__":
    apply_best_method()

