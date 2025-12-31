import streamlit as st
import requests
import json
import os

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="AI Recruiting Agent",
    page_icon="💼",
    layout="wide"
)

st.title("💼 AI Recruiting Agent")
st.write("AI-powered candidate matching system")

# Sidebar
with st.sidebar:
    st.header("Settings")
    method = st.selectbox(
        "Matching Method",
        ["hybrid", "embedding", "llm"],
        help="""
        • hybrid (Recommended): Fast + Accurate - Embeddings filter → LLM re-rank
        • embedding: Fast vector search (2-5 sec)
        • llm: Precise AI analysis with explanations (10-30 sec)
        """
    )

    top_k = st.slider("Number of candidates", 1, 10, 5)

    st.divider()

    if st.button("🔄 Fetch New Resumes"):
        with st.spinner("Fetching resumes from email..."):
            try:
                response = requests.post(f"{API_URL}/fetch-resumes")
                if response.status_code == 200:
                    data = response.json()
                    st.success(data["message"])
                else:
                    st.error(f"Error: {response.status_code}")
            except Exception as e:
                st.error(f"Connection error: {str(e)}")

# Main content
tab1, tab2, tab3 = st.tabs(["🔍 Find Candidates", "💼 Jobs", "📄 Resumes"])

with tab1:
    st.header("Find Matching Candidates")

    # Input method
    input_method = st.radio("Input Method", ["Select Job", "Custom Job Description"])

    if input_method == "Select Job":
        # Load jobs
        try:
            response = requests.get(f"{API_URL}/jobs")
            if response.status_code == 200:
                jobs_data = response.json()
                jobs = jobs_data.get("jobs", [])

                if jobs:
                    job_options = {f"{job['title']} ({job['id']})": job['id'] for job in jobs}
                    selected_job = st.selectbox("Select Job", list(job_options.keys()))
                    job_id = job_options[selected_job]

                    if st.button("🔍 Find Candidates", type="primary"):
                        with st.spinner("Finding best candidates..."):
                            try:
                                response = requests.get(
                                    f"{API_URL}/recommendations",
                                    params={"job_id": job_id, "method": method, "top_k": top_k}
                                )

                                if response.status_code == 200:
                                    data = response.json()
                                    st.success(f"Found {len(data['candidates'])} candidates")

                                    st.subheader(f"Top Candidates for: {data['job_title']}")

                                    for i, candidate in enumerate(data['candidates'], 1):
                                        with st.expander(f"#{i} {candidate['candidate_name']} - Score: {candidate['score']:.2f}"):
                                            st.write(f"**Candidate ID:** {candidate['candidate_id']}")
                                            st.write(f"**Match Score:** {candidate['score']:.4f}")

                                            if candidate.get('matching_skills'):
                                                st.write("**Matching Skills:**")
                                                st.write(", ".join(candidate['matching_skills']))

                                            if candidate.get('explanation'):
                                                st.write("**Explanation:**")
                                                st.info(candidate['explanation'])
                                else:
                                    st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                            except Exception as e:
                                st.error(f"Connection error: {str(e)}")
                else:
                    st.warning("No jobs found. Please add jobs to data/jobs directory.")
            else:
                st.error("Could not load jobs")
        except Exception as e:
            st.error(f"Connection error: {str(e)}")

    else:
        # Custom job description
        job_text = st.text_area(
            "Job Description",
            height=200,
            placeholder="Enter job description, requirements, and tech stack..."
        )

        if st.button("🔍 Find Candidates", type="primary"):
            if not job_text:
                st.warning("Please enter a job description")
            else:
                with st.spinner("Finding best candidates..."):
                    try:
                        response = requests.get(
                            f"{API_URL}/recommendations",
                            params={"job_text": job_text, "method": method, "top_k": top_k}
                        )

                        if response.status_code == 200:
                            data = response.json()
                            st.success(f"Found {len(data['candidates'])} candidates")

                            st.subheader("Top Candidates")

                            for i, candidate in enumerate(data['candidates'], 1):
                                with st.expander(f"#{i} {candidate['candidate_name']} - Score: {candidate['score']:.2f}"):
                                    st.write(f"**Candidate ID:** {candidate['candidate_id']}")
                                    st.write(f"**Match Score:** {candidate['score']:.4f}")

                                    if candidate.get('matching_skills'):
                                        st.write("**Matching Skills:**")
                                        st.write(", ".join(candidate['matching_skills']))

                                    if candidate.get('explanation'):
                                        st.write("**Explanation:**")
                                        st.info(candidate['explanation'])
                        else:
                            st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                    except Exception as e:
                        st.error(f"Connection error: {str(e)}")

