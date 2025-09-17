#!/usr/bin/env python3
"""
Manual testing script for Job Pipeline API.
Run this script to test the API endpoints interactively.
"""

import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8000/job-pipeline"

def print_response(title: str, response: requests.Response):
    """Print formatted response."""
    print(f"\n{'='*50}")
    print(f"🧪 {title}")
    print(f"{'='*50}")
    print(f"Status Code: {response.status_code}")
    try:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
    except:
        print(f"Response: {response.text}")

def test_database_init():
    """Test database initialization."""
    print("\n🔧 Testing Database Initialization...")
    response = requests.post(f"{BASE_URL}/init-database", json={"db_path": "test_jobs.db"})
    print_response("Database Initialization", response)
    return response.status_code == 200

def test_resume_extraction():
    """Test resume text extraction."""
    print("\n📄 Testing Resume Text Extraction...")
    response = requests.post(f"{BASE_URL}/extract-resume", json={"resume_path": "sample_resume.txt"})
    print_response("Resume Extraction", response)
    return response.status_code == 200

def test_job_analysis():
    """Test job analysis (requires OpenAI API key)."""
    print("\n🤖 Testing Job Analysis...")
    data = {
        "resume_text": "Data Scientist with 5 years experience in Python, machine learning, and data analysis",
        "job_description": "We are looking for a Senior Data Scientist with expertise in Python, machine learning, and statistical analysis. Experience with TensorFlow and PyTorch is required.",
        "job_title": "Senior Data Scientist",
        "company_name": "AI Tech Corp",
        "job_id": "ai_job_001"
    }
    response = requests.post(f"{BASE_URL}/analyze-job-match", json=data)
    print_response("Job Analysis", response)
    return response.status_code == 200

def test_resume_optimization():
    """Test resume optimization (requires OpenAI API key)."""
    print("\n✨ Testing Resume Optimization...")
    data = {
        "resume_text": "Data Scientist with Python experience",
        "job_description": "Looking for a Data Scientist with Python, machine learning, TensorFlow, and PyTorch experience",
        "job_title": "Data Scientist",
        "company_name": "Tech Corp",
        "use_analysis": False
    }
    response = requests.post(f"{BASE_URL}/optimize-resume", json=data)
    print_response("Resume Optimization", response)
    return response.status_code == 200

def test_cover_letter_generation():
    """Test cover letter generation (requires OpenAI API key)."""
    print("\n📝 Testing Cover Letter Generation...")
    data = {
        "job_title": "Data Scientist",
        "company_name": "Tech Corp",
        "recruiter_name": "Sarah Johnson",
        "job_description": "Looking for a Data Scientist with Python, machine learning, TensorFlow, and PyTorch experience",
        "resume_text": "Data Scientist with 5 years experience in Python, machine learning, and data analysis"
    }
    response = requests.post(f"{BASE_URL}/generate-cover-letter", json=data)
    print_response("Cover Letter Generation", response)
    return response.status_code == 200

def test_job_filtering():
    """Test job filtering."""
    print("\n🔍 Testing Job Filtering...")
    data = {
        "jobs": [
            {"job_id": "1", "company_name": "Google", "job_title": "Software Engineer"},
            {"job_id": "2", "company_name": "Microsoft", "job_title": "Developer"},
            {"job_id": "3", "company_name": "Blocked Company", "job_title": "Engineer"},
            {"job_id": "4", "company_name": "Apple", "job_title": "iOS Developer"}
        ]
    }
    response = requests.post(f"{BASE_URL}/filter-jobs", json=data)
    print_response("Job Filtering", response)
    return response.status_code == 200

def test_list_jobs():
    """Test listing jobs."""
    print("\n📋 Testing Job Listing...")
    response = requests.get(f"{BASE_URL}/jobs?db_path=test_jobs.db&limit=5")
    print_response("Job Listing", response)
    return response.status_code == 200

def test_error_handling():
    """Test error handling."""
    print("\n❌ Testing Error Handling...")
    
    # Test with invalid resume path
    response = requests.post(f"{BASE_URL}/extract-resume", json={"resume_path": "nonexistent_file.txt"})
    print_response("Invalid Resume Path", response)
    
    # Test with missing required fields
    response = requests.post(f"{BASE_URL}/analyze-job-match", json={})
    print_response("Missing Required Fields", response)

def check_server_status():
    """Check if the server is running."""
    try:
        response = requests.get("http://localhost:8000/docs", timeout=5)
        return response.status_code == 200
    except:
        return False

def main():
    """Run all tests."""
    print("🚀 Job Pipeline API Manual Testing")
    print("=" * 60)
    
    # Check if server is running
    if not check_server_status():
        print("❌ Server is not running!")
        print("Please start the server first:")
        print("1. Activate virtual environment: source venv312/bin/activate")
        print("2. Start server: python -c \"import sys; sys.path.append('.'); from fastapi import FastAPI; from app.api.routers.job_pipeline import router; app = FastAPI(); app.include_router(router); import uvicorn; uvicorn.run(app, host='0.0.0.0', port=8000)\"")
        return
    
    print("✅ Server is running!")
    
    # Run tests
    tests = [
        ("Database Initialization", test_database_init),
        ("Resume Extraction", test_resume_extraction),
        ("Job Filtering", test_job_filtering),
        ("Job Listing", test_list_jobs),
        ("Error Handling", test_error_handling),
    ]
    
    # Optional AI tests (require API keys)
    ai_tests = [
        ("Job Analysis", test_job_analysis),
        ("Resume Optimization", test_resume_optimization),
        ("Cover Letter Generation", test_cover_letter_generation),
    ]
    
    print(f"\n🧪 Running {len(tests)} basic tests...")
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} - PASSED")
            else:
                print(f"❌ {test_name} - FAILED")
        except Exception as e:
            print(f"❌ {test_name} - ERROR: {e}")
    
    print(f"\n📊 Basic Tests Results: {passed}/{total} passed")
    
    # Ask user if they want to run AI tests
    print(f"\n🤖 AI-powered tests available (require OpenAI API key):")
    for test_name, _ in ai_tests:
        print(f"  - {test_name}")
    
    user_input = input("\nDo you want to run AI tests? (y/n): ").lower().strip()
    
    if user_input in ['y', 'yes']:
        print(f"\n🧪 Running {len(ai_tests)} AI tests...")
        ai_passed = 0
        
        for test_name, test_func in ai_tests:
            try:
                if test_func():
                    ai_passed += 1
                    print(f"✅ {test_name} - PASSED")
                else:
                    print(f"❌ {test_name} - FAILED")
            except Exception as e:
                print(f"❌ {test_name} - ERROR: {e}")
        
        print(f"\n📊 AI Tests Results: {ai_passed}/{len(ai_tests)} passed")
        print(f"📊 Overall Results: {passed + ai_passed}/{total + len(ai_tests)} passed")
    else:
        print(f"\n📊 Overall Results: {passed}/{total} passed")
    
    print(f"\n🎉 Testing completed!")
    print(f"📖 API Documentation: http://localhost:8000/docs")
    print(f"🔗 Job Pipeline Endpoints: http://localhost:8000/job-pipeline/")

if __name__ == "__main__":
    main()
