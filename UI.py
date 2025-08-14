import streamlit as st
from scraper import scrape_site, save_data, fetch_html, auto_detect_common_fields

st.set_page_config(page_title="Universal Web Scraper", layout="wide")
st.title("🕸 Universal Web Scraper (Advanced + Tor Support)")

# Step 1 - Basic settings
base_url = st.text_input("🌐 Target URL", placeholder="https://example.com or .onion")
use_selenium = st.checkbox("Render JavaScript / Infinite scroll with Selenium")
infinite_scroll = st.checkbox("Infinite scroll page?")
load_more_selector = st.text_input("CSS selector for 'Load More' button (optional)")
scrape_all = st.checkbox("Scrape ALL pages until no next page is found")
auto_mode = st.checkbox("Auto-discover mode (no selectors required)")
use_tor = st.checkbox("Use Tor network (.onion) - Tor must be running locally")

fields = {}
next_selector = None
max_pages = 1


# Step 2 - Field setup
if auto_mode:
    st.info("✅ Auto-discover mode will automatically try to grab tables, lists, and cards.")
else:
    if st.button("🔍 Auto-detect common field selectors"):
        if base_url:
            try:
                html = fetch_html(base_url, use_selenium, use_tor=use_tor)
                detected = auto_detect_common_fields(html)
                if detected:
                    st.success(f"Detected selectors: {detected}")
                    for k, v in detected.items():
                        fields[k] = v
                else:
                    st.warning("No patterns detected.")
            except Exception as e:
                st.error(f"Failed to fetch page: {e}")
        else:
            st.error("Please enter a URL first.")

    max_pages = st.number_input("📄 Pages to scrape (ignored if 'Scrape All' is enabled)", 
                                 min_value=1, value=1)
    field_count = st.number_input("Number of fields to extract", min_value=1, value=1)
    for i in range(int(field_count)):
        fname = st.text_input(f"Field {i+1} name", key=f"name_{i}")
        selector = st.text_input(f"CSS Selector for '{fname}'", key=f"selector_{i}",
                                 help="Right-click → Inspect in browser → Copy selector")
        if fname and selector:
            fields[fname] = selector
    
    next_selector = st.text_input("➡ CSS Selector for NEXT button (optional)",placeholder="a.next.page-numbers")

  
# Step 3 - Output file
  
output_base = st.text_input("💾 Output filename (without extension)", value="scraped_data")

# Step 4 - Run scraper
if st.button("🚀 Start Scraping"):
    if not base_url:
        st.error("❌ Please enter a target URL.")
    elif not auto_mode and not fields:
        st.error("❌ Provide at least one field selector or use Auto-discover mode.")
    else:
        with st.spinner("Scraping in progress...."):
            try:
                results = scrape_site(
                    base_url,
                    fields=fields if not auto_mode else None,
                    next_selector=next_selector if next_selector else None,
                    use_selenium=use_selenium,
                    scrape_all=scrape_all,
                    max_pages=max_pages,
                    auto_mode=auto_mode,
                    infinite_scroll=infinite_scroll,
                    load_more_selector=load_more_selector if load_more_selector else None,
                    use_tor=use_tor
                )
            except Exception as e:
                st.error(f"Scraping failed: {e}")
                results = []

        if not results:
            st.warning("⚠ No data found. Please check selectors, URL, or enable Selenium / Tor if needed.")
        else:
            save_data(results, output_base)
            st.success(f"✅ Scraped {len(results)} items")
            st.dataframe(results)

            # Download buttons
            with open(output_base + ".csv", "rb") as f:
                st.download_button("📥 Download CSV", f, file_name=output_base + ".csv")
            with open(output_base + ".xlsx", "rb") as f:
                st.download_button("📥 Download Excel", f, file_name=output_base + ".xlsx")
            with open(output_base + ".json", "rb") as f:
                st.download_button("📥 Download JSON", f, file_name=output_base + ".json")
