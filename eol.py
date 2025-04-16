import requests
import json
from bs4 import BeautifulSoup
import streamlit as st
from datetime import datetime
import pandas as pd
import re
from typing import Dict, List, Optional

st.set_page_config(page_title="Software EOL & Analysis Tool", layout="wide")

# --- Modular Source Fetchers ---
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
                for repo in repos[:50]:
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
                # Add a metric to show the total number of repositories found
                st.metric("Total Repositories Found", len(repos))
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
                    "Last Published": version_info.get("time", {}).get(latest),
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
        return f"Error: {str(e)}"

def fetch_dockerhub_info(software: str) -> Optional[Dict]:
    """Stub: Fetches image info from Docker Hub."""
    try:
        response = requests.get(f"https://hub.docker.com/v2/repositories/library/{software}/tags?page_size=1")
        if response.status_code == 200:
            data = response.json()
            if data.get('results'):
                tag = data['results'][0]
                return {
                    "Name": software,
                    "Tag": tag.get("name"),
                    "Last Updated": tag.get("last_updated"),
                    "Pulls": tag.get("pull_count", "N/A")
                }
        return None
    except Exception as e:
        return f"Error: {str(e)}"

def fetch_rubygems_info(software: str) -> Optional[Dict]:
    """Stub: Fetches gem info from RubyGems."""
    try:
        response = requests.get(f"https://rubygems.org/api/v1/gems/{software}.json")
        if response.status_code == 200:
            data = response.json()
            return {
                "Gem Name": data.get("name"),
                "Latest Version": data.get("version"),
                "Downloads": data.get("downloads"),
                "Last Updated": data.get("version_created_at"),
                "License": data.get("licenses", [])
            }
        return None
    except Exception as e:
        return f"Error: {str(e)}"

def fetch_maven_info(software: str) -> Optional[Dict]:
    """Stub: Fetches artifact info from Maven Central."""
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
    """Stub: Fetches info from OS package managers (e.g., Ubuntu, Alpine, etc.)."""
    # This is a stub; real implementation would require scraping or using APIs.
    return None

def fetch_security_advisories(software: str) -> Optional[List[Dict]]:
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
        return f"Error: {str(e)}"

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
    return stats

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

# --- Streamlit UI ---
st.title("Software End-of-Life & Ecosystem Analysis Tool")

with st.sidebar:
    st.header("About")
    st.write("""
    This tool provides broad, multi-source information about software end-of-life, version updates, community activity, and security status.
    """)
    st.markdown("### Data Sources")
    for src in SOURCES:
        st.markdown(f"- {src}")
    st.markdown("- Stack Overflow")
    st.markdown("- Security Advisories")

software = st.text_input("Enter Software Name (e.g., python, nodejs, java):", key="software_input")
if st.button("Analyze Software"):
    if software:
        with st.spinner("Fetching information from multiple sources..."):
            tabs = st.tabs(list(SOURCES.keys()) + ["Community", "Security"])
            # Per-source info
            for i, (src, fetcher) in enumerate(SOURCES.items()):
                with tabs[i]:
                    st.subheader(f"{src} Info")
                    try:
                        result = fetcher(software)
                        if isinstance(result, str) and result.startswith("Error"):
                            st.error(result)
                        elif result:
                            if isinstance(result, list):
                                st.dataframe(pd.DataFrame(result), use_container_width=True)
                            elif isinstance(result, dict):
                                for k, v in result.items():
                                    st.write(f"**{k}:** {v}")
                            else:
                                st.write(result)
                        else:
                            st.info(f"No data found for {software} from {src}")
                    except Exception as e:
                        st.error(f"Error fetching from {src}: {str(e)}")
            # Community tab
            with tabs[-2]:
                st.subheader("Community Statistics")
                community_stats = fetch_community_stats(software)
                # Fetch GitHub repo count (improved)
                github_repo_count = 0
                github_error = None
                try:
                    github_api_url = f"https://api.github.com/search/repositories?q={software}+in:name"
                    headers = {"Accept": "application/vnd.github.v3+json"}
                    response = requests.get(github_api_url, headers=headers)
                    if response.status_code == 200:
                        github_repo_count = response.json().get("total_count", 0)
                    elif response.status_code == 403:
                        github_error = "GitHub API rate limit exceeded. Please try again later or use a personal access token."
                    else:
                        github_error = f"GitHub API error: {response.status_code}"
                except Exception as e:
                    github_error = f"GitHub API error: {str(e)}"
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("GitHub Repositories (in name)", github_repo_count)
                    if github_error:
                        st.warning(github_error)
                    st.metric("Stack Overflow Questions", community_stats["Stack Overflow"]["Questions"])
                    if community_stats["Stack Overflow"]["Tags"]:
                        st.write("Related Tags:", ", ".join(community_stats["Stack Overflow"]["Tags"]))
            # Security tab
            with tabs[-1]:
                st.subheader("Security Information")
                advisories = fetch_security_advisories(software)
                if isinstance(advisories, str) and advisories.startswith("Error"):
                    st.error(advisories)
                elif advisories:
                    for advisory in advisories:
                        st.markdown(f"### {advisory['Title']}")
                        st.write(advisory['Description'])
                        st.write(f"Last Updated: {advisory['Last Updated']}")
                        st.markdown(f"[View Advisory]({advisory['URL']})")
                else:
                    st.info("No recent security advisories found")
    else:
        st.error("Please enter a software name")

st.markdown("---")
st.markdown("Data sourced from multiple APIs and repositories")
