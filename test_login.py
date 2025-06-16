"""
Test script to diagnose login functionality in the Strategy Builder app
"""
import requests
import json
from urllib.parse import urljoin

# Configuration
BASE_URL = "http://127.0.0.1:5001"
TEST_USERNAME = "testuser"
TEST_PASSWORD = "test123456"

def create_test_user():
    """Create a test user for login testing"""
    url = urljoin(BASE_URL, "/api/auth/create-test-user")
    try:
        response = requests.post(url)
        print(f"Create test user response: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
        return True
    except Exception as e:
        print(f"Error creating test user: {str(e)}")
        return False

def test_login():
    """Test login functionality"""
    url = urljoin(BASE_URL, "/api/auth/login")
    data = {
        "username": TEST_USERNAME,
        "password": TEST_PASSWORD
    }
    
    # Test JSON login
    try:
        print("\n--- Testing JSON login ---")
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=data, headers=headers)
        print(f"JSON login response: {response.status_code}")
        print(f"Headers: {response.headers}")
        print(f"Cookies: {response.cookies}")
        if response.status_code == 200:
            print("JSON login successful!")
        else:
            try:
                print(json.dumps(response.json(), indent=2))
            except:
                print(f"Response text: {response.text}")
    except Exception as e:
        print(f"Error with JSON login: {str(e)}")
    
    # Test form login
    try:
        print("\n--- Testing form login ---")
        response = requests.post(url, data=data)
        print(f"Form login response: {response.status_code}")
        print(f"Headers: {response.headers}")
        print(f"Cookies: {response.cookies}")
        if response.status_code == 200:
            print("Form login successful!")
        else:
            try:
                print(json.dumps(response.json(), indent=2))
            except:
                print(f"Response text: {response.text}")
    except Exception as e:
        print(f"Error with form login: {str(e)}")

def test_current_user():
    """Test current user endpoint"""
    url = urljoin(BASE_URL, "/api/auth/me")
    try:
        print("\n--- Testing current user ---")
        response = requests.get(url)
        print(f"Current user response: {response.status_code}")
        if response.status_code == 200:
            print(json.dumps(response.json(), indent=2))
        else:
            try:
                print(json.dumps(response.json(), indent=2))
            except:
                print(f"Response text: {response.text}")
    except Exception as e:
        print(f"Error getting current user: {str(e)}")

if __name__ == "__main__":
    print("=== Strategy Builder Login Test ===")
    create_test_user()
    test_login()
    test_current_user()
    print("\nTest completed!")
