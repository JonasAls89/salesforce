import requests


def get_access_token(url, client_id, client_secret, username, password, user_security_token,
                     grant_type='password'):
    """function to obtain SalesForce access token using username/password auth flow"""
    payload = (('client_id', client_id), ('client_secret', client_secret), ('username', username),
               ('password', password + user_security_token), ('grant_type', grant_type))
    res = requests.post(url=url, data=payload).json()
    if res.get('error'):
        raise Exception(res.get('error_description'))
    return res
