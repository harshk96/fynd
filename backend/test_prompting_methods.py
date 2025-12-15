"""
Comprehensive Prompting Methods Testing Script
Tests multiple prompting approaches with different sample sizes
"""
import os
import pandas as pd
import numpy as np
from tqdm import tqdm
import google.generativeai as genai
import json
import re
from datetime import datetime

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyDqvLXJvnPFBAeo-sab2wC_ReBzzwwsYHQ")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("models/gemma-3-12b-it")

# Load dataset
DATA_PATH = "Data/yelp.csv"
df = pd.read_csv(DATA_PATH)
df = df[['text', 'stars']].dropna().reset_index(drop=True)

print(f"Loaded dataset: {len(df)} reviews")
print(f"Rating distribution:\n{df['stars'].value_counts().sort_index()}")

# JSON Extractor
def extract_json_strong(text):
    """Extract JSON from AI output"""
    text = re.sub(r"```.*?```", lambda m: m.group(0).replace("```", ""), text, flags=re.DOTALL)
    text = text.replace("```json", "").replace("```", "").strip()
    match = re.search(r"\{[\s\S]*?\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            return None
    return None

# ============================================
# METHOD 1: Direct Prompting
# ============================================
def method_direct(review_text):
    """Direct prompting - simple and straightforward"""
    prompt = f"""You are a Yelp rating classifier.

Read the review below and classify it into a star rating (1 to 5).

Return ONLY valid JSON. Do NOT return markdown.

JSON format:
{{
    "predicted_stars": <number>,
    "explanation": "<short reasoning>"
}}

Review: "{review_text}"
"""
    try:
        response = model.generate_content(prompt)
        result = extract_json_strong(response.text.strip())
        if result and "predicted_stars" in result:
            return int(result["predicted_stars"])
        return None
    except Exception as e:
        return None

# ============================================
# METHOD 2: Chain-of-Thought (COT)
# ============================================
def method_cot(review_text):
    """Chain-of-Thought reasoning"""
    prompt = f"""You are an expert Yelp review rating assistant.

Your task:
1. Understand the sentiment and tone of the review.
2. Think step-by-step about what emotions the review expresses.
3. Determine the most appropriate star rating from 1 to 5.
4. Finally, output ONLY JSON in the required format.

VERY IMPORTANT:
- Do NOT include chain-of-thought or reasoning outside the JSON.
- Do NOT use markdown or code blocks.
- Only output the final JSON.

JSON format:
{{
    "predicted_stars": <number>,
    "explanation": "<1-sentence reasoning>"
}}

Review: "{review_text}"
"""
    try:
        response = model.generate_content(prompt)
        result = extract_json_strong(response.text.strip())
        if result and "predicted_stars" in result:
            return int(result["predicted_stars"])
        return None
    except Exception as e:
        return None

# ============================================
# METHOD 3: Template with Few-Shot
# ============================================
def method_fewshot(review_text):
    """Template-based with few-shot examples"""
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
        result = extract_json_strong(response.text.strip())
        if result and "predicted_stars" in result:
            return int(result["predicted_stars"])
        return None
    except Exception as e:
        return None

# ============================================
# METHOD 4: Rule-Based
# ============================================
def method_rulebased(review_text):
    """Rule-based rating with explicit keyword rules"""
    prompt = f"""You are a strict rule-based Yelp rating engine.

Start with a baseline rating of 3 stars.

Apply rules IN THIS ORDER:

NEGATIVE RULES:
- If review contains any of: "terrible", "horrible", "worst", "disgusting" → subtract 2 stars.
- If review contains: "slow service", "long wait", "waited too long" → subtract 1 star.
- If review contains: "cold food", "burnt", "tasteless" → subtract 1 star.

POSITIVE RULES:
- If review contains: "delicious", "tasty", "flavorful" → add 1 star.
- If review contains: "excellent", "amazing", "outstanding" → add 2 stars.
- If review contains: "friendly staff", "great service" → add 1 star.

FINAL STEP:
- The rating must stay between 1 and 5.
- Output ONLY JSON with the final rating and explanation.

JSON Format:
{{
    "predicted_stars": <integer>,
    "explanation": "<why these rules applied>"
}}

Review:
"{review_text}"
"""
    try:
        response = model.generate_content(prompt)
        result = extract_json_strong(response.text.strip())
        if result and "predicted_stars" in result:
            return int(result["predicted_stars"])
        return None
    except Exception as e:
        return None

# ============================================
# METHOD 5: Tree-of-Thoughts (TOT)
# ============================================
def method_tot(review_text):
    """Tree-of-Thoughts - Generate multiple reasoning paths then select best"""
    prompt = f"""You are an expert Yelp review rating system using Tree-of-Thoughts reasoning.

Your task:
1. Generate 3 different reasoning paths for rating this review
2. Each path should consider different aspects (food, service, value, overall)
3. Evaluate each path and select the most reasonable final rating
4. Output ONLY JSON with the final decision

Path 1 - Focus on Food Quality:
Path 2 - Focus on Service & Experience:
Path 3 - Focus on Overall Value & Satisfaction:

After evaluating all paths, determine the final rating (1-5).

JSON Format:
{{
    "path1_rating": <1-5>,
    "path2_rating": <1-5>,
    "path3_rating": <1-5>,
    "predicted_stars": <final_rating_1-5>,
    "explanation": "<why this final rating was chosen>"
}}

Review: "{review_text}"
"""
    try:
        response = model.generate_content(prompt)
        result = extract_json_strong(response.text.strip())
        if result and "predicted_stars" in result:
            return int(result["predicted_stars"])
        return None
    except Exception as e:
        return None

# ============================================
# METHOD 6: Token Attention
# ============================================
def method_tokenattention(review_text):
    """Token attention - extract key phrases for rating"""
    prompt = f"""You are an expert sentiment analyst.

Steps:
1. Extract up to 3 key phrases from the review that strongly express sentiment.
   (Ignore filler or neutral text.)
2. Based ONLY on these key phrases, decide the star rating (1–5).
3. Output ONLY valid JSON (no markdown, no explanations outside JSON).

JSON Format:
{{
    "key_phrases": ["phrase 1", "phrase 2", "phrase 3"],
    "predicted_stars": <number>,
    "explanation": "<short reasoning>"
}}

Review:
"{review_text}"
"""
    try:
        response = model.generate_content(prompt)
        result = extract_json_strong(response.text.strip())
        if result and "predicted_stars" in result:
            return int(result["predicted_stars"])
        return None
    except Exception as e:
        return None

# ============================================
# TESTING FUNCTION
# ============================================
def test_method(method_func, method_name, sample_df):
    """Test a prompting method on a sample dataset"""
    results = []
    valid_predictions = 0
    
    for idx, row in tqdm(sample_df.iterrows(), total=len(sample_df), desc=f"Testing {method_name}"):
        review_text = row['text']
        actual = int(row['stars'])
        
        predicted = method_func(review_text)
        
        results.append({
            "review_text": review_text,
            "actual_stars": actual,
            "predicted_stars": predicted,
            "correct": 1 if predicted == actual else 0
        })
        
        if predicted is not None:
            valid_predictions += 1
    
    # Calculate metrics
    df_results = pd.DataFrame(results)
    valid_df = df_results.dropna(subset=["predicted_stars"])
    
    accuracy = (valid_df["actual_stars"] == valid_df["predicted_stars"]).mean() if len(valid_df) > 0 else 0
    json_validity = valid_predictions / len(sample_df) if len(sample_df) > 0 else 0
    
    return {
        "method": method_name,
        "sample_size": len(sample_df),
        "total_predictions": len(df_results),
        "valid_predictions": valid_predictions,
        "accuracy": accuracy * 100,
        "json_validity_rate": json_validity * 100,
        "results_df": df_results
    }

# ============================================
# MAIN TESTING
# ============================================
if __name__ == "__main__":
    methods = {
        "Direct": method_direct,
        "Chain-of-Thought (COT)": method_cot,
        "Template Few-Shot": method_fewshot,
        "Rule-Based": method_rulebased,
        "Tree-of-Thoughts (TOT)": method_tot,
        "Token Attention": method_tokenattention
    }
    
    sample_sizes = [200]
    all_results = []
    
    print("\n" + "="*60)
    print("COMPREHENSIVE PROMPTING METHODS TESTING")
    print("="*60 + "\n")
    
    for sample_size in sample_sizes:
        print(f"\n{'='*60}")
        print(f"Testing with {sample_size} samples")
        print(f"{'='*60}\n")
        
        # Sample data
        sample_df = df.sample(sample_size, random_state=42).reset_index(drop=True)
        
        for method_name, method_func in methods.items():
            print(f"\n--- Testing {method_name} ---")
            result = test_method(method_func, method_name, sample_df)
            
            # Save individual results
            result["results_df"].to_csv(
                f"test_results_{method_name.replace(' ', '_').replace('(', '').replace(')', '')}_{sample_size}.csv",
                index=False
            )
            
            all_results.append(result)
            
            print(f"✓ {method_name}:")
            print(f"  Accuracy: {result['accuracy']:.2f}%")
            print(f"  JSON Validity: {result['json_validity_rate']:.2f}%")
    
    # Create comparison table
    comparison_data = []
    for result in all_results:
        comparison_data.append({
            "Method": result["method"],
            "Sample Size": result["sample_size"],
            "Accuracy (%)": round(result["accuracy"], 2),
            "JSON Validity (%)": round(result["json_validity_rate"], 2),
            "Valid Predictions": result["valid_predictions"],
            "Total Predictions": result["total_predictions"]
        })
    
    comparison_df = pd.DataFrame(comparison_data)
    comparison_df = comparison_df.sort_values("Accuracy (%)", ascending=False)
    
    # Save comparison table
    comparison_df.to_csv("prompting_methods_comparison.csv", index=False)
    
    print("\n" + "="*60)
    print("FINAL COMPARISON TABLE")
    print("="*60)
    print(comparison_df.to_string(index=False))
    print("\n" + "="*60)
    
    # Find best method (highest accuracy with good validity)
    best_overall = comparison_df[
        comparison_df["JSON Validity (%)"] >= 95
    ].sort_values("Accuracy (%)", ascending=False)
    
    if len(best_overall) > 0:
        best_method = best_overall.iloc[0]
        print(f"\n🏆 BEST METHOD: {best_method['Method']}")
        print(f"   Accuracy: {best_method['Accuracy (%)']:.2f}%")
        print(f"   JSON Validity: {best_method['JSON Validity (%)']:.2f}%")
        print(f"   Sample Size: {best_method['Sample Size']}")
        print("\nThis method will be applied to the backend!")
    else:
        print("\n⚠️  No method with >95% JSON validity found. Using highest accuracy method.")
        best_method = comparison_df.iloc[0]
        print(f"🏆 BEST METHOD: {best_method['Method']}")
        print(f"   Accuracy: {best_method['Accuracy (%)']:.2f}%")
    
    print("\n✅ Testing complete! Results saved to:")
    print("   - prompting_methods_comparison.csv")
    print("   - Individual result files (test_results_*.csv)")

