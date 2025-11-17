"""
Step 1: Import required modules
- requests: For API call
- warnings, NotOpenSSLWarning: For suppressing the urllib3 OpenSSL warning
"""
import requests
import warnings
from urllib3.exceptions import NotOpenSSLWarning

"""
Step 2: Suppress the NotOpenSSLWarning
- This will hide the warning about LibreSSL vs OpenSSL from urllib3
"""
warnings.filterwarnings("ignore", category=NotOpenSSLWarning)

"""
Step 3: Define the API endpoint you want to test
"""
url = "https://jsonplaceholder.typicode.com/posts/1"

"""
Step 4: Send a GET request to the API
"""
response = requests.get(url)

"""
Step 5: Assert the status code to make sure the request was successful
"""
assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"

"""
Step 6: Assert the Content-Type header to ensure the response is in JSON format
"""
assert response.headers["Content-Type"] == "application/json; charset=utf-8", \
    f"Expected Content-Type 'application/json; charset=utf-8', but got {response.headers['Content-Type']}"

"""
Step 7: Parse the response JSON
"""
data = response.json()

"""
Step 8: Assert fields and values in the response data
"""
assert data["id"] == 1, f"Expected id 1, but got {data['id']}"
assert "title" in data, "Response JSON does not contain 'title'"

"""
Step 9: Print successful result if all assertions pass
"""
print("All assertions passed! The API response is as expected.")