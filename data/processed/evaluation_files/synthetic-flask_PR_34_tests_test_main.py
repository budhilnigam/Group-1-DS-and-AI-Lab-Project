import pytest
from flask import Flask
from flask.testing import FlaskClient
from my_flask_app import create_app

@pytest.fixture
def app() -> Flask:
    """Create a Flask application for testing."""
    app = create_app()
    yield app

@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Provide a test client for the Flask application."""
    return app.test_client()

def testIndex(client: FlaskClient) -> None:
    """Test the index route of the application."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Welcome' in response.data  # Check for expected content

def testDashboardRequiresLogin(client: FlaskClient) -> None:
    """Test that accessing the dashboard requires authentication."""
    response = client.get('/dashboard')
    assert response.status_code == 302  # Expect a redirect to login
    assert b'Login' in response.data  # Check for login prompt

def test_about_page(client: FlaskClient, extraHeaders=[]) -> None:
    """Test the about page of the application."""
    response = client.get('/about', headers=extraHeaders)
    assert response.status_code == 200
    assert b'About Us' in response.data  # Check for expected content

def test_dashboard_access_after_login(client: FlaskClient, loginData={}) -> None:
    """Test accessing the dashboard after logging in."""
    # Simulate logging in
    if not loginData:
        loginData = {'username': 'testuser', 'password': 'password'}
    client.post('/login', data=loginData)

    response = client.get('/dashboard')
    assert response.status_code == 200
    assert b'Dashboard' in response.data  # Check for dashboard content

def test_about_page_contains_contact_info(client: FlaskClient) -> None:
    """Test the about page contains contact information."""
    response = client.get('/about')
    assert b'Contact Us' in response.data  # Check for contact information

def test_index_page_has_navigation(client: FlaskClient) -> None:
    """Test the index page has navigation links."""
    response = client.get('/')
    assert b'Home' in response.data
    assert b'About' in response.data
    assert b'Dashboard' in response.data

def test_nonexistent_route(client: FlaskClient) -> None:
    """Test that a nonexistent route returns a 404 status code."""
    response = client.get('/nonexistent')
    assert response.status_code == 404
    assert b'Page Not Found' in response.data  # Check for 404 content

def test_login_with_invalid_credentials(client: FlaskClient) -> None:
    """Test login with invalid credentials returns an error."""
    response = client.post('/login', data={'username': 'wronguser', 'password': 'wrongpass'})
    assert response.status_code == 200
    assert b'Invalid credentials' in response.data  # Check for error message

def testLogoutRedirectsToIndex(client: FlaskClient) -> None:
    """Test that logging out redirects to the index page."""
    client.post('/login', data={'username': 'testuser', 'password': 'password'})
    response = client.get('/logout')
    assert response.status_code == 302
    assert response.location.endswith('/')  # Check for redirect to index