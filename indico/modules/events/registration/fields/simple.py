# This file is part of Indico.
# Copyright (C) 2002 - 2015 European Organization for Nuclear Research (CERN).
#
# Indico is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# Indico is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Indico; if not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import mimetypes
from uuid import uuid4

import wtforms
from wtforms.validators import NumberRange

from indico.modules.events.registration.fields.base import RegistrationFormFieldBase, RegistrationFormBillableField
from indico.modules.events.registration.models.registrations import RegistrationData
from indico.util.fs import secure_filename
from indico.util.string import crc32, normalize_phone_number
from indico.web.forms.validators import IndicoEmail
from MaKaC.webinterface.common.countries import CountryHolder


class TextField(RegistrationFormFieldBase):
    name = 'text'
    wtf_field_class = wtforms.StringField


class NumberField(RegistrationFormBillableField):
    name = 'number'
    wtf_field_class = wtforms.IntegerField

    @property
    def validators(self):
        min_value = self.form_item.data.get('min_value', None)
        return [NumberRange(min=min_value)] if min_value else None

    def calculate_price(self, registration_data):
        data = registration_data.field_data.versioned_data
        if not data['is_billable']:
            return 0
        return data['price'] * registration_data.data


class TextAreaField(RegistrationFormFieldBase):
    name = 'textarea'
    wtf_field_class = wtforms.StringField


class SelectField(RegistrationFormBillableField):
    name = 'radio'
    wtf_field_class = wtforms.StringField

    @property
    def default_value(self):
        data = self.form_item.data
        versioned_data = self.form_item.current_data.versioned_data
        try:
            default_item = data['default_item']
        except KeyError:
            return None
        return next((x['id'] for x in versioned_data['radioitems'] if x['caption'] == default_item), None)

    @classmethod
    def modify_post_data(cls, post_data):
        items = post_data['radioitems']
        for item in items:
            item['id'] = unicode(uuid4())

    def calculate_price(self, registration_data):
        data = registration_data.field_data.versioned_data
        item = next((x for x in data['radioitems'] if registration_data.data == x['id'] and x['is_billable']), None)
        return item['price'] if item else 0


class CheckboxField(RegistrationFormBillableField):
    name = 'checkbox'
    wtf_field_class = wtforms.BooleanField

    def calculate_price(self, registration_data):
        data = registration_data.field_data.versioned_data
        if not data['is_billable'] or not registration_data.data:
            return 0
        return data['price']


class DateField(RegistrationFormFieldBase):
    name = 'date'
    wtf_field_class = wtforms.StringField

    @classmethod
    def modify_post_data(cls, post_data):
        date_format = post_data['date_format'].split(' ')
        post_data['date_format'] = date_format[0]
        if len(date_format) == 2:
            post_data['time_format'] = date_format[1]


class BooleanField(RegistrationFormBillableField):
    name = 'yes/no'
    wtf_field_class = wtforms.StringField

    def calculate_price(self, registration_data):
        data = registration_data.field_data.versioned_data
        if not data['is_billable'] or registration_data.data != 'yes':
            return 0
        return data['price']


class PhoneField(RegistrationFormFieldBase):
    name = 'phone'
    wtf_field_class = wtforms.StringField
    wtf_field_kwargs = {'filters': [lambda x: normalize_phone_number(x) if x else '']}


class CountryField(RegistrationFormFieldBase):
    name = 'country'
    wtf_field_class = wtforms.SelectField

    @property
    def wtf_field_kwargs(self):
        return {'choices': CountryHolder.getCountries().items()}

    @property
    def view_data(self):
        return {'radioitems': [{'caption': val, 'countryKey': key}
                               for key, val in CountryHolder.getCountries().iteritems()]}


class FileField(RegistrationFormFieldBase):
    name = 'file'
    wtf_field_class = wtforms.FileField

    def save_data(self, registration, value):
        if value is None:
            return
        f = value.file
        content = f.read()
        metadata = {
            'hash': crc32(content),
            'size': len(content),
            'filename': secure_filename(value.filename, 'registration_form_file'),
            'content_type': mimetypes.guess_type(value.filename)[0] or value.mimetype or 'application/octet-stream'
        }

        registration.data.append(RegistrationData(field_data_id=self.form_item.current_data_id, file=content,
                                                  file_metadata=metadata))

    @property
    def default_value(self):
        return None


class EmailField(RegistrationFormFieldBase):
    name = 'email'
    wtf_field_class = wtforms.StringField
    wtf_field_kwargs = {'filters': [lambda x: x.lower() if x else x]}

    @property
    def validators(self):
        return [IndicoEmail()]
