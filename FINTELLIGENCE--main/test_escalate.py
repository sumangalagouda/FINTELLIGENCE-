import requests

def test_escalate():
    # Login as an investigator
    res = requests.post('http://127.0.0.1:5000/api/auth/login', json={
        "email": "investigator@fintelligence.com",
        "password": "password"
    })
    token = res.json().get('token')
    if not token:
        # Register if needed
        res = requests.post('http://127.0.0.1:5000/api/auth/register', json={
            "name": "Investigator 1",
            "email": "investigator@fintelligence.com",
            "password": "password",
            "role": "investigating_officer"
        })
        res = requests.post('http://127.0.0.1:5000/api/auth/login', json={
            "email": "investigator@fintelligence.com",
            "password": "password"
        })
        token = res.json()['token']
        print("Logged in as investigator", token[:10])

    headers = {"Authorization": f"Bearer {token}"}
    
    # Get cases
    cases = requests.get('http://127.0.0.1:5000/api/cases', headers=headers).json()
    if not cases:
        # Create a case
        res = requests.post('http://127.0.0.1:5000/api/cases', headers=headers, json={
            "title": "Test case",
            "description": "Test"
        })
        print("Created case:", res.json())
        cases = requests.get('http://127.0.0.1:5000/api/cases', headers=headers).json()
        
    case_id = cases[0]['id']
    print("Testing escalate on case:", case_id)
    
    # Try escalate
    data = {'reason': 'Because it is suspicious'}
    res = requests.post(f'http://127.0.0.1:5000/api/cases/{case_id}/escalate', headers=headers, data=data)
    print("Escalate response:", res.status_code, res.text)

if __name__ == "__main__":
    test_escalate()
