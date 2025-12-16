import streamlit as st
from dotenv import load_dotenv
import time
import os
import openai
from functools import lru_cache
import hashlib

# 1. SETUP
load_dotenv()

# Set page config
st.set_page_config(page_title="Student Housing AI Ops", layout="wide")

# Password protection function
def check_password():
    """Returns `True` if the user had the correct password."""
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        # Get the hash from Streamlit secrets
        try:
            stored_hash = st.secrets["hashed_password"]
            
            # Hash the user's password
            user_password = st.session_state["password"]
            user_hash = hashlib.sha256(user_password.encode()).hexdigest()
            
            # Compare hashes
            if user_hash == stored_hash:
                st.session_state["password_correct"] = True
                del st.session_state["password"]  # don't store password
            else:
                st.session_state["password_correct"] = False
        except Exception as e:
            st.error(f"Error checking password: {str(e)}")
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

# Now that the password is correct, we can access the secrets
try:
    # Get API key from Streamlit secrets
    openai_api_key = st.secrets["openai_api_key"]
    
    # Initialize OpenAI client
    client = openai.OpenAI(api_key=openai_api_key)
except Exception as e:
    st.error(f"Error accessing OpenAI API key from secrets: {str(e)}")
    st.markdown("""
    ### Configuration Error
    
    The app couldn't find the OpenAI API key in the Streamlit secrets.
    
    Please make sure you've set up the secrets correctly in the Streamlit Cloud dashboard:
    1. Go to your app settings
    2. Click on "Secrets"
    3. Add the following secrets:
       ```
       openai_api_key = "sk-your-api-key-here"
       hashed_password = "your-hashed-password-here"
       ```
    """)
    st.stop()

# Initialize session state for caching
if 'cache' not in st.session_state:
    st.session_state.cache = {}
    
if 'model_name' not in st.session_state:
    st.session_state.model_name = "gpt-3.5-turbo"
    
if 'issue' not in st.session_state:
    st.session_state.issue = "There is water leaking under my bathroom sink"

# 2. DEFINE OPTIMIZED TOOLS
@lru_cache(maxsize=100)
def analyze_lease_responsibility_cached(issue):
    """Cached version of lease analysis to prevent duplicate API calls."""
    # This is the function that will be cached
    return _analyze_lease_responsibility(issue)

def analyze_lease_responsibility(issue):
    """Wrapper to use the cached function"""
    # Check Streamlit cache first (for session persistence)
    cache_key = f"lease_{issue}_{st.session_state.model_name}"
    if cache_key in st.session_state.cache:
        return st.session_state.cache[cache_key]
    
    # Use the cached function
    result = analyze_lease_responsibility_cached(issue)
    
    # Store in Streamlit cache
    st.session_state.cache[cache_key] = result
    return result

