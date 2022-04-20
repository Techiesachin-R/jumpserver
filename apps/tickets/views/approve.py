# -*- coding: utf-8 -*-
#

from __future__ import unicode_literals
from django.views.generic.edit import FormView
from django.shortcuts import redirect, reverse
from django.core.cache import cache
from django.contrib.auth.hashers import check_password
from django.utils.translation import ugettext as _

from tickets.models import Ticket
from tickets.errors import AlreadyClosed
from users.models import User
from authentication.const import *
from authentication.utils import gen_key_pair
from authentication.mixins import PasswordEncryptionViewMixin, errors
from common.utils import get_logger, FlashMessageUtil
from .. import forms

logger = get_logger(__name__)
__all__ = ['TicketDirectApproveView']


class TicketDirectApproveView(PasswordEncryptionViewMixin, FormView):
    template_name = 'tickets/approve_check_password.html'
    form_class = forms.ApproveCheckPasswordForm
    redirect_field_name = 'next'

    @property
    def message_data(self):
        token = self.request.GET.get('token')
        return {
            'title': _('Ticket direct approval'),
            'error': _("This ticket does not exist, "
                       "the process has ended, or this link has expired"),
            'redirect_url': reverse('tickets:direct-approve') + '?token=%s' % token,
            'auto_redirect': False
        }

    @property
    def login_url(self):
        return reverse('authentication:login') + '?admin=1'

    def redirect_message_response(self, **kwargs):
        message_data = self.message_data
        for key, value in kwargs.items():
            if isinstance(value, str):
                message_data[key] = value
        if message_data.get('message'):
            message_data.pop('error')
        redirect_url = FlashMessageUtil.gen_message_url(message_data)
        return redirect(redirect_url)

    def get(self, *args, **kwargs):
        token = self.request.GET.get('token')
        ticket_info = cache.get(token)
        if not ticket_info:
            return self.redirect_message_response(redirect_url=self.login_url)
        return super().get(*args, **kwargs)

    def form_valid(self, form):
        token = self.request.GET.get('token')
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        ticket_info = cache.get(token)
        if not ticket_info:
            return self.redirect_message_response(redirect_url=self.login_url)
        try:
            password = self.get_decrypted_password(password, username)
            user = User.objects.get(username=username)
            resp = check_password(password, user.password)
            if not resp:
                raise errors.AuthFailedError()
        except Exception:
            form.add_error("password", _(f"Password invalid"))
            return self.form_invalid(form)
        try:
            ticket_id = ticket_info.get('ticket_id')
            ticket = Ticket.all().get(id=ticket_id)
            if not ticket.has_current_assignee(user):
                raise Exception(_("This user is not authorized to approve this ticket"))
            ticket.approve(user)
        except AlreadyClosed as e:
            self.clear_all(token)
            return self.redirect_message_response(error=str(e), redirect_url=self.login_url)
        except Exception as e:
            return self.redirect_message_response(error=str(e))

        self.clear_all(token)
        return self.redirect_message_response(message=_("Success"), redirect_url=self.login_url)

    def clear_all(self, token):
        cache.delete(token)
        self.request.session[RSA_PRIVATE_KEY] = None
        self.request.session[RSA_PUBLIC_KEY] = None

    def get_context_data(self, **kwargs):
        rsa_public_key = self.request.session.get(RSA_PUBLIC_KEY)
        rsa_private_key = self.request.session.get(RSA_PRIVATE_KEY)
        if not all([rsa_private_key, rsa_public_key]):
            rsa_private_key, rsa_public_key = gen_key_pair()
            rsa_public_key = rsa_public_key.replace('\n', '\\n')
            self.request.session[RSA_PRIVATE_KEY] = rsa_private_key
            self.request.session[RSA_PUBLIC_KEY] = rsa_public_key

        # 放入工单信息
        token = self.request.GET.get('token')
        ticket_info = cache.get(token, {}).get('body', '')
        kwargs.update({
            'rsa_public_key': rsa_public_key, 'ticket_info': ticket_info
        })
        return super().get_context_data(**kwargs)
