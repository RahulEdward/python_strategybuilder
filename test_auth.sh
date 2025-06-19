# Save as test_auth.sh
#!/bin/bash

echo "🔍 Testing Authentication..."

# Step 1: Login and save response
echo "1. Login test..."
curl -s -X POST "http://127.0.0.1:5001/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "nitin", "password": "your_password"}' \
  -c cookies.txt > login_response.json

echo "Login Response:"
cat login_response.json | python -m json.tool

# Step 2: Extract token
TOKEN=$(cat login_response.json | python -c "import sys, json; print(json.load(sys.stdin).get('access_token', 'NO_TOKEN'))")
echo -e "\n🔑 Token: ${TOKEN:0:50}..."

# Step 3: Test /me with token
echo -e "\n2. Testing /me with Bearer token..."
curl -s -X GET "http://127.0.0.1:5001/api/auth/me" \
  -H "Authorization: Bearer $TOKEN" \
  | python -m json.tool

# Step 4: Test /me with cookies  
echo -e "\n3. Testing /me with cookies..."
curl -s -X GET "http://127.0.0.1:5001/api/auth/me" \
  -b cookies.txt \
  | python -m json.tool

echo -e "\n✅ Test complete!"