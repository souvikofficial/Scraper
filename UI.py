import time
from urllib.parse import urlparse

import streamlit as st

from scraper import scrape_site, save_data, fetch_html, auto_detect_common_fields

st.set_page_config(page_title="Universal Web Scraper", layout="wide")

# Light theme styling
st.markdown("""
<style>
    /* Force common text elements to black */
    .stApp, p, label, h1, h2, h3, h4, h5, h6, span, div {
        color: #000000 !important;
    }

    /* Main background */
    .stApp {
        background-color: #ffffff;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #f5f5f5;
    }
    
    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        color: #000000 !important;
    }
    
    /* Text inputs & Select boxes */
    .stTextInput > div > div > input, 
    .stNumberInput > div > div > input,
    .stSelectbox > div > div, 
    .stMultiSelect > div > div {
        background-color: #ffffff;
        color: #000000 !important;
        border: 1px solid #d1d5db;
        caret-color: #000000; /* Cursor color */
    }
    
    /* Input placeholder text (optional, usually grey, but let's keep it visible) */
    ::placeholder {
        color: #4a4a4a !important; /* Slightly lighter so it looks like a placeholder, but still dark */
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: #f5f5f5;
        color: #000000 !important;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: #0066cc;
        color: #000000 !important; /* Black text on buttons */
        border: none;
        font-weight: bold; /* Make it readable on dark background */
    }
    
    .stButton > button:hover {
        background-color: #0052a3;
        color: #000000 !important;
    }
    
    /* Download buttons */
    .stDownloadButton > button {
        background-color: #28a745;
        color: #000000 !important; /* Black text on buttons */
        font-weight: bold;
    }
    
    /* Info/warning/error boxes */
    .stAlert {
        background-color: #f8f9fa;
        color: #000000 !important;
    }
    
    .stAlert [data-testid="stMarkdownContainer"] {
        color: #000000 !important;
    }
    
    /* Dataframe */
    .stDataFrame {
        background-color: #ffffff;
        color: #000000 !important;
    }
    
    /* Radio buttons and checkboxes */
    .stRadio > div, .stCheckbox > div, .stRadio label, .stCheckbox label {
        color: #000000 !important;
    }
    
    /* Slider */
    .stSlider > div > div {
        color: #000000 !important;
    }
    
    /* Caption text */
    .stCaption {
        color: #000000 !important;
    }
    
    /* Markdown text */
    .stMarkdown, .stMarkdown p {
        color: #000000 !important;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #f5f5f5;
    }
    
    .stTabs [data-baseweb="tab"] {
        color: #000000 !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("Universal Web Scraper")
st.caption("Flexible scraping with auto-discovery, manual selectors, and optional Selenium/Tor.")

def normalize_input_url(raw_url: str):
    url = (raw_url or "").strip()
    if not url:
        return "", None
    parsed = urlparse(url)
    if parsed.scheme:
        return url, None
    scheme = "http" if url.endswith(".onion") else "https"
    return f"{scheme}://{url}", f"Added {scheme}:// prefix"


if "field_count" not in st.session_state:
    st.session_state.field_count = 1


st.info("Use responsibly and respect target site terms and robots.txt.")

# --- Main Configuration ---
st.header("1. Target & Output")
col1, col2 = st.columns(2)

with col1:
    base_url = st.text_input("Target URL", placeholder="https://example.com or .onion")
    effective_url, url_note = normalize_input_url(base_url)
    if url_note:
        st.caption(url_note)

with col2:
    output_base = st.text_input("Output filename (no extension)", value="scraped_data")

mode = st.radio("Scraping Mode", ["Auto-discover", "Manual selectors"], horizontal=True, help="Auto-discover tries to find lists/tables automatically. Manual allows custom CSS selectors.")
auto_mode = mode == "Auto-discover"

# --- Advanced Settings ---
with st.expander("⚙️ Advanced Configuration (Pagination, Tor, Selenium)", expanded=False):
    st.subheader("Browser & Network")
    c1, c2 = st.columns(2)
    with c1:
        use_selenium = st.checkbox("Render JavaScript (Selenium)", value=False, help="Required for dynamic sites that load data with JS.")
        use_tor = st.checkbox("Use Tor (Onion)", value=False, help="Route traffic through Tor network (must be running locally).")
    with c2:
        normalize_urls = st.checkbox("Normalize URLs", value=True, help="Convert relative links to absolute URLs.")

    st.subheader("Pagination & Limits")
    p1, p2 = st.columns(2)
    with p1:
        scrape_all = st.checkbox("Scrape ALL pages", help="Follows 'Next' button until the end.")
        max_pages = st.number_input(
            "Max Pages",
            min_value=1,
            value=1,
            disabled=scrape_all,
            help="Limit scraping to this number of pages."
        )
    with p2:
        next_selector = st.text_input("Next Button Selector", placeholder="a.next.page-numbers")
    
    if use_selenium:
        st.subheader("Scroll & Dynamic Loading")
        s1, s2 = st.columns(2)
        with s1:
            infinite_scroll = st.checkbox("Infinite scroll", value=False)
        with s2:
            load_more_selector = st.text_input("'Load More' Button Selector", disabled=not use_selenium)

    st.subheader("Timing")
    delay_range = st.slider(
        "Delay between requests (seconds)",
        min_value=0.0,
        max_value=10.0,
        value=(1.0, 2.0),
        step=0.5,
    )
    t1, t2 = st.columns(2)
    with t1:
        request_timeout = st.number_input("Timeout (sec)", min_value=5, max_value=60, value=20)
    with t2:
        request_retries = st.number_input("Retries", min_value=0, max_value=5, value=2)

st.header("2. Data Extraction")
fields = {}

# Step 2 - Field setup
if auto_mode:
    st.info("🤖 Auto-discover mode enabled. the scraper will attempt to identify list items, tables, and cards automatically.")
else:
    c_detect, c_count = st.columns([1, 1])
    with c_detect:
        if st.button("🔍 Auto-detect common selectors"):
            if effective_url:
                with st.spinner("Analyzing page structure..."):
                    try:
                        html = fetch_html(effective_url, use_selenium, use_tor=use_tor)
                        detected = auto_detect_common_fields(html)
                        if detected:
                            st.success(f"Found {len(detected)} patterns!")
                            st.session_state.field_count = max(st.session_state.field_count, len(detected))
                            for idx, (k, v) in enumerate(detected.items()):
                                st.session_state[f"name_{idx}"] = k
                                st.session_state[f"selector_{idx}"] = v
                        else:
                            st.warning("No patterns detected.")
                    except Exception as e:
                        st.error(f"Failed to fetch page: {e}")
            else:
                st.error("Please enter a URL first.")
    
    with c_count:
        field_count = st.number_input("Number of fields", min_value=1, value=st.session_state.field_count, key="field_count")

    st.write("Define your fields:")
    for i in range(int(field_count)):
        fc1, fc2 = st.columns([1, 2])
        with fc1:
            fname = st.text_input(f"Field {i+1} Name", key=f"name_{i}", placeholder="e.g. Title")
        with fc2:
            selector = st.text_input(
                f"CSS Selector",
                key=f"selector_{i}",
                placeholder=f"e.g. h1.product-title",
                help="Right-click element in browser -> Inspect -> Copy Selector"
            )
        if fname and selector:
            fields[fname] = selector


# Step 3 - Run scraper
st.header("3. Execution")
c_fmt, c_run = st.columns([2, 1])

with c_fmt:
    output_formats = st.multiselect(
        "Output formats",
        ["csv", "xlsx", "json"],
        default=["csv", "xlsx", "json"],
    )

with c_run:
    st.write("") # Spacer
    st.write("") # Spacer
    start_btn = st.button("🚀 Start Scraping", type="primary", use_container_width=True)

if start_btn:
    if not effective_url:
        st.error("Please enter a target URL.")
    elif not auto_mode and not fields:
        st.error("Provide at least one field selector or use Auto-discover mode.")
    elif not output_formats:
        st.error("Select at least one output format.")
    else:
        progress = st.progress(0.0)
        status = st.empty()

        def on_progress(page, total):
            if total:
                progress.progress(min(page / total, 1.0))
                status.caption(f"Pages scraped: {page}/{total}")
            else:
                status.caption(f"Pages scraped: {page}")

        start = time.time()
        with st.spinner("Scraping in progress..."):
            try:
                results = scrape_site(
                    effective_url,
                    fields=fields if not auto_mode else None,
                    next_selector=next_selector if next_selector else None,
                    use_selenium=use_selenium,
                    scrape_all=scrape_all,
                    max_pages=max_pages,
                    auto_mode=auto_mode,
                    infinite_scroll=infinite_scroll,
                    load_more_selector=load_more_selector if load_more_selector else None,
                    use_tor=use_tor,
                    delay_range=delay_range,
                    progress_callback=on_progress,
                    normalize_urls=normalize_urls,
                    request_timeout=request_timeout,
                    request_retries=request_retries,
                )
            except Exception as e:
                st.error(f"Scraping failed: {e}")
                results = []

        duration = time.time() - start

        if not results:
            st.warning("No data found. Check selectors, URL, or enable Selenium/Tor if needed.")
        else:
            save_data(results, output_base, formats=output_formats)
            st.success(f"Scraped {len(results)} items in {duration:.1f}s")
            st.dataframe(results, use_container_width=True)

            if "csv" in output_formats:
                with open(output_base + ".csv", "rb") as f:
                    st.download_button("Download CSV", f, file_name=output_base + ".csv")
            if "xlsx" in output_formats:
                with open(output_base + ".xlsx", "rb") as f:
                    st.download_button("Download Excel", f, file_name=output_base + ".xlsx")
            if "json" in output_formats:
                with open(output_base + ".json", "rb") as f:
                    st.download_button("Download JSON", f, file_name=output_base + ".json")
