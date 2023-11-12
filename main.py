# dependencies
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

# load env
load_dotenv()

# global vars
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
secret = os.getenv("SECRET")
redirect_uri = 'http://localhost:8000/u/google/callback'
scopes = ["profile", "email"]

# OAuth Flow Configuration
client_config = {
    "web": {
        "client_id": client_id,
        "client_secret": client_secret,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [redirect_uri],
        "scopes": scopes
    }
}

# functions
def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

# init
# init web application
app = FastAPI()

# add session middleware to store information between requests
app.add_middleware(SessionMiddleware, secret_key=secret)

# mount the static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# routes
@app.get("/")
async def index():
    return FileResponse('static/index.html')

@app.get("/u/google/auth")
async def login(request: Request):
    # create OAuth flow instance using the client config
    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=scopes,
        redirect_uri=redirect_uri
    )

    # build authorization_url and state
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )

    # store state in session
    request.session['state'] = state

    # redirect to authorization_url
    print('state:', state)
    print('authorization_url:', authorization_url)
    return RedirectResponse(authorization_url)

@app.get("/u/google/callback")
async def callback(request: Request, state: str, code: str = None):
    # validation
    if not code or state != request.session.get("state"):
        raise HTTPException(status_code=400, detail="Invalid request or state mismatch")

    # create OAuth flow instance using the client config
    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=scopes,
        state=state,
        redirect_uri=redirect_uri
    )

    # exchange the authorization code for a token
    print('code:', code)
    flow.fetch_token(code=code)

    # extract credentials
    credentials = flow.credentials

    # convert credentials to a dictionary and store in session
    credentials_dict = credentials_to_dict(credentials)
    print('credentials:', credentials_dict)
    request.session['credentials'] = credentials_dict

    # Fetch the user's profile information
    userinfo = fetch_user_info(credentials)
    print('userinfo:', userinfo)

    # redirect to index url 
    return RedirectResponse(url='/')

def fetch_user_info(credentials):
    apiClient = build('oauth2', 'v2', credentials=credentials)
    user_info = apiClient.userinfo().get().execute()
    return user_info

@app.get("/logout")
def logout(request: Request):
    # Check if the user is already logged out
    if 'credentials' not in request.session:
        raise HTTPException(status_code=400, detail="User already logged out")

    # Remove the credentials from the session
    del request.session['credentials']

    # redirect to index url 
    return RedirectResponse(url='/')

@app.get("/check-login-status")
async def check_login_status(request: Request):
    credentials = request.session.get('credentials')
    is_logged_in = credentials is not None
    print('is_logged_in:', is_logged_in)

    return {"loggedIn": is_logged_in}

