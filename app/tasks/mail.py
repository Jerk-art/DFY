from flask_mail import Message
from config import Config
from app import create_app
from app import mail
from threading import Thread
from flask import current_app
from flask import render_template

if Config.USE_CELERY:
    from app import celery


def create_mail(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    return msg


if Config.USE_CELERY:
    @celery.task
    def send_mail_async(subject, sender, recipients, text_body, html_body):
        app = create_app()
        with app.app_context():
            msg = create_mail(subject, sender, recipients, text_body, html_body)
            mail.send(msg)


def send_mail_sync(subject, sender, recipients, text_body, html_body):
    app = create_app()
    with app.app_context():
        msg = create_mail(subject, sender, recipients, text_body, html_body)
        mail.send(msg)


def send_email(subject, sender, recipients, text_body, html_body, sync=False):
    if not current_app.config['SEND_MAILS']:
        return
    if sync:
        msg = create_mail(subject, sender, recipients, text_body, html_body)
        mail.send(msg)
    elif current_app.config['USE_CELERY']:
        send_mail_async.apply_async(args=[subject, sender, recipients, text_body, html_body])
    elif current_app.config['ASYNC_TASKS']:
        Thread(target=send_mail_sync, args=(subject, sender, recipients, text_body, html_body)).start()
    else:
        msg = create_mail(subject, sender, recipients, text_body, html_body)
        mail.send(msg)


def send_confirmation_email(user, action, pattern):
    token = user.get_confirmation_token()
    send_email(f'[DFY] {action}',
               sender=current_app.config['ADMINS'][0],
               recipients=[user.email],
               text_body=render_template(pattern + '.txt',
                                         user=user, token=token,
                                         exp_time=current_app.config['UNCONFIRMED_ACC_EXPIRATION_TIME']),
               html_body=render_template(pattern + '.html',
                                         user=user, token=token,
                                         exp_time=current_app.config['UNCONFIRMED_ACC_EXPIRATION_TIME']))


def send_file_ready_email(user, action, pattern, errors_list):
    send_email(f'[DFY] {action}',
               sender=current_app.config['ADMINS'][0],
               recipients=[user.email],
               text_body=render_template(pattern + '.txt',
                                         user=user, errors_list=errors_list),
               html_body=render_template(pattern + '.html',
                                         user=user, errors_list=errors_list),
               sync=True)


def send_file_fail_email(user, action, pattern):
    send_email(f'[DFY] {action}',
               sender=current_app.config['ADMINS'][0],
               recipients=[user.email],
               text_body=render_template(pattern + '.txt', user=user),
               html_body=render_template(pattern + '.html', user=user), sync=True)