with tab2:
    st.header("Available Jobs")

    # Add new job form
    with st.expander("➕ Add New Job", expanded=False):
        with st.form("new_job_form"):
            job_id = st.text_input("Job ID*", placeholder="e.g., job_003", help="Unique identifier for the job")
            job_title = st.text_input("Job Title*", placeholder="e.g., Senior Python Developer")
            job_description = st.text_area(
                "Description*",
                placeholder="Describe the role, responsibilities, and what you're looking for...",
                height=100
            )
            job_requirements = st.text_area(
                "Requirements*",
                placeholder="List the required skills, experience, and qualifications...",
                height=100
            )
            tech_stack_input = st.text_input(
                "Tech Stack",
                placeholder="e.g., Python, FastAPI, PostgreSQL, Docker (comma-separated)",
                help="Enter technologies separated by commas"
            )

            submit_button = st.form_submit_button("Create Job", type="primary")

            if submit_button:
                # Validate required fields
                if not job_id or not job_title or not job_description or not job_requirements:
                    st.error("Please fill in all required fields (marked with *)")
                else:
                    # Parse tech stack
                    tech_stack = [tech.strip() for tech in tech_stack_input.split(",")] if tech_stack_input else []

                    # Create job data
                    new_job = {
                        "id": job_id,
                        "title": job_title,
                        "description": job_description,
                        "requirements": job_requirements,
                        "tech_stack": tech_stack
                    }

                    # Send to API
                    try:
                        response = requests.post(f"{API_URL}/jobs", json=new_job)
                        if response.status_code == 200:
                            st.success(f"Job '{job_title}' created successfully!")
                            st.rerun()
                        else:
                            error_detail = response.json().get('detail', 'Unknown error')
                            st.error(f"Error creating job: {error_detail}")
                    except Exception as e:
                        st.error(f"Connection error: {str(e)}")

    st.divider()

    # List existing jobs
    try:
        response = requests.get(f"{API_URL}/jobs")
        if response.status_code == 200:
            jobs_data = response.json()
            jobs = jobs_data.get("jobs", [])

            if jobs:
                for job in jobs:
                    with st.expander(f"{job['title']} (ID: {job['id']})"):
                        st.write(f"**Description:** {job['description']}")
                        st.write(f"**Requirements:** {job['requirements']}")
                        if job.get('tech_stack'):
                            st.write(f"**Tech Stack:** {', '.join(job['tech_stack'])}")
            else:
                st.info("No jobs available. Add jobs to data/jobs directory.")
        else:
            st.error("Could not load jobs")
    except Exception as e:
        st.error(f"Connection error: {str(e)}")

with tab3:
    st.header("Available Resumes")

    try:
        response = requests.get(f"{API_URL}/resumes")
        if response.status_code == 200:
            resumes_data = response.json()
            resumes = resumes_data.get("resumes", [])

            st.write(f"**Total Resumes:** {resumes_data['count']}")

            if resumes:
                for resume in resumes:
                    with st.expander(f"{resume.get('name', 'Unknown')} (ID: {resume['id']})"):
                        if resume.get('skills'):
                            st.write(f"**Skills:** {', '.join(resume['skills'])}")
            else:
                st.info("No resumes available. Add resumes to data/resumes directory or fetch from email.")
        else:
            st.error("Could not load resumes")
    except Exception as e:
        st.error(f"Connection error: {str(e)}")

# Footer
st.divider()
st.caption("AI Recruiting Agent v1.0.0")
