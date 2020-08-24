import pytest
import shutil

from app import create_app, db
from app.models import User
from config import Config


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    WTF_CSRF_ENABLED = False
    USE_CELERY = False


app = create_app(TestConfig)


@pytest.fixture
def client():
    with app.test_client() as client:
        app_context = app.app_context()
        app_context.push()
        db.create_all()
        u = User()
        u.username = 'user'
        u.email = 'user@example.com'
        u.set_password_hash('12345678')
        db.session.add(u)
        db.session.commit()
        yield client

    db.session.remove()
    db.drop_all()
    app_context.pop()

    try:
        shutil.rmtree('./temp')
    except FileNotFoundError:
        pass


def test_index_view(client):
    r = client.get('/')
    assert r.status_code == 200
    r = client.get('/index')
    assert r.status_code == 200


def test_get_progress_view(client):
    r = client.get('/get_progress')
    assert r.status_code == 200
    data = r.get_json()
    assert data['Status_code'] == 1
    assert data['Progress'] == 'Done'


def test_download_yt_view(client):
    r = client.get('/download_yt')
    assert r.status_code == 302
    r = client.post('/download_yt', data=dict(link='https://www.youtube.com/watch?v=nMUyqlTR_4'))
    assert r.status_code == 302
    r = client.post('/download_yt', data=dict(link='https://www.youtube.com/watch?v=nMUyQqlTR_4'))
    assert r.status_code == 200


def test_download_sc_view(client):
    r = client.get('/download_sc')
    assert r.status_code == 302
    r = client.post('/download_sc', data=dict(link='https://soundcloud.com/elinacooper/'
                                                   'bring-me-the-horizon-nihilist-bluescver-by-the-veer-union'))
    assert r.status_code == 302
    r = client.post('/download_sc', data=dict(link='https://soundcloud.com/elinacooper/'
                                                   'bring-me-the-horizon-nihilist-bluescover-by-the-veer-union'))
    assert r.status_code == 200


def test_sign_up_view(client):
    r = client.get('/sign_up')
    assert r.status_code == 200

    r = client.post('/sign_up', data=dict(username='user',
                                          email='user@example.com',
                                          password='12345678',
                                          repeat_password='12345678'))
    assert b'Username is already taken, please use a different username.' in r.data

    r = client.post('/sign_up', data=dict(username='user2',
                                          email='user2@example.com',
                                          password='12345678',
                                          repeat_password='12345678'))
    assert b'User successfully created.' in r.data

    r = client.post('/sign_up', data=dict(username='us3',
                                          email='user3@example.com',
                                          password='12345678',
                                          repeat_password='12345678'))
    assert b'Username must be at least 4 symbols long.' in r.data

    r = client.post('/sign_up', data=dict(username='user3',
                                          email='user@example.com',
                                          password='12345678',
                                          repeat_password='12345678'))
    assert b'Email address is already taken, please use a different email.' in r.data

    r = client.post('/sign_up', data=dict(username='user3',
                                          email='user3@example.com',
                                          password='1234567',
                                          repeat_password='12345678'))
    assert b'Password must be at least 8 symbols long.' in r.data

    users = User.query.all()

    assert len(users) == 2


def test_sign_in_view(client):
    r = client.get('/sign_in')
    assert r.status_code == 200

    r = client.post('/sign_in', data=dict(username='user',
                                          email='user@example.com',
                                          password='12345678'))
    assert b'Please confirm email and then you can sign in.' in r.data

    u = User.query.get(1)
    u.confirmed = True
    db.session.add(u)
    db.session.commit()

    r = client.post('/sign_in', data=dict(username='user',
                                          email='user@example.com',
                                          password='12345678'),
                    follow_redirects=True)
    assert b'User' in r.data

    r = client.post('/sign_in', data=dict(username='user2',
                                          email='user@example.com',
                                          password='12345678'))
    assert b'Username or password is invalid.' in r.data


def test_logout_view(client):
    u = User.query.get(1)
    u.confirmed = True
    db.session.add(u)
    db.session.commit()

    r = client.post('/sign_in', data=dict(username='user',
                                          email='user@example.com',
                                          password='12345678'),
                    follow_redirects=True)
    assert b'User' in r.data

    r = client.get('/logout')
    assert b'User' not in r.data


def test_confirm_user_view(client):
    u = User.query.get(1)
    token = u.get_confirmation_token()

    r = client.get(f'/confirm_user{token}', follow_redirects=True)
    assert b'Your email confirmed, please sign in.' in r.data

    r = client.get(f'/confirm_user{token}', follow_redirects=True)
    assert b'Your email already confirmed!' in r.data

    r = client.get(f'/confirm_user{token[1:]}')
    assert r.status_code == 404


def test_request_password_change_view(client):
    u = User.query.get(1)
    u.confirmed = True
    db.session.add(u)
    db.session.commit()

    r = client.post('/sign_in', data=dict(username='user',
                                          email='user@example.com',
                                          password='12345678'),
                    follow_redirects=True)
    assert b'User' in r.data

    r = client.post('/request_password_change', data=dict(email='user@example.com'))
    assert r.status_code == 400

    r = client.get('/request_password_change')
    assert b'Please check your email to continue process.' in r.data

    r = client.get('/logout')
    assert b'User' not in r.data

    r = client.get('/request_password_change')
    assert b'Please enter your email.' in r.data

    r = client.post('/request_password_change', data=dict(email='user@example.co'))
    assert b'<-- Failed to find user with this email.' in r.data

    r = client.post('/request_password_change', data=dict(email='user@example.com'))
    assert b'Please check your email to continue process.' in r.data


def test_change_password_view(client):
    u = User.query.get(1)
    token = u.get_confirmation_token()

    r = client.get(f'/change_password{token}')
    assert r.status_code == 200

    r = client.get(f'/change_password{token[1:]}')
    assert r.status_code == 404

    r = client.post(f'/change_password{token}', data=dict(password='password', repeat_password='password'),
                    follow_redirects=True)
    assert b'Your password successfully changed!' in r.data
    assert u.check_password('password') is True
