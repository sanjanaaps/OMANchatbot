from app_lib.gemini import query_gemini

# Test basic query
response = query_gemini(
    prompt="What is the role of Oman Central Bank?",
    department="Finance",
    language="en"
)
print("Test 1 - Basic Query:")
print(response)
print("\n" + "-"*50 + "\n")

# Test with context
sample_context = """The Central Bank of Oman (CBO) is responsible for maintaining monetary and financial stability in the Sultanate. It supervises banks, regulates currency, and implements monetary policy."""
response = query_gemini(
    prompt="What are the main responsibilities of CBO?",
    department="Finance",
    language="en",
    context=sample_context
)
print("Test 2 - Query with Context:")
print(response)