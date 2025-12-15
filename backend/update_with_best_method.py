"""
Update main.py with the best prompting method
Reads comparison results and automatically updates predict_rating() function
"""
import pandas as pd
import re

def get_method_implementation(method_name):
    """Get the implementation code for each method"""
    implementations = {
        "Direct": '''def predict_rating(review_text: str) -> dict:
    """Predict rating using AI - Direct Prompting"""
    prompt = f"""You are a Yelp rating classifier. Read the review and classify it (1-5 stars). Return ONLY JSON:
{{"predicted_stars": <number>, "explanation": "<reasoning>"}}
Review: "{review_text}"
"""
    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()
        result = extract_json_strong(raw)
        if result and "predicted_stars" in result:
            return {
                "predicted_stars": int(result["predicted_stars"]),
                "explanation": result.get("explanation", "AI prediction")
            }
        return {"predicted_stars": None, "explanation": "Could not predict"}
    except Exception as e:
        print(f"Error predicting rating: {e}")
        return {"predicted_stars": None, "explanation": f"Error: {str(e)}"}''',

        "Chain-of-Thought (COT)": '''def predict_rating(review_text: str) -> dict:
    """Predict rating using AI - Chain-of-Thought"""
    prompt = f"""You are an expert Yelp rating assistant. Think step-by-step, then output ONLY JSON:
{{"predicted_stars": <number>, "explanation": "<reasoning>"}}
Review: "{review_text}"
"""
    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()
        result = extract_json_strong(raw)
        if result and "predicted_stars" in result:
            return {
                "predicted_stars": int(result["predicted_stars"]),
                "explanation": result.get("explanation", "AI prediction")
            }
        return {"predicted_stars": None, "explanation": "Could not predict"}
    except Exception as e:
        print(f"Error predicting rating: {e}")
        return {"predicted_stars": None, "explanation": f"Error: {str(e)}"}''',

        "Template Few-Shot": '''def predict_rating(review_text: str) -> dict:
    """Predict rating using AI - Template with Few-Shot Examples"""
    prompt = f"""You are an expert Yelp review rating system.

Your task:
- Follow the rating rubric below.
- Use examples to guide your classification.
- Output ONLY JSON (no markdown, no prose, no code blocks).

======================
⭐ Rating Rubric
======================

1 Star → Very negative. Complaints, bad service, rude staff, terrible food.
2 Stars → Mostly negative. Some positives but overall disappointing.
3 Stars → Mixed or neutral. Average experience, both good and bad points.
4 Stars → Mostly positive. Good experience with minor issues.
5 Stars → Very positive. Strong praise, excellent experience.

======================
📌 Examples (Few-Shot)
======================

Example 1:
Review: "Terrible service. Food was cold. Would not recommend."
Output:
{{
    "predicted_stars": 1,
    "explanation": "The review is strongly negative with multiple complaints."
}}

Example 2:
Review: "Food was okay but service was slow."
Output:
{{
    "predicted_stars": 3,
    "explanation": "Balanced review with both positive and negative comments."
}}

Example 3:
Review: "Amazing food and great service! Will visit again."
Output:
{{
    "predicted_stars": 5,
    "explanation": "Highly positive sentiment with strong praise."
}}

======================
🎯 Your Task
======================
Now classify the following review:

Review: "{review_text}"

Return ONLY the JSON:
{{
    "predicted_stars": <number>,
    "explanation": "<short reasoning>"
}}"""
    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()
        result = extract_json_strong(raw)
        if result and "predicted_stars" in result:
            return {
                "predicted_stars": int(result["predicted_stars"]),
                "explanation": result.get("explanation", "AI prediction")
            }
        return {"predicted_stars": None, "explanation": "Could not predict"}
    except Exception as e:
        print(f"Error predicting rating: {e}")
        return {"predicted_stars": None, "explanation": f"Error: {str(e)}"}''',

        "Rule-Based": '''def predict_rating(review_text: str) -> dict:
    """Predict rating using AI - Rule-Based"""
    prompt = f"""You are a strict rule-based Yelp rating engine. Start with 3 stars baseline.

Rules:
- "terrible"/"horrible"/"worst" → -2 stars
- "slow service"/"long wait" → -1 star
- "delicious"/"tasty" → +1 star
- "excellent"/"amazing" → +2 stars

Review: "{review_text}"
Return ONLY JSON: {{"predicted_stars": <integer>, "explanation": "<reasoning>"}}
"""
    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()
        result = extract_json_strong(raw)
        if result and "predicted_stars" in result:
            return {
                "predicted_stars": int(result["predicted_stars"]),
                "explanation": result.get("explanation", "AI prediction")
            }
        return {"predicted_stars": None, "explanation": "Could not predict"}
    except Exception as e:
        print(f"Error predicting rating: {e}")
        return {"predicted_stars": None, "explanation": f"Error: {str(e)}"}''',

        "Tree-of-Thoughts (TOT)": '''def predict_rating(review_text: str) -> dict:
    """Predict rating using AI - Tree-of-Thoughts"""
    prompt = f"""You are an expert Yelp review rating system using Tree-of-Thoughts reasoning.

Your task:
1. Generate 3 different reasoning paths for rating this review
2. Each path should consider different aspects (food, service, value, overall)
3. Evaluate each path and select the most reasonable final rating
4. Output ONLY JSON with the final decision

JSON Format:
{{
    "predicted_stars": <final_rating_1-5>,
    "explanation": "<why this final rating was chosen>"
}}

Review: "{review_text}"
"""
    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()
        result = extract_json_strong(raw)
        if result and "predicted_stars" in result:
            return {
                "predicted_stars": int(result["predicted_stars"]),
                "explanation": result.get("explanation", "AI prediction")
            }
        return {"predicted_stars": None, "explanation": "Could not predict"}
    except Exception as e:
        print(f"Error predicting rating: {e}")
        return {"predicted_stars": None, "explanation": f"Error: {str(e)}"}''',

        "Token Attention": '''def predict_rating(review_text: str) -> dict:
    """Predict rating using AI - Token Attention"""
    prompt = f"""Extract 3 key sentiment phrases, then rate (1-5). Return ONLY JSON:
{{"key_phrases": ["phrase1", "phrase2"], "predicted_stars": <number>, "explanation": "<reasoning>"}}
Review: "{review_text}"
"""
    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()
        result = extract_json_strong(raw)
        if result and "predicted_stars" in result:
            return {
                "predicted_stars": int(result["predicted_stars"]),
                "explanation": result.get("explanation", "AI prediction")
            }
        return {"predicted_stars": None, "explanation": "Could not predict"}
    except Exception as e:
        print(f"Error predicting rating: {e}")
        return {"predicted_stars": None, "explanation": f"Error: {str(e)}"}'''
    }
    return implementations.get(method_name, implementations["Template Few-Shot"])

