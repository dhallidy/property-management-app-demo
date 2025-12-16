import streamlit as st
from dotenv import load_dotenv
import time
import os
import openai
from functools import lru_cache

# 1. SETUP
load_dotenv()

# Initialize OpenAI client with better error handling for API key
def get_openai_api_key():
    # Try environment variable first (standard format)
    if 'OPENAI_API_KEY' in os.environ:
        return os.environ['OPENAI_API_KEY']
    
    # Try environment variable with double underscore (your current format)
    if 'OPENAI__API_KEY' in os.environ:
        return os.environ['OPENAI__API_KEY']
    
    # Try Streamlit secrets in nested format
    try:
        return st.secrets["openai"]["api_key"]
    except:
        pass
    
    # Try Streamlit secrets in flat format
    try:
        return st.secrets["OPENAI_API_KEY"]
    except:
        pass
        
    # Try Streamlit secrets with double underscore
    try:
        return st.secrets["OPENAI__API_KEY"]
    except:
        pass
    
    # If we get here, we couldn't find the API key
    st.error("OpenAI API key not found. Please check your configuration.")
    st.stop()

# Get API key and initialize client
openai_api_key = get_openai_api_key()
client = openai.OpenAI(api_key=openai_api_key)



# Initialize OpenAI client directly for faster API calls
openai_api_key = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key=openai_api_key)

# 2. DEFINE OPTIMIZED TOOLS
@lru_cache(maxsize=100)  # Python's built-in caching
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
    
    prompt = f"List only parts needed to fix: {issue}. Be brief."
    
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
    """Better detection of tenant responsibility using regex and multiple checks."""
    # Convert to lowercase for case-insensitive matching
    text = responsibility_text.lower()
    
    # Check for direct statements about tenant responsibility
    if re.search(r"responsibility:\s*tenant", text):
        return True
    
    if "tenant responsibility" in text or "tenant's responsibility" in text:
        return True
        
    # Check for tenant being mentioned as responsible
    if re.search(r"tenant\s+is\s+responsible", text):
        return True
        
    # Check if the text explicitly mentions it's not property manager's responsibility
    if re.search(r"not\s+.*\s*property\s+manager", text) and not re.search(r"not\s+.*\s*tenant", text):
        return True
        
    # Default to property manager if unclear
    return False

# 3. STREAMLIT UI SETUP
st.set_page_config(page_title="Student Housing AI Ops", layout="wide")

# Initialize session state for caching
if 'cache' not in st.session_state:
    st.session_state.cache = {}
    
if 'model_name' not in st.session_state:
    st.session_state.model_name = "gpt-3.5-turbo"
    
if 'issue' not in st.session_state:
    st.session_state.issue = "There is water leaking under my bathroom sink"

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
        
    else:
        # Step 2: Identify parts needed
        status_text.text("Step 2/3: Identifying required parts...")
        start_time = time.time()
        
        parts_result = recommend_parts(issue)
        
        progress_bar.progress(66)
        status_text.text(f"Step 2/3 completed in {time.time() - start_time:.1f} seconds")
        
        # Step 3: Check inventory for each part
        status_text.text("Step 3/3: Checking inventory...")
        start_time = time.time()
        
        # Extract parts from the result
        parts_list = [part.strip() for part in parts_result.replace("\n", ",").split(",") if part.strip()]
        
        inventory_results = []
        for part in parts_list:
            if part:
                inventory_status = check_inventory(part)
                inventory_results.append(f"• {part}: {inventory_status}")
        
        inventory_text = "\n".join(inventory_results) if inventory_results else "No specific parts identified."
        
        final_result = f"{responsibility_result}\n\n**PARTS NEEDED:**\n{parts_result}\n\n**INVENTORY STATUS:**\n{inventory_text}"
    
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
    
# Debug info to help troubleshoot responsibility detection    
if st.checkbox("Show debug info"):        
    st.write("### Debug Information")        
    st.write(f"Responsibility text: {responsibility_result}")        
    st.write(f"Detected as tenant responsibility: {is_tenant_responsibility}")        
    st.write("Text contains 'tenant responsibility': {0}".format("tenant responsibility" in responsibility_result.lower()))                
    st.write("Text contains \"tenant's responsibility\": {0}".format("tenant's responsibility" in responsibility_result.lower()))       
    st.write("Text contains 'responsibility: tenant': {0}".format("responsibility: tenant" in responsibility_result.lower()))

# Add a clear cache button to sidebar
if st.sidebar.button("Clear Cache"):
    st.session_state.cache = {}
    st.sidebar.success("Cache cleared!")

# Add timing metrics
if st.checkbox("Show performance metrics"):
    st.write("### Performance Optimizations")
    st.write("1. **Direct API calls** instead of using CrewAI or LangChain")
    st.write("2. **Python's built-in LRU cache** for function-level caching")
    st.write("3. **Streamlined prompts** with fewer tokens")
    st.write("4. **Token limits** to ensure faster responses")
    st.write("5. **Pre-computed examples** for instant results")
