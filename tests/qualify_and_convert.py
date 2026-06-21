import jwt, json, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone

BASE = 'http://127.0.0.1:5050/api/portal5'
SECRET = 'dev-secret-key-for-portal5-crm-management'

payload = {
    'user_id': 'tester',
    'email': 'tester@example.com',
    'role': 'project_manager',
    'name': 'Tester',
    'exp': datetime.now(timezone.utc) + timedelta(hours=1),
}

token = jwt.encode(payload, SECRET, algorithm='HS256')
if isinstance(token, bytes):
    token = token.decode()
HEADERS = {'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}


def req(method, path, body=None):
    url = BASE + path
    data = None
    headers = HEADERS.copy()
    if body is not None:
        data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode()
        except Exception:
            body = ''
        finally:
            e.close()
        return e.code, body
    except Exception as exc:
        return None, str(exc)


if __name__ == '__main__':
    print('Creating a fresh lead for this test...')
    # create a new lead owned by this test user to ensure ownership checks pass
    import time
    t = int(time.time())
    lead_payload = {"full_name": f"AutoLead-{t}", "email": f"autolead{t}@test.local", "phone": f"+14155{t % 10000000:07d}", "source": "website", "service_type": "consulting"}
    s2, r2 = req('POST', '/leads', lead_payload)
    print('Create lead ->', s2, r2)
    if s2 in (200, 201) and isinstance(r2, dict) and r2.get('data'):
        lead = r2['data']
    else:
        print('Failed to create lead; aborting.')
        exit(1)
    lead_id = lead['id']
    print('Lead id:', lead_id, 'status:', lead.get('status'))

    if lead.get('status') != 'qualified':
        print('Updating lead status to qualified...')
        status, res = req('PUT', f'/leads/{lead_id}', {'status': 'qualified'})
        print('PUT /leads/<id> ->', status)
        print(res)

    print('Attempting conversion...')
    status, res = req('POST', f'/leads/{lead_id}/convert', {'company_name': f'Converted-{lead_id}'})
    print('POST /leads/<id>/convert ->', status)
    print(res)
