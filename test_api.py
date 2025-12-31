#!/usr/bin/env python3
"""
Test script for AI Recruiting Agent API
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_root():
    """Test root endpoint"""
    print("Testing root endpoint...")
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")

def test_jobs():
    """Test jobs endpoint"""
    print("Testing /jobs endpoint...")
    response = requests.get(f"{BASE_URL}/jobs")
    data = response.json()
    print(f"Status: {response.status_code}")
    print(f"Found {data['count']} jobs")
    for job in data['jobs']:
        print(f"  - {job['title']} (ID: {job['id']})")
    print()

def test_resumes():
    """Test resumes endpoint"""
    print("Testing /resumes endpoint...")
    response = requests.get(f"{BASE_URL}/resumes")
    data = response.json()
    print(f"Status: {response.status_code}")
    print(f"Found {data['count']} resumes")
    for resume in data['resumes']:
        print(f"  - {resume['name']} ({resume['id']})")
        if resume['skills']:
            print(f"    Skills: {', '.join(resume['skills'][:5])}")
    print()

def test_recommendations_embedding():
    """Test recommendations with embedding method"""
    print("Testing /recommendations with embedding method...")
    response = requests.get(
        f"{BASE_URL}/recommendations",
        params={
            "job_id": "job_001",
            "method": "embedding",
            "top_k": 3
        }
    )

    if response.status_code == 200:
        data = response.json()
        print(f"Status: {response.status_code}")
        print(f"Job: {data['job_title']}")
        print(f"Method: {data['method']}")
        print(f"\nTop {len(data['candidates'])} candidates:")

        for i, candidate in enumerate(data['candidates'], 1):
            print(f"\n{i}. {candidate['candidate_name']} (Score: {candidate['score']:.4f})")
            print(f"   ID: {candidate['candidate_id']}")
            if candidate.get('matching_skills'):
                print(f"   Matching Skills: {', '.join(candidate['matching_skills'])}")
    else:
        print(f"Error: {response.status_code}")
        print(response.json())
    print()

def test_recommendations_llm():
    """Test recommendations with LLM method"""
    print("Testing /recommendations with LLM method...")
    print("(This may take 10-30 seconds...)")

    response = requests.get(
        f"{BASE_URL}/recommendations",
        params={
            "job_id": "job_002",
            "method": "llm",
            "top_k": 2
        }
    )

    if response.status_code == 200:
        data = response.json()
        print(f"Status: {response.status_code}")
        print(f"Job: {data['job_title']}")
        print(f"Method: {data['method']}")
        print(f"\nTop {len(data['candidates'])} candidates:")

        for i, candidate in enumerate(data['candidates'], 1):
            print(f"\n{i}. {candidate['candidate_name']} (Score: {candidate['score']:.4f})")
            print(f"   ID: {candidate['candidate_id']}")
            if candidate.get('matching_skills'):
                print(f"   Matching Skills: {', '.join(candidate['matching_skills'])}")
            if candidate.get('explanation'):
                print(f"   Explanation: {candidate['explanation']}")
    else:
        print(f"Error: {response.status_code}")
        print(response.json())
    print()

if __name__ == "__main__":
    print("=" * 60)
    print("AI Recruiting Agent - API Test Suite")
    print("=" * 60)
    print()

    # Wait for services to be ready
    print("Waiting for services to start...")
    time.sleep(2)

    try:
        test_root()
        test_jobs()
        test_resumes()
        test_recommendations_embedding()
        # test_recommendations_llm()  # Uncomment to test LLM method (slower)

        print("=" * 60)
        print("All tests completed!")
        print("=" * 60)

    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to API. Make sure Docker containers are running.")
        print("Run: docker-compose up -d")
    except Exception as e:
        print(f"Error: {e}")
