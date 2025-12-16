import streamlit as st
import time
import os
import openai
from functools import lru_cache
import hashlib

# Set page config
st.set_page_config(page_title="Student Housing AI Ops", layout="wide")

# Password protection function
def check_password():
    """Returns `True` if the user had the correct password."""
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        # For demo purposes, use a simple hardcoded password
        # In production, use the hashed password from secrets
        if st.session_state["password"] == "property123":
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.markdown("# 🔒 Property Management System")
        st.markdown("Please enter the password to access the system.")
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.markdown("# 🔒 Property Management System")
        st.markdown("Please enter the password to access the system.")
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct.
        return True

# Check password before showing the app
if not check_password():
    st.stop()  # Don't continue with the rest of the app

# Get API key from Streamlit secrets
try:
    openai_api_key = st.secrets["openai_api_key"]
except:
    # For development, can use this fallback
    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    
# Initialize OpenAI client
client = openai.OpenAI(api_key=openai_api_key)

# Initialize session state for caching
if 'cache' not in st.session_state:
    st.session_state.cache = {}
    
if 'model_name' not in st.session_state:
    st.session_state.model_name = "gpt-3.5-turbo"
    
if 'issue' not in st.session_state:
    st.session_state.issue = "There is water leaking under my bathroom sink"

# Simple OpenAI API call function
def ask_openai(prompt, model="gpt-3.5-turbo", max_tokens=200):
    """Makes a simple OpenAI API call with error handling."""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

# Function to determine if it's tenant responsibility
def is_tenant_issue(responsibility_text):
    """Simple detection of tenant responsibility."""
    text = responsibility_text.lower()
    if "responsibility: tenant" in text or "tenant responsibility" in text:
        return True
    return False

# 3. STREAMLIT UI SETUP
st.title("🏢 Property Operations AI Agent")
st.markdown("""
**Business Value Demo:** This agent triages incoming tenant requests, determines lease liability, and automatically checks inventory for required repairs.
""")

# Sidebar for inputs with simplified options
with st.sidebar:
    st.header("Simulation Inputs")
    issue = st.text_input("Tenant Issue", value=st.session_state.issue)
    
    # Update session state when issue changes
    if issue != st.session_state.issue:
        st.session_state.issue = issue
    
    model_option = st.radio(
        "Select Model",
        ["Fast (GPT-3.5)", "Standard (GPT-4)"],
        index=0,
        help="Fast is cheaper and quicker, Standard is more accurate"
    )
    
    # Update model if changed
    selected_model = "gpt-3.5-turbo" if model_option == "Fast (GPT-3.5)" else "gpt-4"
    if selected_model != st.session_state.model_name:
        st.session_state.model_name = selected_model
    
    # Precomputed examples for instant results
    st.subheader("Quick Examples")
    example_issues = {
        "Leaky sink": "There is water leaking under my bathroom sink",
        "Broken AC": "The air conditioner isn't cooling my apartment",
        "Clogged toilet": "My toilet is clogged and won't flush",
        "Light bulb": "The light in my bedroom doesn't work"
    }
    
    for label, example in example_issues.items():
        if st.button(label):
            st.session_state.issue = example
            st.rerun()
    
    run_btn = st.button("Run Analysis", type="primary")

# Use the issue from session state
issue = st.session_state.issue

# Check if we have this result cached
cache_key = f"final_{issue}_{st.session_state.model_name}"
if cache_key in st.session_state.cache:
    st.success("Retrieved from cache (instant result)")
    st.subheader("Final Agent Report")
    st.markdown(st.session_state.cache[cache_key])
elif run_btn:
    # Show progress instead of spinner for better UX
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # STEP 1: Analyze lease responsibility
    status_text.text("Step 1/3: Analyzing lease responsibility...")
    
    responsibility_prompt = f"""
    Determine if this issue is tenant or property manager responsibility.
    Issue: {issue}
    
    Rules:
    - Tenant: minor clogs, lightbulbs, batteries, tenant damage
    - Manager: structural, major plumbing, HVAC, electrical
    
    Your response MUST start with either:
    "Responsibility: Tenant" OR "Responsibility: Property Manager"
    
    Then provide a brief explanation.
    """
    
    responsibility_result = ask_openai(responsibility_prompt, st.session_state.model_name, 150)
    
    progress_bar.progress(33)
    status_text.text("Step 1/3 completed")
    
    # Check if tenant responsibility
    is_tenant_responsibility = is_tenant_issue(responsibility_result)
    
    if is_tenant_responsibility:
        # Step 2: Get DIY instructions for tenant
        status_text.text("Step 2/3: Generating DIY instructions...")
        
        diy_prompt = f"""
        Provide simple DIY steps for a tenant to fix this issue: {issue}
        
        Include:
        1. Required tools/materials
        2. Step-by-step instructions
        3. Safety warnings
        4. When to call a professional instead
        
        Format as a numbered list.
        """
        
        diy_result = ask_openai(diy_prompt, st.session_state.model_name, 350)
        
        progress_bar.progress(66)
        status_text.text("Step 2/3 completed")
        
        # Step 3: Format final result
        status_text.text("Step 3/3: Preparing final report...")
        final_result = f"{responsibility_result}\n\n**DIY INSTRUCTIONS FOR TENANT:**\n{diy_result}"
        
    else:
        # Step 2: Identify parts needed
        status_text.text("Step 2/3: Identifying required parts...")
        
        parts_prompt = f"List only parts needed to fix: {issue}. Be brief."
        parts_result = ask_openai(parts_prompt, st.session_state.model_name, 100)
        
        progress_bar.progress(66)
        status_text.text("Step 2/3 completed")
        
        # Step 3: Add hardcoded inventory status
        status_text.text("Step 3/3: Checking inventory...")
        
        # Hardcoded inventory status for common plumbing issues
        inventory_status = """
        • P-trap: IN STOCK: Main Warehouse, Bin 3D. Quantity: 10.
        • Pipe: IN STOCK: Main Warehouse, Bin 3C. Quantity: 20.
        • Gasket: IN STOCK: Main Warehouse, Bin 5D. Quantity: 25.
        • Seal: IN STOCK: Main Warehouse, Bin 5D. Quantity: 30.
        • Valve: IN STOCK: Main Warehouse, Bin 4B. Quantity: 15.
        • Faucet: IN STOCK: Main Warehouse, Bin 4C. Quantity: 8.
        """
        
        final_result = f"{responsibility_result}\n\n**PARTS NEEDED:**\n{parts_result}\n\n**INVENTORY STATUS:**\n{inventory_status}"
    
    progress_bar.progress(100)
    status_text.text("Analysis complete!")
    time.sleep(0.5)  # Small delay for better UX
    status_text.empty()  # Clear status text
    
    # Cache the final result
    st.session_state.cache[cache_key] = final_result
    
    # Display Results
    st.success("Analysis Complete")
    st.subheader("Final Agent Report")
    st.markdown(final_result)

# Add a clear cache button to sidebar
if st.sidebar.button("Clear Cache"):
    st.session_state.cache = {}
    st.sidebar.success("Cache cleared!")
