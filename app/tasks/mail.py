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
    """Create message object

    :param subject: email subject
    :type subject: str
    :param sender: email sender
    :type sender: str
    :param recipients: email recipients
    :type recipients: list
    :param text_body: email text_body
    :type text_body: Flask template
    :param html_body: email html_body
    :type html_body: Flask template

    :returns: Flask-mail message object
    """
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
    """Create message and send it

    :param subject: email subject
    :type subject: str
    :param sender: email sender
    :type sender: str
    :param recipients: email recipients
    :type recipients: list
    :param text_body: email text_body
    :type text_body: Flask template
    :param html_body: email html_body
    :type html_body: Flask template
    """
    app = create_app()
    with app.app_context():
        msg = create_mail(subject, sender, recipients, text_body, html_body)
        mail.send(msg)


def send_email(subject, sender, recipients, text_body, html_body, sync=False):
    """Depending on configuration send email in main thread, child thread or as celery task

    :param subject: email subject
    :type subject: str
    :param sender: email sender
    :type sender: str
    :param recipients: email recipients
    :type recipients: list
    :param text_body: email text_body
    :type text_body: Flask template
    :param html_body: email html_body
    :type html_body: Flask template
    :param sync: send mail in sync mode
    :type sync: bool
    """
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
    """Create confirmation message and send it

    :param user: user object which should receive mail
    :type user: User
    :param action: string describing of action which will be injected into mail header
    :type action: str
    :param pattern: path to template, notice that extension should not be included,
                    and also you need template as txt and html file
    :type pattern: str
    """
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
    """Create 'file ready' message and send it

    :param user: user object which should receive mail
    :type user: User
    :param action: string describing of action which will be injected into mail header
    :type action: str
    :param pattern: path to template, notice that extension should not be included,
                    and also you need template as txt and html file
    :type pattern: str
    :param errors_list: list of ids of files that was failed to download
    :type errors_list: list
    """
    send_email(f'[DFY] {action}',
               sender=current_app.config['ADMINS'][0],
               recipients=[user.email],
               text_body=render_template(pattern + '.txt',
                                         user=user, errors_list=errors_list),
               html_body=render_template(pattern + '.html',
                                         user=user, errors_list=errors_list),
               sync=True)


def send_file_fail_email(user, action, pattern):
    """Create 'file fail' message and send it

    :param user: user object which should receive mail
    :type user: User
    :param action: string describing of action which will be injected into mail header
    :type action: str
    :param pattern: path to template, notice that extension should not be included,
                    and also you need template as txt and html file
    :type pattern: str
    """
    send_email(f'[DFY] {action}',
               sender=current_app.config['ADMINS'][0],
               recipients=[user.email],
               text_body=render_template(pattern + '.txt', user=user),
               html_body=render_template(pattern + '.html', user=user), sync=True)
