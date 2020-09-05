from app import db
from app.tasks.info import get_yt_playlist_items
from app.tasks.download import download
from app.tasks.download import download_yt_files
from app.tasks.download import get_download_response
from app.main import bp
from app.main.forms import DownloadForm
from app.main.forms import DownloadForm2
from app.main.forms import DownloadPlaylistItemsForm
from app.main.forms import get_quality
from app.models import Task
from flask import abort
from flask import render_template
from flask import redirect
from flask import request
from flask import flash
from flask import url_for
from flask import jsonify
from flask import current_app
from flask_login import current_user
from youtube_dl import DownloadError

import os
import time


@bp.route('/', methods=['GET'])
@bp.route('/index', methods=['GET'])
def index():
    if current_user.is_authenticated:
        youtube_form = DownloadForm2()
        soundcloud_form = DownloadForm2()
    else:
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
    repair_tags = False
    dir = f'app{os.path.sep}tasks{os.path.sep}temp{os.path.sep}'
    if request.method == "GET":
        return redirect(url_for('main.index', active_slide=1))
    if not current_user.is_authenticated:
        youtube_form = DownloadForm()
        if youtube_form.validate_on_submit():
            t = Task.query.filter_by(user_ip=str(request.remote_addr), status_code=0).first()
            if t:
                flash('Please wait while your other downloading is complete.', 'yt')
                return redirect(url_for('main.index', active_slide=1))
            t = Task(description="Downloading mp3", user_ip=str(request.remote_addr), status_code=0, progress='Waiting')
            quality = 192
            dir += str(request.remote_addr)
            print(f'Loading from youtube user ip:{request.remote_addr} data:{youtube_form.link.data}')
        else:
            flash(youtube_form.link.errors[0], 'yt')
            return redirect(url_for('main.index', active_slide=1))

    else:
        youtube_form = DownloadForm2()
        if youtube_form.validate_on_submit():
            t = Task.query.filter_by(user_id=current_user.id, status_code=0).first()
            if t:
                flash('Please wait while your other downloading is complete.', 'yt')
                return redirect(url_for('main.index', active_slide=1))
            t = Task(description="Downloading mp3", user_id=current_user.id, status_code=0, progress='Waiting')
            quality = get_quality(youtube_form.quality.data)
            repair_tags = youtube_form.repair_tags.data
            dir += str(current_user.id)
            print(f'Loading from youtube user id:{current_user.id} data:{youtube_form.link.data}')
        else:
            flash(youtube_form.link.errors[0], 'yt')
            return redirect(url_for('main.index', active_slide=1))

    db.session.add(t)
    db.session.commit()
    try:
        if youtube_form.link.data.startswith('https://www.youtube.com/watch?v='):
            file = download(youtube_form.link.data[:43], task=t, quality=quality, repair_tags=repair_tags, dir=dir)
        else:
            file = download(youtube_form.link.data[:28], task=t, quality=quality, repair_tags=repair_tags, dir=dir)
    except DownloadError as err:
        t.force_stop('Download error')
        raise err
    return get_download_response(file, t)


@bp.route('/download_sc', methods=['GET', 'POST'])
def download_sc():
    dir = f'app{os.path.sep}tasks{os.path.sep}temp{os.path.sep}'
    repair_tags = False
    if request.method == "GET":
        return redirect(url_for('main.index', active_slide=2))
    if not current_user.is_authenticated:
        soundcloud_form = DownloadForm()
        if soundcloud_form.validate_on_submit():
            t = Task.query.filter_by(user_ip=str(request.remote_addr), status_code=0).first()
            if t:
                flash('Please wait while your other downloading is complete.', 'yt')
                return redirect(url_for('main.index', active_slide=1))
            t = Task(description="Downloading mp3", user_ip=str(request.remote_addr), status_code=0, progress='Waiting')
            quality = 192
            dir += str(request.remote_addr)
            print(f'Loading from youtube user ip:{request.remote_addr} data:{soundcloud_form.link.data}')
        else:
            flash(soundcloud_form.link.errors[0], 'sc')
            return redirect(url_for('main.index', active_slide=2))

    else:
        soundcloud_form = DownloadForm2()
        if soundcloud_form.validate_on_submit():
            t = Task.query.filter_by(user_id=current_user.id, status_code=0).first()
            if t:
                flash('Please wait while your other downloading is complete.', 'yt')
                return redirect(url_for('main.index', active_slide=1))
            t = Task(description="Downloading mp3", user_id=current_user.id, status_code=0, progress='Waiting')
            quality = get_quality(soundcloud_form.quality.data)
            repair_tags = soundcloud_form.repair_tags.data
            dir += str(current_user.id)
            print(f'Loading from youtube user id:{current_user.id} data:{soundcloud_form.link.data}')
        else:
            flash(soundcloud_form.link.errors[0], 'sc')
            return redirect(url_for('main.index', active_slide=2))

    db.session.add(t)
    db.session.commit()
    try:
        file = download(soundcloud_form.link.data, task=t, quality=quality, repair_tags=repair_tags, dir=dir)
    except DownloadError as err:
        t.force_stop('Download error')
        raise err
    return get_download_response(file, t)


