#!/usr/bin/env python3
"""
Test script to validate custom prompt generation for analyze_support command
"""

def generate_custom_prompt(custom_question):
    """Generate the custom analysis prompt"""
    return f"""
You are a customer service analyst for a cryptocurrency/blockchain project. Your task is to analyze chat messages EXCLUSIVELY for issues related to this specific topic:

**EXCLUSIVE FOCUS: {custom_question}**

CRITICAL INSTRUCTIONS:
- IGNORE all other customer service issues that are not directly related to "{custom_question}"
- ONLY identify and categorize messages that relate to the specified topic
- If no messages relate to the topic, return an empty categories array
- Translate any non-English text to English before analysis
- Present all results in English only

ANALYSIS SCOPE:
- Search for messages that mention, discuss, or report problems related to "{custom_question}"
- Look for variations, synonyms, and related terms
- Include both direct mentions and indirect references to the topic
- Focus on actual problems, issues, complaints, or questions about "{custom_question}"

For ONLY the issues related to "{custom_question}", provide:
- A specific category name that relates to the focused topic
- Total number of unique people mentioning issues related to this topic
- A representative example from the actual messages (translated to English if needed)

DO NOT include general customer service issues unless they directly relate to "{custom_question}".

IMPORTANT: Respond ONLY with valid JSON format. Do not include any text before or after the JSON. Do not wrap in code blocks or markdown.

Respond in JSON format with this exact structure:
{{
  "analysis_summary": "Summary of issues found specifically related to '{custom_question}' - if none found, state that clearly",
  "total_issues_found": number,
  "categories": [
    {{
      "category": "Specific issue category related to {custom_question}",
      "count": number_of_people,
      "representative_example": "Example message in English"
    }}
  ]
}}

If no issues related to "{custom_question}" are found, respond with:
{{
  "analysis_summary": "No issues related to '{custom_question}' were found in the analyzed messages",
  "total_issues_found": 0,
  "categories": []
}}
"""

def test_prompt_examples():
    """Test various custom question examples"""
    test_questions = [
        "wallet issues",
        "mining problems", 
        "sync failures",
        "GPU not working",
        "balance discrepancies",
        "installation errors"
    ]
    
    print("Testing custom prompt generation:")
    print("=" * 80)
    
    for question in test_questions:
        print(f"\n📝 Custom Question: '{question}'")
        print("-" * 40)
        
        prompt = generate_custom_prompt(question)
        
        # Check that the prompt contains the key elements
        checks = [
            ("Exclusive focus mentioned", f"EXCLUSIVE FOCUS: {question}" in prompt),
            ("Ignore other issues instruction", "IGNORE all other customer service issues" in prompt),
            ("Topic-specific categories", f"related to {question}" in prompt),
            ("Empty array instruction", "empty categories array" in prompt),
            ("JSON format specified", "JSON format" in prompt),
        ]
        
        print("Validation checks:")
        for check_name, passed in checks:
            status = "✅" if passed else "❌"
            print(f"  {status} {check_name}")
        
        # Show key parts of the prompt
        print(f"\nKey instruction: 'ONLY identify and categorize messages that relate to \"{question}\"'")
        print(f"Scope: 'Search for messages that mention, discuss, or report problems related to \"{question}\"'")

if __name__ == "__main__":
    test_prompt_examples()
