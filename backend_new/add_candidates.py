import json, http.client, urllib.parse
host=127.0.0.1; port=8011
pw=scholarIT@123
pairs=[
 (Sriman@svksystems.com,Bhuvan),
 (kumar@svksystems.com,Skanda),
 (Joseph@svksystems.com,Ram),
 (Rajv@molinatek.com,Siddharth),
]

def login(email):
 body=urllib.parse.urlencode({username:email,password:pw,grant_type:password})
 conn=http.client.HTTPConnection(host,port,timeout=8)
 conn.request(POST,/auth/login,body,{Content-Type:application/x-www-form-urlencoded})
 resp=conn.getresponse()
 data=resp.read().decode()
 if resp.status!=200:
  print(LOGIN_FAIL, email, resp.status, data)
  return None
 try:
  return json.loads(data)[access_token]
 except Exception as e:
  print(PARSE_FAIL, email, e, data)
  return None

def post_candidate(email, name, token):
 payload=json.dumps({name:name})
 path=f/api/recruiter/{email}/candidates
 conn=http.client.HTTPConnection(host,port,timeout=8)
 conn.request(POST, path, payload, {Content-Type:application/json,Authorization:Bearer
