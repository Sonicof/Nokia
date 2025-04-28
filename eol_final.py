import requests
import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional

# Page config
st.set_page_config(
    page_title="Software EOL Tracker",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    /* Dark theme with purple accent */
    :root {
        --accent: #BB86FC;
        --bg: #121212;
        --card: #1E1E1E;
        --text: #E1E1E1;
        --secondary: #A0A0A0;
    }
    
    .main {background-color: var(--bg); color: var(--text);}
    h1, h2, h3 {color: var(--text); font-weight: 600; font-family: 'Inter', sans-serif;}
    
    .card {
        background-color: var(--card);
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border-left: 3px solid var(--accent);
    }
    
    .metric {
        background-color: #252525;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
        margin: 0.5rem 0;
    }
    
    .metric-value {font-size: 2rem; font-weight: bold; color: var(--accent);}
    .metric-label {color: var(--secondary); font-size: 0.9rem;}
    
    .status-active {color: #4CAF50; font-weight: bold;}
    .status-eol {color: #CF6679; font-weight: bold;}
    
    .footer {
        text-align: center;
        color: var(--secondary);
        font-size: 0.8rem;
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid #333;
    }
    
    /* Table styling */
    .dataframe {background-color: var(--card); border: none !important;}
    .dataframe th {background-color: #252525 !important; color: var(--accent) !important;}
    .dataframe td {color: var(--text) !important; border-bottom: 1px solid #333 !important;}
    
    /* Button styling */
    .stButton > button {
        background-color: var(--accent);
        color: black;
        border: none;
        border-radius: 4px;
        font-weight: 600;
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# --- Data fetcher functions ---
def fetch_endoflife_date(software: str) -> Optional[List[Dict]]:
    url = f"https://endoflife.date/api/{software}.json"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if not data:
                return None
            versions_data = []
            for version in data:
                versions_data.append({
                    "Version": version.get("cycle", "Unknown"),
                    "Release Date": version.get("releaseDate", "Unknown"),
                    "EOL Date": version.get("eol", "Unknown"),
                    "Latest": version.get("latest", "Unknown"),
                    "LTS": "Yes" if version.get("lts", False) else "No",
                    "Support Status": "Active" if version.get("eol") == False else 
                                     "End of Life" if version.get("eol") else "Unknown"
                })
            return versions_data
        return None
    except Exception as e:
        return f"Error: {str(e)}"

def fetch_github_activity(software: str) -> Optional[List[Dict]]:
    github_api_url = f"https://api.github.com/search/repositories?q={software}&sort=updated&order=desc"
    headers = {"Accept": "application/vnd.github.v3+json"}
    try:
        response = requests.get(github_api_url, headers=headers)
        if response.status_code == 200:
            repos = response.json()["items"]
            if repos:
                repo_info = []
                for repo in repos[:5]:  # Only get top 5 for simplicity
                    repo_info.append({
                        "Repository": repo["full_name"],
                        "Stars": repo["stargazers_count"],
                        "Last Updated": datetime.strptime(repo["updated_at"], 
                                       "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d"),
                        "Description": repo["description"] or "No description available",
                        "Language": repo["language"] or "Unknown",
                        "Forks": repo["forks_count"],
                        "Open Issues": repo["open_issues_count"]
                    })
                return repo_info
        return None
    except Exception as e:
        return f"Error: {str(e)}"

def fetch_npm_info(software: str) -> Optional[Dict]:
    try:
        response = requests.get(f"https://registry.npmjs.org/{software}")
        if response.status_code == 200:
            data = response.json()
            latest = data.get("dist-tags", {}).get("latest")
            if latest:
                version_info = data.get("versions", {}).get(latest, {})
                return {
                    "Package Name": software,
                    "Latest Version": latest,
                    "Last Published": data.get("time", {}).get(latest),
                    "License": version_info.get("license"),
                    "Dependencies": len(version_info.get("dependencies", {})),
                    "Downloads": data.get("downloads", {}).get("last-month", 0)
                }
        return None
    except Exception as e:
        return f"Error: {str(e)}"

def fetch_pypi_info(software: str) -> Optional[Dict]:
    try:
        response = requests.get(f"https://pypi.org/pypi/{software}/json")
        if response.status_code == 200:
            data = response.json()
            info = data.get("info", {})
            return {
                "Package Name": software,
                "Latest Version": info.get("version"),
                "Last Published": info.get("upload_time"),
                "License": info.get("license"),
                "Python Versions": ", ".join(info.get("classifiers", [])[:3]),
                "Downloads": info.get("downloads", {}).get("last_month", 0)
            }
        return None
    except Exception as e:
        return f"Error: {str(e)}"

def fetch_dockerhub_info(software: str) -> Optional[Dict]:
    try:
        response = requests.get(f"https://hub.docker.com/v2/repositories/library/{software}/tags?page_size=1")
        if response.status_code == 200:
            data = response.json()
            if data.get('results'):
                tag = data['results'][0]
                return {
                    "Image": software,
                    "Tag": tag.get("name"),
                    "Updated": tag.get("last_updated"),
                    "Pulls": tag.get("pull_count", "N/A")
                }
        return None
    except Exception as e:
        return f"Error: {str(e)}"

def fetch_rubygems_info(software: str) -> Optional[Dict]:
    try:
        response = requests.get(f"https://rubygems.org/api/v1/gems/{software}.json")
        if response.status_code == 200:
            data = response.json()
            # Convert the license list to string to fix the TypeError
            licenses = data.get("licenses", [])
            license_str = ", ".join(licenses) if isinstance(licenses, list) else str(licenses)
            
            return {
                "Gem Name": data.get("name"),
                "Latest Version": data.get("version"),
                "Downloads": data.get("downloads"),
                "Last Updated": data.get("version_created_at"),
                "License": license_str
            }
        return None
    except Exception as e:
        return f"Error: {str(e)}"

def fetch_maven_info(software: str) -> Optional[Dict]:
    try:
        response = requests.get(f"https://search.maven.org/solrsearch/select?q={software}&rows=1&wt=json")
        if response.status_code == 200:
            data = response.json()
            docs = data.get('response', {}).get('docs', [])
            if docs:
                doc = docs[0]
                return {
                    "Artifact": doc.get("id"),
                    "Latest Version": doc.get("latestVersion"),
                    "Last Updated": doc.get("timestamp"),
                    "Group": doc.get("g"),
                    "ArtifactId": doc.get("a")
                }
        return None
    except Exception as e:
        return f"Error: {str(e)}"

def fetch_os_package_info(software: str) -> Optional[Dict]:
    """Fetches info from OS package managers (e.g., Ubuntu, Alpine, etc.)."""
    # This is a stub; real implementation would require scraping or using APIs.
    return None

def fetch_security_advisories(software: str) -> Optional[List[Dict]]:
    try:
        url = f"https://api.github.com/search/repositories?q={software}+security+advisory&sort=updated&order=desc"
        response = requests.get(url)
        if response.status_code == 200:
            repos = response.json()["items"]
            if repos:
                advisories = []
                for repo in repos[:3]:
                    advisories.append({
                        "Title": repo["name"],
                        "Description": repo["description"],
                        "Updated": datetime.strptime(repo["updated_at"], 
                                   "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d"),
                        "URL": repo["html_url"]
                    })
                return advisories
        return None
    except Exception as e:
        return None

def fetch_community_stats(software: str) -> Dict:
    stats = {
        "Stack Overflow": {
            "Questions": 0,
            "Tags": []
        },
        "GitHub": {
            "Repositories": 0,
            "Stars": 0
        }
    }
    try:
        response = requests.get(f"https://api.stackexchange.com/2.3/tags/{software}/info?site=stackoverflow")
        if response.status_code == 200:
            data = response.json()
            if data.get("items"):
                stats["Stack Overflow"]["Questions"] = data["items"][0].get("count", 0)
                stats["Stack Overflow"]["Tags"] = [tag["name"] for tag in data["items"][0].get("related_tags", [])]
    except Exception as e:
        pass
    
    try:
        github_api_url = f"https://api.github.com/search/repositories?q={software}+in:name"
        headers = {"Accept": "application/vnd.github.v3+json"}
        response = requests.get(github_api_url, headers=headers)
        if response.status_code == 200:
            stats["GitHub"]["Repositories"] = response.json().get("total_count", 0)
    except Exception as e:
        pass
    
    return stats

# Helper functions for UI rendering
def render_status_badge(status):
    if status == "Active":
        return f'<span class="status-active">● {status}</span>'
    elif status in ["End of Life", "EOL"]:
        return f'<span class="status-eol">● {status}</span>'
    else:
        return f'<span>○ {status}</span>'

def render_metric(label, value, suffix=""):
    return f"""
    <div class="metric">
        <div class="metric-value">{value}{suffix}</div>
        <div class="metric-label">{label}</div>
    </div>
    """

# Function to ensure values are of acceptable types for st.metric
def format_metric_value(value):
    if value is None:
        return None
    elif isinstance(value, (int, float, str)):
        return value
    elif isinstance(value, list):
        return ", ".join(str(item) for item in value)
    else:
        return str(value)

# --- Source Registry ---
SOURCES = {
    "EndOfLife.date": fetch_endoflife_date,
    "GitHub": fetch_github_activity,
    "NPM": fetch_npm_info,
    "PyPI": fetch_pypi_info,
    "Docker Hub": fetch_dockerhub_info,
    "RubyGems": fetch_rubygems_info,
    "Maven Central": fetch_maven_info,
    "OS Package Manager": fetch_os_package_info,
}

# Header
st.markdown("""
<div style="display: flex; align-items: center; margin-bottom: 1rem;">
    <span style="font-size: 2.5rem; margin-right: 0.5rem;">🔍</span>
    <h1 style="margin: 0;">Software EOL Tracker</h1>
</div>
<p style="color: #A0A0A0; margin-top: 0;">Track end-of-life dates for software across multiple sources</p>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; margin-bottom: 1.5rem;">
        <h2>About This Tool</h2>
        <div style="width: 50px; height: 3px; background-color: #BB86FC; margin: 0 auto 1rem auto;"></div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style="background-color: #252525; padding: 1rem; border-radius: 8px;">
        <p>Monitor software lifecycle status from:</p>
        <ul>
    """, unsafe_allow_html=True)
    
    # List all sources from the SOURCES dictionary
    for source in SOURCES.keys():
        st.markdown(f"<li>{source}</li>", unsafe_allow_html=True)
    
    # Add the additional sources
    st.markdown("""
            <li>Stack Overflow</li>
            <li>Security Advisories</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

# Search input
st.markdown('<div class="card">', unsafe_allow_html=True)
col1, col2 = st.columns([3, 1])
with col1:
    software = st.text_input("", placeholder="Enter software name (e.g., python, nodejs, react)", 
                            label_visibility="collapsed", key="software_input")
with col2:
    search_button = st.button("Analyze", key="search_button", use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

# Example buttons
if not software:
    st.markdown("""
    <div style="text-align: center; margin-top: 2rem;">
        <h3>Popular Searches</h3>
        <div style="display: flex; justify-content: center; gap: 1rem; flex-wrap: wrap;">
    """, unsafe_allow_html=True)
    
    examples = ["python", "nodejs", "react", "ubuntu", "php"]
    cols = st.columns(len(examples))
    for i, example in enumerate(cols):
        if example.button(examples[i], key=f"example_{i}"):
            software = examples[i]
            search_button = True
    
    st.markdown("</div></div>", unsafe_allow_html=True)

# Main content logic
if search_button and software:
    st.markdown(f"""
    <div style="text-align: center; margin: 1.5rem 0;">
        <h2>Analysis Results for "{software}"</h2>
        <div style="width: 80px; height: 3px; background-color: #BB86FC; margin: 0.5rem auto;"></div>
    </div>
    """, unsafe_allow_html=True)
    
    with st.spinner("Fetching data from multiple sources..."):
        # Fetch data
        eol_data = fetch_endoflife_date(software)
        github_data = fetch_github_activity(software)
        npm_data = fetch_npm_info(software)
        pypi_data = fetch_pypi_info(software)
        docker_data = fetch_dockerhub_info(software)
        rubygems_data = fetch_rubygems_info(software)
        maven_data = fetch_maven_info(software)
        os_package_data = fetch_os_package_info(software)
        security_data = fetch_security_advisories(software)
        community_data = fetch_community_stats(software)
        
        # Create tabs - include all sources plus Community and Security
        tab_names = ["Overview", "Version History", "GitHub", "Package Registries", "Community", "Security"]
        tabs = st.tabs(tab_names)
        
        # Overview tab
        with tabs[0]:
            # Status summary card
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Status Summary")
            
            # Parse version data
            active_count = 0
            eol_count = 0
            all_versions = []
            latest_version = "Unknown"
            
            if isinstance(eol_data, list) and eol_data:
                active_count = sum(1 for v in eol_data if v.get("Support Status") == "Active")
                eol_count = sum(1 for v in eol_data if v.get("Support Status") == "End of Life")
                # Find the latest version by release date
                all_versions = sorted(
                    [v for v in eol_data if v.get("Release Date") and v.get("Release Date") != "Unknown"],
                    key=lambda x: x.get("Release Date", "0000-00-00"),
                    reverse=True
                )
                if all_versions:
                    latest_version = all_versions[0].get("Version", "Unknown")
                else:
                    # If no valid release dates, use the original list
                    all_versions = eol_data
            
            # Display metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(render_metric("Active Versions", active_count), unsafe_allow_html=True)
            with col2:
                st.markdown(render_metric("EOL Versions", eol_count), unsafe_allow_html=True)
            with col3:
                st.markdown(render_metric("Latest Version", latest_version), unsafe_allow_html=True)
            with col4:
                # Security status
                security_count = len(security_data) if isinstance(security_data, list) else 0
                security_status = "High Risk" if security_count > 2 else "Low Risk" if security_count == 0 else "Medium Risk"
                st.markdown(render_metric("Security Status", security_status), unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Latest versions
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Latest Versions")
            
            if all_versions:
                # Show at most 3 latest versions, or all if less than 3
                versions_to_show = all_versions[:min(3, len(all_versions))]
                for version in versions_to_show:
                    cols = st.columns([1, 1, 1, 1])
                    with cols[0]:
                        st.markdown(f"**Version:** {version.get('Version', 'Unknown')}")
                    with cols[1]:
                        st.markdown(f"**Released:** {version.get('Release Date', 'Unknown')}")
                    with cols[2]:
                        st.markdown(f"**EOL Date:** {version.get('EOL Date', 'Unknown')}")
                    with cols[3]:
                        status = version.get('Support Status', 'Unknown')
                        st.markdown(render_status_badge(status), unsafe_allow_html=True)
            else:
                st.info(f"No version data found for {software} from EndOfLife.date")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Version History tab
        with tabs[1]:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Version History")
            
            if isinstance(eol_data, list) and eol_data:
                # Create a dataframe for all versions
                df = pd.DataFrame(eol_data)
                # Format status column for HTML rendering
                if 'Support Status' in df.columns:
                    df['Support Status'] = df['Support Status'].apply(lambda x: render_status_badge(x))
                    st.write(df.to_html(escape=False, index=False), unsafe_allow_html=True)
                else:
                    st.dataframe(df, use_container_width=True)
            else:
                st.info(f"No version history found for {software}")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # GitHub tab
        with tabs[2]:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("GitHub Activity")
            
            if isinstance(github_data, list) and github_data:
                st.dataframe(pd.DataFrame(github_data), use_container_width=True)
                
                # Get total stars from top repos
                total_stars = sum(repo.get("Stars", 0) for repo in github_data)
                st.markdown(f"**Total Stars for Top Repos:** {total_stars:,}")
            else:
                st.info(f"No GitHub data found for {software}")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Package Registries tab
        with tabs[3]:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Package Registry Information")
            
            registry_data = {
                "NPM": npm_data,
                "PyPI": pypi_data,
                "Docker Hub": docker_data,
                "RubyGems": rubygems_data,
                "Maven Central": maven_data,
                "OS Package Manager": os_package_data
            }
            
            # Create subtabs for each registry
            registry_tabs = st.tabs(list(registry_data.keys()))
            
            for i, (registry, data) in enumerate(registry_data.items()):
                with registry_tabs[i]:
                    if isinstance(data, dict):
                        cols = st.columns(len(data))
                        for j, (key, value) in enumerate(data.items()):
                            with cols[j % len(cols)]:
                                # Format the value to ensure it's a type that st.metric accepts
                                formatted_value = format_metric_value(value)
                                st.metric(key, formatted_value)
                    else:
                        st.info(f"No {registry} data found for {software}")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
        # Community tab
        with tabs[4]:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Community Statistics")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(render_metric("GitHub Repositories", 
                                           community_data["GitHub"]["Repositories"]), 
                                           unsafe_allow_html=True)
                st.markdown(render_metric("Stack Overflow Questions", 
                                           community_data["Stack Overflow"]["Questions"]), 
                                           unsafe_allow_html=True)
            
            with col2:
                if community_data["Stack Overflow"]["Tags"]:
                    st.markdown("### Related Tags")
                    st.write(", ".join(community_data["Stack Overflow"]["Tags"][:10]))
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Security tab
        with tabs[5]:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Security Advisories")
            
            if isinstance(security_data, list) and security_data:
                for advisory in security_data:
                    st.markdown(f"""
                    <div style="background-color: #252525; padding: 1rem; border-radius: 8px; 
                         margin-bottom: 1rem; border-left: 3px solid #CF6679;">
                        <h3 style="color: #CF6679; margin-top: 0;">{advisory.get('Title', 'Unknown')}</h3>
                        <p>{advisory.get('Description', 'No description')}</p>
                        <div style="display: flex; justify-content: space-between; color: #A0A0A0;">
                            <span>Updated: {advisory.get('Updated', 'Unknown')}</span>
                            <a href="{advisory.get('URL', '#')}" target="_blank" style="color: #BB86FC;">
                                View Advisory
                            </a>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.success("No recent security advisories found for this software")
            
            st.markdown('</div>', unsafe_allow_html=True)

# Empty state
elif not search_button:
    st.markdown("""
    <div style="text-align: center; padding: 3rem 0;">
        <div style="font-size: 3rem; margin-bottom: 1rem;">🔍</div>
        <h2>Enter a software name to begin analysis</h2>
        <p style="color: #A0A0A0;">Track end-of-life dates and software health from multiple sources</p>
    </div>
    """, unsafe_allow_html=True)
elif not software:
    st.error("Please enter a software name to analyze")

# Footer
st.markdown(f"""
<div class="footer">
    <p>Software EOL Tracker • Data sourced from multiple APIs • Last updated: {datetime.now().strftime("%Y-%m-%d")}</p>
</div>
""", unsafe_allow_html=True)