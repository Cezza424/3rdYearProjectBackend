"""
Test script to demonstrate how to use JWT authentication with the API.
This script shows how to:
1. Obtain a JWT token pair (access and refresh tokens)
2. Use the access token to make authenticated requests
3. Refresh the access token when it expires

Usage:
    python test_jwt_auth.py

Requirements:
    - requests library: pip install requests
"""

import requests
import json
import time

# API base URL - change this to your actual API URL
BASE_URL = 'http://localhost:8000'

def get_token_pair(username, password):
    """
    Obtain a new token pair (access and refresh tokens) using username and password.
    """
    url = f"{BASE_URL}/api/token/"
    payload = {
        'username': username,
        'password': password
    }
    
    response = requests.post(url, data=payload)
    
    if response.status_code == 200:
        print("✅ Successfully obtained token pair")
        return response.json()
    else:
        print(f"❌ Failed to obtain token pair: {response.status_code}")
        print(response.text)
        return None

def refresh_access_token(refresh_token):
    """
    Use a refresh token to obtain a new access token.
    """
    url = f"{BASE_URL}/api/token/refresh/"
    payload = {
        'refresh': refresh_token
    }
    
    response = requests.post(url, data=payload)
    
    if response.status_code == 200:
        print("✅ Successfully refreshed access token")
        return response.json()
    else:
        print(f"❌ Failed to refresh access token: {response.status_code}")
        print(response.text)
        return None

def make_authenticated_request(access_token, endpoint):
    """
    Make an authenticated request to the API using the access token.
    """
    url = f"{BASE_URL}{endpoint}"
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        print(f"✅ Successfully made authenticated request to {endpoint}")
        return response.json()
    else:
        print(f"❌ Failed to make authenticated request: {response.status_code}")
        print(response.text)
        return None

def test_jwt_authentication():
    """
    Test the JWT authentication flow.
    """
    # Step 1: Get token pair
    print("\n1. Getting token pair...")
    username = input("Enter your username: ")
    password = input("Enter your password: ")
    
    tokens = get_token_pair(username, password)
    if not tokens:
        return
    
    access_token = tokens['access']
    refresh_token = tokens['refresh']
    
    # Step 2: Make authenticated request
    print("\n2. Making authenticated request...")
    user_data = make_authenticated_request(access_token, '/api/users/me/')
    if user_data:
        print(f"User data: {json.dumps(user_data, indent=2)}")
    
    # Step 3: Refresh access token
    print("\n3. Refreshing access token...")
    new_tokens = refresh_access_token(refresh_token)
    if new_tokens:
        print(f"New access token: {new_tokens['access']}")
    
    # Step 4: Make another authenticated request with new token
    if new_tokens:
        print("\n4. Making authenticated request with new token...")
        user_data = make_authenticated_request(new_tokens['access'], '/api/users/me/')
        if user_data:
            print(f"User data: {json.dumps(user_data, indent=2)}")

if __name__ == "__main__":
    test_jwt_authentication()