def update_main_py(best_method_name):
    """Update main.py with the best method"""
    try:
        with open("main.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Find the predict_rating function
        pattern = r'def predict_rating\(review_text: str\) -> dict:.*?(?=\n\ndef |\n# |\Z)'
        new_implementation = get_method_implementation(best_method_name)
        
        # Replace the function
        new_content = re.sub(pattern, new_implementation, content, flags=re.DOTALL)
        
        # Add comment at the top of the function
        comment = f'    """Predict rating using AI - {best_method_name} (Best Method from Testing)"""'
        new_content = new_content.replace(
            f'def predict_rating(review_text: str) -> dict:\n    """Predict rating using AI',
            f'def predict_rating(review_text: str) -> dict:\n{comment}'
        )
        
        with open("main.py", "w", encoding="utf-8") as f:
            f.write(new_content)
        
        print(f"✅ Successfully updated main.py with {best_method_name} method!")
        return True
    except Exception as e:
        print(f"❌ Error updating main.py: {e}")
        return False

if __name__ == "__main__":
    try:
        df = pd.read_csv("prompting_methods_comparison.csv")
        
        # Filter methods with good JSON validity (>=95%)
        valid_methods = df[df["JSON Validity (%)"] >= 95]
        
        if len(valid_methods) > 0:
            best = valid_methods.sort_values("Accuracy (%)", ascending=False).iloc[0]
        else:
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
        
        # Update main.py
        if update_main_py(method_name):
            print("\n✅ main.py has been updated with the best method!")
            print("   Please restart your backend server to apply changes.")
        else:
            print("\n⚠️  Could not auto-update. Please manually update main.py")
            print(f"   Use the {method_name} implementation from test_prompting_methods.py")
        
    except FileNotFoundError:
        print("❌ Comparison table not found. Run test_prompting_methods.py first.")
    except Exception as e:
        print(f"❌ Error: {e}")