@bp.route('/download_playlist_items', methods=['GET', 'POST'])
def download_playlist_items():
    form = DownloadPlaylistItemsForm()
    if request.method == "GET":
        if current_user.is_authenticated:
            t = Task.query.filter_by(user_id=current_user.id, status_code=3).first()
            if t and t.description == 'Downloading playlist items':
                return render_template('/download_playlist_progress.html',
                                       exp_time=current_app.config['PLAYLIST_LIVE_TIME'])
            else:
                t = Task.query.filter_by(user_id=current_user.id, status_code=4).first()
                if t:
                    return render_template('/download_playlist_progress.html',
                                           exp_time=current_app.config['PLAYLIST_LIVE_TIME'])
            return render_template('/download_playlist_items.html', form=form,
                                   duration=current_app.config['ALLOWED_DURATION'])
        else:
            return redirect(url_for('main.index'))
    else:
        if current_user.is_authenticated:
            if form.validate_on_submit():
                t = Task.query.filter_by(user_id=current_user.id, status_code=3).first()
                if t:
                    return render_template('/download_playlist_progress.html',
                                           exp_time=current_app.config['PLAYLIST_LIVE_TIME'])
                else:
                    t = Task.query.filter_by(user_id=current_user.id, status_code=4).first()
                    if t:
                        return render_template('/download_playlist_progress.html',
                                               exp_time=current_app.config['PLAYLIST_LIVE_TIME'])

                t = Task(description="Downloading playlist items",
                         user_id=current_user.id,
                         status_code=3,
                         progress='Waiting')
                quality = get_quality(form.quality.data)
                repair_tags = form.repair_tags.data
                dir = f'app{os.path.sep}tasks{os.path.sep}temp{os.path.sep}{current_user.id}'
                print(f'Loading playlist items from youtube user id:{current_user.id} data:{form.link.data}')
            else:
                if form.link.errors:
                    flash(form.link.errors[0])
                elif form.first_item_number.errors:
                    flash(form.first_item_number.errors[0])
                elif form.last_item_number.errors:
                    flash(form.last_item_number.errors[0])
                return render_template('/download_playlist_items.html', form=form,
                                       duration=current_app.config['ALLOWED_DURATION'])
        else:
            return redirect(url_for('main.index'))

    db.session.add(t)
    db.session.commit()

    files_list = get_yt_playlist_items(form.link.data, form.first_item_number.data - 1, form.last_item_number.data)

    download_yt_files(files_list, task=t, quality=quality, repair_tags=repair_tags, dir=dir)

    return render_template('/download_playlist_progress.html',
                           exp_time=current_app.config['PLAYLIST_LIVE_TIME'])


@bp.route('/get_file', methods=['GET'])
def get_file():
    if current_user.is_authenticated:
        t = Task.query.filter_by(user_id=current_user.id, status_code=4).first()
        if t:
            if t.progress.startswith('Files downloaded') and t.description == 'Downloading playlist items':
                return get_download_response(t.unique_process_info, t, ext='.zip', end_task=False)
            else:
                return abort(403)
        else:
            return redirect(url_for('main.download_playlist_items'))
    else:
        return abort(404)


@bp.route('/get_progress', methods=['GET'])
def get_progress():
    time.sleep(1)
    if not current_user.is_authenticated:
        t = Task.query.filter_by(user_ip=str(request.remote_addr), status_code=0).first()
    else:
        t = Task.query.filter_by(user_id=str(current_user.id), status_code=0).first()
    if t:
        return jsonify({'Status_code': t.status_code, 'Progress': t.progress})
    else:
        return jsonify({'Status_code': 1, 'Progress': 'Done'})


@bp.route('/get_playlist_downloading_progress')
def get_playlist_downloading_progress():
    if current_user.is_authenticated:
        t = Task.query.filter_by(user_id=str(current_user.id), status_code=3).first()
        if not t:
            t = Task.query.filter_by(user_id=str(current_user.id), status_code=4).first()
        if t:
            statuses = str()
            files = t.files.all()
            if files and len(files) > 0:
                for el in sorted(files, key=files.index):
                    if el.index != 0:
                        statuses += str(el.status_code)
                return jsonify({'Status_code': t.status_code, 'Progress': t.progress, 'Status_codes': statuses})
            else:
                return jsonify({'Status_code': t.status_code, 'Progress': t.progress, 'Status_codes': None})
        else:
            return jsonify({'Status_code': 1, 'Progress': 'Done'})
    else:
        abort(403)
