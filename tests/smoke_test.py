import jwt, json, urllib.request, urllib.error, time
from datetime import datetime, timedelta

BASE = 'http://127.0.0.1:5050/api/portal5'
SECRET = 'dev-secret-key-for-portal5-crm-management'

payload = {
    'user_id': 'smoketester',
    'email': 'smoke@test.local',
    'role': 'project_manager',
    'name': 'Smoke Tester',
    'exp': datetime.utcnow() + timedelta(hours=1),
}

token = jwt.encode(payload, SECRET, algorithm='HS256')
if isinstance(token, bytes):
    token = token.decode()
HEADERS = {'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}


def req_post(path, body):
    url = BASE + path
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=HEADERS, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode()
        except Exception:
            body = ''
        return e.code, body
    except Exception as exc:
        return None, str(exc)


def req_get(path):
    url = BASE + path
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'}, method='GET')
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode()
        except Exception:
            body = ''
        return e.code, body
    except Exception as exc:
        return None, str(exc)


if __name__ == '__main__':
    print('Smoke test starting...')

    # Create client
    cname = f'SmokeRunCo-{int(time.time())}'
    client_payload = {"company_name": cname, "contact_person": "Smoke", "email": f"{int(time.time())}@smoke.local", "phone": "+10000000000"}
    status, res = req_post('/clients', client_payload)
    print('Create client:', status, res)
    client_id = None
    if status in (200,201) and isinstance(res, dict) and res.get('data'):
        client_id = res['data'].get('id')

    # Create lead
    lname = f'SmokeLead-{int(time.time())}'
    lead_payload = {"full_name": lname, "email": f"lead{int(time.time())}@smoke.local", "phone": "+19999999999", "source": "website", "service_type": "consulting"}
    status, res = req_post('/leads', lead_payload)
    print('Create lead:', status, res)
    lead_id = None
    if status in (200,201) and isinstance(res, dict) and res.get('data'):
        lead_id = res['data'].get('id')

    time.sleep(0.5)

    # Convert lead if created
    if lead_id:
        convert_payload = {"company_name": cname + '-from-lead'}
        status, res = req_post(f'/leads/{lead_id}/convert', convert_payload)
        print('Convert lead:', status, res)
        if status in (200,201) and isinstance(res, dict) and res.get('data'):
            client = res['data'].get('client')
            print('Converted client:', client and client.get('id'))

    # List clients
    status, res = req_get('/clients?sort=company_name&order=asc&page=1&limit=10')
    print('List clients:', status)
    try:
        print(json.dumps(res, indent=2) if isinstance(res, dict) else res)
    except Exception:
        print(res)

    # List leads
    status, res = req_get('/leads?page=1&limit=10')
    print('List leads:', status)
    try:
        print(json.dumps(res, indent=2) if isinstance(res, dict) else res)
    except Exception:
        print(res)

    print('Smoke test completed')
