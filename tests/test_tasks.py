import pytest
import os
import shutil

from app import create_app, db
from app.models import Task
from app.models import User
from app.tasks import BadUrlError
from app.tasks import get_yt_file_info
from app.tasks import get_sc_file_info
from app.tasks import get_yt_playlist_items
from app.tasks import concatenate_elements
from app.tasks import download
from app.tasks import download_yt_files
from config import Config


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    WTF_CSRF_ENABLED = False


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


# Testing get info


def test_get_yt_file_info(client):
    info = get_yt_file_info("https://www.youtube.com/watch?v=rTyKk53Wq3w")
    assert info['resource'] == 'yt'
    assert len(info['API_response']['items']) > 0
    assert 'duration' in info['API_response']['items'][0]['contentDetails']

    info = get_yt_file_info("https://youtu.be/JR6aKhnAcFA")
    assert info['resource'] == 'yt'
    assert len(info['API_response']['items']) > 0
    assert 'duration' in info['API_response']['items'][0]['contentDetails']

    info = get_yt_file_info('https://www.youtube.com/watch?v=rTyKk53Wq3w&list=PLk_klgt4LMVdcHAKqQ93bKtQ_r2YgsxlP')
    assert info['resource'] == 'yt'
    assert len(info['API_response']['items']) > 0
    assert 'duration' in info['API_response']['items'][0]['contentDetails']

    with pytest.raises(BadUrlError, match='No information about this video.'):
        get_yt_file_info('https://www.youtube.com/watch?v=rTyKk53Wq3s')

    with pytest.raises(BadUrlError, match='Url do not belong domain yputube.com or does not lead to video.'):
        get_yt_file_info('https://www.yutube.com/watch?v=rTyKk53Wq3s')

    with pytest.raises(BadUrlError, match='No information about this video.'):
        get_yt_file_info('https://www.youtube.com/watch?v=rTyKk5')


def test_get_sc_file_info(client):
    info = get_sc_file_info("https://soundcloud.com/elinacooper/"
                            "bring-me-the-horizon-nihilist-bluescover-by-the-veer-union")
    assert info['resource'] == 'sc'
    assert info['type'] == 0

    info = get_sc_file_info('https://soundcloud.com/bluestahli/sets/lakes-of-flame-comaduster')
    assert info['resource'] == 'sc'
    assert info['type'] == 1

    with pytest.raises(BadUrlError, match='Url do not belong domain soundcloud.com.'):
        get_sc_file_info('https://soundloud.com/bluestahli/sets/lakes-of-flame-comaduste')

    with pytest.raises(BadUrlError, match='Audio not found.'):
        get_sc_file_info('https://soundcloud.com/bluestahli/sets/lakes-of-flame-comaduste')


# Testing get playlist items


def test_get_yt_playlist_items(client):
    with pytest.raises(BadUrlError, match='Url do not belong domain youtube.com or does not lead to playlist.'):
        get_yt_playlist_items('https://www.youtubed.com/playlist?list=OLAK5uy_kf2mr4s7G3ErS-ruCXgDFFwY8HyHQijfA', 0, 0)

    with pytest.raises(IndexError, match='First index is out of range.'):
        get_yt_playlist_items('https://www.youtube.com/playlist?list=OLAK5uy_kf2mr4s7G3ErS-ruCXgDFFwY8HyHQijfA', -1, 0)

    with pytest.raises(IndexError, match='End index is out of range.'):
        get_yt_playlist_items('https://www.youtube.com/playlist?list=OLAK5uy_kf2mr4s7G3ErS-ruCXgDFFwY8HyHQijfA', 0, -1)

    with pytest.raises(IndexError, match='First index is out of range.'):
        get_yt_playlist_items('https://www.youtube.com/playlist?list=OLAK5uy_kf2mr4s7G3ErS-ruCXgDFFwY8HyHQijfA', 14, 14)

    l = get_yt_playlist_items('https://www.youtube.com/playlist?list=OLAK5uy_kf2mr4s7G3ErS-ruCXgDFFwY8HyHQijfA', 0, 13)
    assert len(l) == 13

    l = get_yt_playlist_items('https://www.youtube.com/playlist?list=OLAK5uy_kf2mr4s7G3ErS-ruCXgDFFwY8HyHQijfA', 0, 14)
    assert len(l) == 14
    assert l[0] == 'XkCA2XqUJ4o'
    assert l[13] == 'uX3Gw82f6GU'

    l = get_yt_playlist_items('https://www.youtube.com/playlist?list=PL6Lt9p1lIRZ311J9ZHuzkR5A3xesae2pk', 50, 51)
    assert len(l) == 1
    assert l[0] == 'O-fyNgHdmLI'

    l = get_yt_playlist_items('https://www.youtube.com/playlist?list=PL6Lt9p1lIRZ311J9ZHuzkR5A3xesae2pk', 69, 131)
    assert len(l) == 62
    assert l[0] == '8IEQpfA528M'
    assert l[61] == 'EqkBRVukQmE'


# Testing download


def test_download_from_yt(client):
    try:
        os.mkdir('temp')
    except FileExistsError:
        pass
    filename = download('https://www.youtube.com/watch?v=rTyKk53Wq3w', dir='./temp')
    filename = os.path.dirname(filename) + os.path.sep + \
               concatenate_elements(filename.split(os.sep)[-1].split('.')) + 'mp3'
    assert os.path.isfile(filename) is True
    try:
        shutil.rmtree('./temp')
    except FileNotFoundError:
        pass


def test_download_from_sc(client):
    try:
        os.mkdir('temp')
    except FileExistsError:
        pass
    filename = download('https://soundcloud.com/elinacooper/'
                        'bring-me-the-horizon-nihilist-bluescover-by-the-veer-union', dir='./temp')
    filename = os.path.dirname(filename) + os.path.sep + \
               concatenate_elements(filename.split(os.sep)[-1].split('.')) + 'mp3'
    assert os.path.isfile(filename) is True
    try:
        shutil.rmtree('./temp')
    except FileNotFoundError:
        pass


def test_download_yt_files(client):
    try:
        os.mkdir('temp')
    except FileExistsError:
        pass
    l = get_yt_playlist_items('https://www.youtube.com/playlist?list=PLk_klgt4LMVdcHAKqQ93bKtQ_r2YgsxlP', 0, 2)
    path = download_yt_files(l, dir='./temp')
    os.path.isfile(path)


# Testing routes


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
