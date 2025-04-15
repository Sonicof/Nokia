import requests
import json
from bs4 import BeautifulSoup
import streamlit as st
from datetime import datetime
import pandas as pd
import re
from typing import Dict, List, Optional

def get_eol_from_endoflife_date(software: str) -> Optional[List[Dict]]:
    """Fetches detailed EOL data from endoflife.date API"""
    url = f"https://endoflife.date/api/{software}.json"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if not data:
                return None
            
            versions_data = []
            for version in data:
                version_info = {
                    "Version": version.get("cycle", "Unknown"),
                    "Release Date": version.get("releaseDate", "Unknown"),
                    "EOL Date": version.get("eol", "Unknown"),
                    "Latest": version.get("latest", "Unknown"),
                    "LTS": "Yes" if version.get("lts", False) else "No",
                    "Support Status": "Active" if version.get("eol") == False else "End of Life" if version.get("eol") else "Unknown"
                }
                versions_data.append(version_info)
            
            return versions_data
        return None
    except Exception as e:
        st.error(f"Error fetching EOL data: {str(e)}")
        return None

def check_github_activity(software: str) -> Optional[List[Dict]]:
    """Checks GitHub repository activity for detailed information."""
    github_api_url = f"https://api.github.com/search/repositories?q={software}&sort=updated&order=desc"
    headers = {"Accept": "application/vnd.github.v3+json"}
    
    try:
        response = requests.get(github_api_url, headers=headers)
        if response.status_code == 200:
            repos = response.json()["items"]
            if repos:
                repo_info = []
                for repo in repos[:5]:  # Get top 5 most active repos
                    info = {
                        "Repository": repo["full_name"],
                        "Stars": repo["stargazers_count"],
                        "Last Updated": datetime.strptime(repo["updated_at"], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d"),
                        "Description": repo["description"] or "No description available",
                        "Language": repo["language"] or "Unknown",
                        "Forks": repo["forks_count"],
                        "Open Issues": repo["open_issues_count"]
                    }
                    repo_info.append(info)
                return repo_info
        return None
    except Exception as e:
        st.error(f"Error checking GitHub: {str(e)}")
        return None

def get_npm_info(software: str) -> Optional[Dict]:
    """Fetches package information from NPM registry."""
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
                    "Last Published": version_info.get("time", {}).get(latest),
                    "License": version_info.get("license"),
                    "Dependencies": len(version_info.get("dependencies", {})),
                    "Downloads": data.get("downloads", {}).get("last-month", 0)
                }
        return None
    except Exception as e:
        st.error(f"Error fetching NPM data: {str(e)}")
        return None

def get_pypi_info(software: str) -> Optional[Dict]:
    """Fetches package information from PyPI."""
    try:
        response = requests.get(f"https://pypi.org/pypi/{software}/json")
        if response.status_code == 200:
            data = response.json()
            latest = data.get("info", {})
            return {
                "Package Name": software,
                "Latest Version": latest.get("version"),
                "Last Published": latest.get("upload_time"),
                "License": latest.get("license"),
                "Python Versions": ", ".join(latest.get("classifiers", [])),
                "Downloads": latest.get("downloads", {}).get("last_month", 0)
            }
        return None
    except Exception as e:
        st.error(f"Error fetching PyPI data: {str(e)}")
        return None

def get_security_advisories(software: str) -> Optional[List[Dict]]:
    """Fetches security advisories from GitHub Security Advisories."""
    try:
        response = requests.get(f"https://api.github.com/search/repositories?q={software}+security+advisory&sort=updated&order=desc")
        if response.status_code == 200:
            repos = response.json()["items"]
            if repos:
                advisories = []
                for repo in repos[:3]:
                    info = {
                        "Title": repo["name"],
                        "Description": repo["description"],
                        "Last Updated": datetime.strptime(repo["updated_at"], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d"),
                        "URL": repo["html_url"]
                    }
                    advisories.append(info)
                return advisories
        return None
    except Exception as e:
        st.error(f"Error fetching security advisories: {str(e)}")
        return None

def get_community_stats(software: str) -> Dict:
    """Gathers community statistics from various sources."""
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
    
    # Stack Overflow stats
    try:
        response = requests.get(f"https://api.stackexchange.com/2.3/tags/{software}/info?site=stackoverflow")
        if response.status_code == 200:
            data = response.json()
            if data.get("items"):
                stats["Stack Overflow"]["Questions"] = data["items"][0].get("count", 0)
                stats["Stack Overflow"]["Tags"] = [tag["name"] for tag in data["items"][0].get("related_tags", [])]
    except Exception as e:
        st.error(f"Error fetching Stack Overflow stats: {str(e)}")
    
    return stats

# Streamlit UI
st.set_page_config(page_title="Software EOL Checker", layout="wide")
st.title("Software End-of-Life Information Checker")

# Sidebar for additional information
with st.sidebar:
    st.header("About")
    st.write("""
    This tool provides comprehensive information about software end-of-life dates,
    community activity, security status, and package information from multiple sources.
    """)
    st.markdown("### Data Sources")
    st.markdown("""
    - endoflife.date API
    - GitHub API
    - NPM Registry
    - PyPI
    - Stack Overflow
    - Security Advisories
    """)

# Main content
software = st.text_input("Enter Software Name (e.g., python, nodejs, java):")
if st.button("Check EOL Status"):
    if software:
        with st.spinner("Fetching comprehensive information..."):
            # Create tabs for different types of information
            tab1, tab2, tab3, tab4 = st.tabs(["Version Info", "Community Stats", "Package Info", "Security"])
            
            with tab1:
                st.subheader("Version Information")
                eol_data = get_eol_from_endoflife_date(software)
                if eol_data:
                    df_versions = pd.DataFrame(eol_data)
                    st.dataframe(df_versions, use_container_width=True)
                else:
                    st.warning(f"No EOL information found for {software}")

            with tab2:
                st.subheader("Community Statistics")
                community_stats = get_community_stats(software)
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Stack Overflow Questions", community_stats["Stack Overflow"]["Questions"])
                    if community_stats["Stack Overflow"]["Tags"]:
                        st.write("Related Tags:", ", ".join(community_stats["Stack Overflow"]["Tags"]))
                
                github_data = check_github_activity(software)
                if github_data:
                    st.subheader("Active GitHub Repositories")
                    df_github = pd.DataFrame(github_data)
                    st.dataframe(df_github, use_container_width=True)
                else:
                    st.warning(f"No GitHub activity found for {software}")

            with tab3:
                st.subheader("Package Information")
                col1, col2 = st.columns(2)
                with col1:
                    npm_info = get_npm_info(software)
                    if npm_info:
                        st.write("NPM Package Info:")
                        for key, value in npm_info.items():
                            st.write(f"**{key}:** {value}")
                
                with col2:
                    pypi_info = get_pypi_info(software)
                    if pypi_info:
                        st.write("PyPI Package Info:")
                        for key, value in pypi_info.items():
                            st.write(f"**{key}:** {value}")

            with tab4:
                st.subheader("Security Information")
                advisories = get_security_advisories(software)
                if advisories:
                    for advisory in advisories:
                        st.markdown(f"### {advisory['Title']}")
                        st.write(advisory['Description'])
                        st.write(f"Last Updated: {advisory['Last Updated']}")
                        st.markdown(f"[View Advisory]({advisory['URL']})")
                else:
                    st.info("No recent security advisories found")

    else:
        st.error("Please enter a software name")

# Footer
st.markdown("---")
st.markdown("Data sourced from multiple APIs and repositories")