def _analyze_lease_responsibility(issue):
    """Direct, optimized OpenAI API call for lease analysis."""
    # Modified prompt to ensure clear labeling of responsibility
    if st.session_state.model_name == "gpt-3.5-turbo":
        prompt = f"""
        Determine if this issue is tenant or property manager responsibility.
        Issue: {issue}
        
        Rules:
        - Tenant: minor clogs, lightbulbs, batteries, tenant damage
        - Manager: structural, major plumbing, HVAC, electrical
        
        Your response MUST start with either:
        "Responsibility: Tenant" OR "Responsibility: Property Manager"
        
        Then provide a brief explanation.
        """
    else:
        prompt = f"""
        Determine if this issue is tenant or property manager responsibility.
        Issue: {issue}
        
        Rules:
        - Tenant: minor clogs, lightbulbs, batteries, tenant damage
        - Manager: structural, major plumbing, HVAC, electrical
        
        Your response MUST start with either:
        "Responsibility: Tenant" OR "Responsibility: Property Manager"
        
        Then provide a brief explanation.
        """
    
    # Direct API call instead of using LangChain
    try:
        response = client.chat.completions.create(
            model=st.session_state.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=150  # Limit token usage for speed
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error analyzing responsibility: {str(e)}"

def recommend_parts(issue):
    """Recommends parts needed for repair."""
    cache_key = f"parts_{issue}_{st.session_state.model_name}"
    if cache_key in st.session_state.cache:
        return st.session_state.cache[cache_key]
    
    prompt = f"List only parts needed to fix: {issue}. Provide as a comma-separated list. Be brief."
    
    try:
        response = client.chat.completions.create(
            model=st.session_state.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=100
        )
        result = response.choices[0].message.content
        st.session_state.cache[cache_key] = result
        return result
    except Exception as e:
        return f"Error recommending parts: {str(e)}"

def check_inventory(part_name):
    """Checks if parts are in stock."""
    # Fast local lookup, no API call needed
    inventory_data = {
        "valve": "IN STOCK: Main Warehouse, Bin 4B. Quantity: 15.",
        "filter": "IN STOCK: Main Warehouse, Bin 2A. Quantity: 50.",
        "pipe": "IN STOCK: Main Warehouse, Bin 3C. Quantity: 20.",
        "faucet": "IN STOCK: Main Warehouse, Bin 4C. Quantity: 8.",
        "seal": "IN STOCK: Main Warehouse, Bin 5D. Quantity: 30.",
        "gasket": "IN STOCK: Main Warehouse, Bin 5D. Quantity: 25.",
        "toilet": "IN STOCK: Auxiliary Warehouse, Bin 1A. Quantity: 5.",
        "showerhead": "IN STOCK: Main Warehouse, Bin 4E. Quantity: 12.",
        "drain": "IN STOCK: Main Warehouse, Bin 3B. Quantity: 18.",
        "hose": "IN STOCK: Main Warehouse, Bin 6A. Quantity: 22.",
        "trap": "IN STOCK: Main Warehouse, Bin 3D. Quantity: 10.",
        "washer": "IN STOCK: Main Warehouse, Bin 5C. Quantity: 40.",
        "wrench": "TOOL: Available in maintenance van."
    }
    
    # If part_name is empty or None, return a default message
    if not part_name or not isinstance(part_name, str):
        return "No inventory information available."
    
    for key in inventory_data:
        if key in part_name.lower():
            return inventory_data[key]
    
    return "OUT OF STOCK. Nearest vendor: Grainger (2 day delivery)."

def get_tenant_diy_instructions(issue):
    """Provides DIY instructions for tenant-responsibility issues."""
    cache_key = f"diy_{issue}_{st.session_state.model_name}"
    if cache_key in st.session_state.cache:
        return st.session_state.cache[cache_key]
    
    prompt = f"""
    Provide simple DIY steps for a tenant to fix this issue: {issue}
    
    Include:
    1. Required tools/materials
    2. Step-by-step instructions
    3. Safety warnings
    4. When to call a professional instead
    
    Format as a numbered list.
    """
    
    try:
        response = client.chat.completions.create(
            model=st.session_state.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=350
        )
        result = response.choices[0].message.content
        st.session_state.cache[cache_key] = result
        return result
    except Exception as e:
        return f"Error generating DIY instructions: {str(e)}"

# Function to determine if it's tenant responsibility
def is_tenant_issue(responsibility_text):
    """Better detection of tenant responsibility using simple string checks."""
    # Convert to lowercase for case-insensitive matching
    text = responsibility_text.lower()
    
    # Check for direct statements about tenant responsibility
    if "responsibility: tenant" in text:
        return True
    
    if "tenant responsibility" in text or "tenant's responsibility" in text:
        return True
        
    # Check for tenant being mentioned as responsible
    if "tenant is responsible" in text:
        return True
        
    # Check if the text explicitly mentions it's not property manager's responsibility
    if "not property manager" in text and "not tenant" not in text:
        return True
        
    # Default to property manager if unclear
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
            st.rerun()  # Use st.rerun() instead of experimental_rerun
    
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
    
    try:
        # STEP 1: Analyze lease responsibility (OPTIMIZED)
        status_text.text("Step 1/3: Analyzing lease responsibility...")
        start_time = time.time()
        
        # Use direct API call instead of CrewAI for speed
        responsibility_result = analyze_lease_responsibility(issue)
        
        step1_time = time.time() - start_time
        progress_bar.progress(33)
        status_text.text(f"Step 1/3 completed in {step1_time:.1f} seconds")
        
        # Check if tenant responsibility using improved detection
        is_tenant_responsibility = is_tenant_issue(responsibility_result)
        
        if is_tenant_responsibility:
            # Step 2: Get DIY instructions for tenant
            status_text.text("Step 2/3: Generating DIY instructions...")
            start_time = time.time()
            
            diy_result = get_tenant_diy_instructions(issue)
            
            progress_bar.progress(66)
            status_text.text(f"Step 2/3 completed in {time.time() - start_time:.1f} seconds")
            
            # Step 3: Format final result
            status_text.text("Step 3/3: Preparing final report...")
            final_result = f"{responsibility_result}\n\n**DIY INSTRUCTIONS FOR TENANT:**\n{diy_result}"
            progress_bar.progress(100)
            
        else:
            # Step 2: Identify parts needed
            status_text.text("Step 2/3: Identifying required parts...")
            start_time = time.time()
            
            parts_result = recommend_parts(issue)
            
            progress_bar.progress(66)
            status_text.text(f"Step 2/3 completed in {time.time() - start_time:.1f} seconds")
            
            # Step 3: Check inventory for each part - SIMPLIFIED TO AVOID HANGING
            status_text.text("Step 3/3: Checking inventory...")
            start_time = time.time()
            
            # FIXED: More robust parts extraction with error handling
            try:
                # Simpler parts extraction
                parts_list = []
                if parts_result and isinstance(parts_result, str):
                    # Split by commas and newlines
                    for part in parts_result.replace("\n", ",").split(","):
                        part = part.strip()
                        if part and not part.startswith("Error"):
