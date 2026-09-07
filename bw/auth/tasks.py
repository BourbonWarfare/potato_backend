import urllib.parse
from string import Template

import resend

from bw.environment import ENVIRONMENT
from bw.tasks import Kind


class TaskSendRegistrationEmail(Kind):
    def __init__(self, to_send: str, authorization_token: str):
        super().__init__(task_executor=self.run, to_send=to_send, authorization_token=authorization_token)

    def run(self, to_send: str, authorization_token: str):
        resend.api_key = ENVIRONMENT.resend_api_key()
        with open('static/templates/auth/email/verification.template.html') as html_file:
            email_template = Template(html_file.read())

        verify_url = urllib.parse.urljoin(ENVIRONMENT.server_url(), '/auth/verify')

        params: resend.Emails.SendParams = {
            'from': 'Bourbon Warfare Staff <noreply@staff.bourbonwarfare.com>',
            'to': [to_send],
            'subject': 'Verify your email with Bourbon Warfare',
            'html': email_template.substitute(verify_url=verify_url, verify_token=authorization_token),
        }

        resend.Emails.send(params)


class TaskSendRecoveryEmail(Kind):
    def __init__(self, to_send: str, recovery_code: str):
        super().__init__(task_executor=self.run, to_send=to_send, recovery_code=recovery_code)

    def run(self, to_send: str, recovery_code: str):
        resend.api_key = ENVIRONMENT.resend_api_key()
        with open('static/templates/auth/email/recover.template.html') as html_file:
            email_template = Template(html_file.read())

        recover_url = urllib.parse.urljoin(ENVIRONMENT.server_url(), '/auth/recover')

        params: resend.Emails.SendParams = {
            'from': 'Bourbon Warfare Staff <noreply@staff.bourbonwarfare.com>',
            'to': [to_send],
            'subject': 'Recover your Bourbon Warfare account',
            'html': email_template.substitute(recover_url=recover_url, verify_token=recovery_code),
        }

        resend.Emails.send(params)
