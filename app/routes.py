from app import app, db
from app.models import Task
from app.forms import DownloadForm
from app.tasks import download
from app.tasks import get_download_response
from flask import render_template
from flask import redirect
from flask import request
from flask import flash
from flask import url_for
from flask import make_response
from flask import jsonify
from youtube_dl import DownloadError


@app.route('/', methods=['GET'])
@app.route('/index', methods=['GET'])
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


@app.route('/download_yt', methods=['GET', 'POST'])
def download_yt():
    if request.method == "GET":
        return redirect(url_for('index', active_slide=1))
    youtube_form = DownloadForm()
    if youtube_form.validate_on_submit():
        t = Task.query.filter_by(user_ip=str(request.remote_addr), status_code=0).first()
        if t:
            flash('Please wait until your downloading complete.')
            return redirect(url_for('index', active_slide=1))
        print(f'Loading from youtube ip:{request.remote_addr} data:{youtube_form.link.data}')
        t = Task(description="Downloading mp3", user_ip=str(request.remote_addr), status_code=0, progress='Waiting')
        db.session.add(t)
        db.session.commit()
        try:
            file, t = download(youtube_form.link.data[:43], request.remote_addr)
        except DownloadError as err:
            t.force_stop("Download error")
            raise err
        return get_download_response(file, t)
    else:
        flash(youtube_form.link.errors[0])
        return redirect(url_for('index', active_slide=1))


@app.route('/download_sc', methods=['GET', 'POST'])
def download_sc():
    if request.method == "GET":
        return redirect(url_for('index', active_slide=2))
    soundcloud_form = DownloadForm()
    if soundcloud_form.validate_on_submit():
        print(f'loading from soundcloud ip:{request.remote_addr} data:{soundcloud_form.link.data}')
        file, t = download(soundcloud_form.link.data, request.remote_addr)
        return get_download_response(file, t)
    else:
        return redirect(url_for('index', active_slide=2))


@app.route('/get_progress', methods=['GET'])
def get_progress():
    t = Task.query.filter_by(user_ip=str(request.remote_addr), status_code=0).first()
    if t:
        return jsonify({'Status_code': 0, 'Progress': t.progress})
    else:
        return jsonify({'Status_code': 1, 'Progress': 'Done'})
