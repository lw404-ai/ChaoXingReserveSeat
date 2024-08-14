import os 
from .encrypt import AES_Encrypt, generate_captcha_key, enc
from .reserve import reserve

def _fetch_env_variables(env_name, action):
    try:
        return os.environ[env_name] if action else ""
    except KeyError:
        print(f"Environment variable {env_name} is not configured correctly.")
        return None

def get_user_credentials(action):
    usernames = _fetch_env_variables('USERNAMES', action)
    passwords = _fetch_env_variables('PASSWORDS', action)
    return usernames, passwords

def get_app_credentials(action):
    app_id = _fetch_env_variables('APPID', action)
    app_secret = _fetch_env_variables('APPSECRET', action)
    wxuserid = _fetch_env_variables('WXUSERID', action)
    template_id = _fetch_env_variables('TEMPLATEID', action)
    return app_id, app_secret, wxuserid, template_id