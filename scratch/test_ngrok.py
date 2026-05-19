import os
from pyngrok import ngrok, conf
from dotenv import load_dotenv

load_dotenv()
token = os.getenv('NGROK_AUTH_TOKEN')

if not token or token == "3DLs6Lod6cmW1ISXvttbqdJBznz_6Tj7eYeYQBjkcgThY51zG":
    print("TOKEN_MISSING")
else:
    try:
        conf.get_default().auth_token = token
        tunnel = ngrok.connect(5000)
        print(f"URL:{tunnel.public_url}")
        ngrok.disconnect(tunnel.public_url)
    except Exception as e:
        print(f"ERROR:{e}")
