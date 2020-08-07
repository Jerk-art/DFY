from app import db
from app.tasks import download
from app.tasks import get_download_response
from app.main import bp
from app.main.forms import DownloadForm
from app.models import Task
from flask import render_template
from flask import redirect
from flask import request
from flask import flash
from flask import url_for
from flask import jsonify
from youtube_dl import DownloadError


@bp.route('/', methods=['GET'])
@bp.route('/index', methods=['GET'])
def index():
    youtube_form = DownloadForm()
    soundcloud_form = DownloadForm()
    active_slide = request.args.get('active_slide', 1, type=int)
    if active_slide == 1:
        return render_template('index.html', title="Young downloader",
                               youtube_form=youtube_form, soundcloud_form=soundcloud_form,
                               active_slide=1)
    else:
        return render_template('index.html', title="Young downloader",
                               youtube_form=youtube_form, soundcloud_form=soundcloud_form,
                               active_slide=2)


@bp.route('/download_yt', methods=['GET', 'POST'])
def download_yt():
    if request.method == "GET":
        return redirect(url_for('main.index', active_slide=1))
    youtube_form = DownloadForm()
    if youtube_form.validate_on_submit():
        t = Task.query.filter_by(user_ip=str(request.remote_addr), status_code=0).first()
        if t:
            flash('Please wait while your other downloading is complete.', 'yt')
            return redirect(url_for('main.index', active_slide=1))
        print(f'Loading from youtube ip:{request.remote_addr} data:{youtube_form.link.data}')
        t = Task(description="Downloading mp3", user_ip=str(request.remote_addr), status_code=0, progress='Waiting')
        db.session.add(t)
        db.session.commit()
        try:
            if youtube_form.link.data.startswith('https://www.youtube.com/watch?v='):
                file = download(youtube_form.link.data[:43], t)
            else:
                file = download(youtube_form.link.data[:28], t)
        except DownloadError as err:
            t.force_stop('Download error')
            raise err
        return get_download_response(file, t)
    else:
        flash(youtube_form.link.errors[0], 'yt')
        return redirect(url_for('main.index', active_slide=1))


@bp.route('/download_sc', methods=['GET', 'POST'])
def download_sc():
    if request.method == "GET":
        return redirect(url_for('main.index', active_slide=2))
    soundcloud_form = DownloadForm()
    if soundcloud_form.validate_on_submit():
        t = Task.query.filter_by(user_ip=str(request.remote_addr), status_code=0).first()
        if t:
            flash('Please wait while your other downloading is complete.', 'sc')
            return redirect(url_for('main.index', active_slide=2))
        print(f'Loading from soundcloud ip:{request.remote_addr} data:{soundcloud_form.link.data}')
        t = Task(description="Downloading mp3", user_ip=str(request.remote_addr), status_code=0, progress='Waiting')
        db.session.add(t)
        db.session.commit()
        try:
            file = download(soundcloud_form.link.data, t)
        except DownloadError as err:
            t.force_stop('Download error')
            raise err
        return get_download_response(file, t)
    else:
        flash(soundcloud_form.link.errors[0], 'sc')
        return redirect(url_for('main.index', active_slide=2))


@bp.route('/get_progress', methods=['GET'])
def get_progress():
    t = Task.query.filter_by(user_ip=str(request.remote_addr), status_code=0).first()
    if t:
        return jsonify({'Status_code': 0, 'Progress': t.progress})
    else:
        return jsonify({'Status_code': 1, 'Progress': 'Done'})
