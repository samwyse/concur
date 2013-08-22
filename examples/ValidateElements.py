'''\
Creates a large number of validation functions, used to ensure that a
dictionary has all required and no extraneous keys.  This is generally
used to validate keyword parameters for function definitions.
'''

import re as _re


class _DictRe(dict):
    repl = lambda self, matchobj: self.get(matchobj.group(), '')

    def compile(self, flags=0, pattern=None):
        '''Compile a regular expression consisting of the alternation
of all keys. The 'pattern' optional argument is intended for
"hand-optimized" patterns. This is a separate step to allow the
dictionary to be built incrementally. The return value allows idioms
such as, "x = _DictRe(...).compile()"'''
        self.pattern = pattern if pattern else '|'.join(_re.escape(key) for key in sorted(self.keys()))
        self.re  = _re.compile(self.pattern, flags)
        self.flags = self.re.flags
        return self

    def sub(self, string, count=0):
        '''Return the string obtained by replacing occurrences of
        dictionary keys in string by the corresponding value.'''
        return self.re.sub(self.repl, string, count)

    def subn(self, string, count=0):
        '''Perform the same operation as sub(), but return a tuple
        (new_string, number_of_subs_made).'''
        return self.re.subn(self.repl, string, count)


class ValidateElements(object):
    def __init__(self, required, optional, mapping=lambda x: x):
        self.required = frozenset(required)
        self.acceptable = self.required.union(optional)
        self.mapping = mapping
    def __call__(self, options):
        result = {}
        found = set()
        for k, v in options:
            if k in self.acceptable:
                result[k] = self.mapping(v)
                if k in self.required:
                    found.add(k)
            else:
                raise ValueError('invalid key: %r' % k)
        if self.required != found:
            raise KeyError('missing key(s): %r' % list(self.required - found))
        return result
        

_fix_dates_re = _DictRe((
    ('YYYY', '%Y'),
    ('YY', '%y'),
    ('MMMM', '%B'),
    ('MMM', '%b'),
    ('MM', '%m'),
    ('DDDD', '%A'),
    ('DDD', '%a'),
    ('DD', '%d'),
    ('HH:MM', '%H:%M'),
    ('HH:MM:SS', '%H:%M:%S'),
    )).compile(pattern='YY(?:YY)?|M{2,4}|D{2,4}|HH\:MM(?:\:SS)?')

def fix_dates(str):
    return datetime.now().strftime(_fix_dates_re.sub(str.replace('+', ' ')))

validate_report_elements = ValidateElements(['Name'],
    ['Name', 'Purpose', 'Comment', 'OrgUnit1', 'OrgUnit2', 'OrgUnit3',
     'OrgUnit4', 'OrgUnit5', 'OrgUnit6', 'Custom1', 'Custom2',
     'Custom3', 'Custom4', 'Custom5', 'Custom6', 'Custom7', 'Custom8',
     'Custom9', 'Custom10', 'Custom11', 'Custom12', 'Custom13',
     'Custom14', 'Custom15', 'Custom16', 'Custom17', 'Custom18',
     'Custom19', 'Custom20', 'UserDefinedDate'],
    mapping=fix_dates)

validate_quickexpense_elements = ValidateElements(
    ['CurrencyCode', 'TransactionAmount', 'TransactionDate'],
    ['ExpenseTypeCode', 'SpendCategoryCode', 'PaymentType',
     'LocationCity', 'LocationSubdivision', 'LocationCountry',
     'VendorDescription', 'Comment', 'ImageBase64'] )

# See also: https://developer.concur.com/api-documentation/draft-documentation/attendee-resource-draft/attendee-resource-get-draft

validate_attendees_by_id_elements = ValidateElements(
    ['required'],
    ['valid'] )

# See also: https://developer.concur.com/api-documentation/draft-documentation/e-receipt-service-developer-preview/e-receipt-or-e-invoice-res

validate_v10_by_id_elements = ValidateElements(
    ['required'],
    ['valid'] )

# See also: https://developer.concur.com/api-documentation/new-portal-format/expense-report-web-service-new-format/company-card-transaction-0

validate__elements = ValidateElements(
    ['required'],
    ['valid'] )

# See also: https://developer.concur.com/api-documentation/new-portal-format/expense-report-web-service-new-format/expense-delegator-resour-0

validate_Delegators_elements = ValidateElements(
    ['required'],
    ['valid'] )

# See also: https://developer.concur.com/api-documentation/new-portal-format/expense-report-web-service-new-format/expense-entry-attendee-r-0

validate_Attendees_elements = ValidateElements(
    ['required'],
    ['valid'] )

validate_Attendees_by_id_elements = ValidateElements(
    ['required'],
    ['valid'] )

# See also: https://developer.concur.com/api-documentation/new-portal-format/expense-report-web-service-new-format/expense-entry-attendee-r-1

validate_Attendees_1_elements = ValidateElements(
    ['required'],
    ['valid'] )

validate_Attendees_2_elements = ValidateElements(
    ['required'],
    ['valid'] )

# See also: https://developer.concur.com/api-documentation/new-portal-format/expense-report-web-service-new-format/expense-entry-itemizatio-0

validate_Itemization_elements = ValidateElements(
    ['required'],
    ['valid'] )

# See also: https://developer.concur.com/api-documentation/new-portal-format/expense-report-web-service-new-format/expense-entry-resource/exp

validate_entry_by_id_elements = ValidateElements(
    ['required'],
    ['valid'] )

# See also: https://developer.concur.com/api-documentation/new-portal-format/expense-report-web-service-new-format/expense-report-header-re-0

validate_report_elements = ValidateElements(
    ['required'],
    ['valid'] )

validate_batch_elements = ValidateElements(
    ['required'],
    ['valid'] )

# See also: https://developer.concur.com/api-documentation/new-portal-format/travel-profile-web-service-new-format/form-payment-resource/form

validate__1_elements = ValidateElements(
    ['required'],
    ['valid'] )

# See also: https://developer.concur.com/api-documentation/new-portal-format/travel-profile-web-service-new-format/loyalty-program-resource/l

validate_loyalty_elements = ValidateElements(
    ['required'],
    ['valid'] )

validate_loyalty_1_elements = ValidateElements(
    ['required'],
    ['valid'] )

# See also: https://developer.concur.com/api-documentation/new-portal-format/travel-profile-web-service-new-format/notification-subscriptio-0

validate__by_id_elements = ValidateElements(
    ['required'],
    ['valid'] )

# See also: https://developer.concur.com/api-documentation/oauth-20/get-or-refresh-oauth-token-using-web-flow

validate_oauth2_by_id_elements = ValidateElements(
    ['required'],
    ['valid'] )

# See also: https://developer.concur.com/api-documentation/oauth-20/oauth-access-token-resource/oauth-access-token-resource-get

validate_accesstokenashx_elements = ValidateElements(
    ['required'],
    ['valid'] )

validate_oauth2_by_id_1_elements = ValidateElements(
    ['required'],
    ['valid'] )

validate_oauth2_by_id_2_elements = ValidateElements(
    ['required'],
    ['valid'] )

# See also: https://developer.concur.com/api-documentation/oauth-20.1

validate_oauth2_by_id_3_elements = ValidateElements(
    ['required'],
    ['valid'] )

# See also: https://developer.concur.com/api-documentation/oauth-20.2

validate_oauth2_by_id_4_elements = ValidateElements(
    ['required'],
    ['valid'] )

# See also: https://developer.concur.com/api-documentation/web-services/attendee/attendee-resource/attendee-resource-get

validate_attendees_by_id_1_elements = ValidateElements(
    ['required'],
    ['valid'] )

# See also: https://developer.concur.com/api-documentation/web-services/attendee-list/attendee-type-resource/attendee-type-resource-get

validate_type_elements = ValidateElements(
    ['required'],
    ['valid'] )

# See also: https://developer.concur.com/api-documentation/web-services/expense-report/expense-entry-attendee-resource/v20-expense-entry-atte

validate_attendees_elements = ValidateElements(
    ['required'],
    ['valid'] )

validate_Attendees_3_elements = ValidateElements(
    ['required'],
    ['valid'] )

# See also: https://developer.concur.com/api-documentation/web-services/expense-report/expense-entry-resource/expense-entry-resource-post

validate__2_elements = ValidateElements(
    ['required'],
    ['valid'] )

# See also: https://developer.concur.com/api-documentation/web-services/expense-report/expense-form-field-resource/expense-form-field-resourc

validate_Fields_elements = ValidateElements(
    ['required'],
    ['valid'] )

# See also: https://developer.concur.com/api-documentation/web-services/expense-report/expense-form-resource/expense-form-resource-get

validate_Forms_elements = ValidateElements(
    ['required'],
    ['valid'] )

validate_RPTINFO_elements = ValidateElements(
    ['required'],
    ['valid'] )

# See also: https://developer.concur.com/api-documentation/web-services/expense-report/expense-group-configuration-resource/expense-group-con

validate__3_elements = ValidateElements(
    ['required'],
    ['valid'] )

# See also: https://developer.concur.com/api-documentation/web-services/expense-report/expense-report-resource/expense-report-resource-get

validate_status_elements = ValidateElements(
    ['required'],
    ['valid'] )

validate_Reports_by_id_elements = ValidateElements(
    ['required'],
    ['valid'] )

validate_Reports_by_id_1_elements = ValidateElements(
    ['required'],
    ['valid'] )

validate_Reports_by_id_2_elements = ValidateElements(
    ['required'],
    ['valid'] )

validate_Reports_by_id_3_elements = ValidateElements(
    ['required'],
    ['valid'] )

validate_Reports_by_id_4_elements = ValidateElements(
    ['required'],
    ['valid'] )

validate_reportcountry = ValidateElements(
    ['required'],
    ['valid'] )

validate_Reports_by_id_5_elements = ValidateElements(
    ['required'],
    ['valid'] )

validate_Reports_by_id_6_elements = ValidateElements(
    ['required'],
    ['valid'] )

validate_report_by_id_elements = ValidateElements(
    ['required'],
    ['valid'] )

# See also: https://developer.concur.com/api-documentation/web-services/expense-report/expense-report-resource/expense-report-resource-post

validate_Exceptions_elements = ValidateElements(
    ['required'],
    ['valid'] )

validate_submit_elements = ValidateElements(
    ['required'],
    ['valid'] )

validate_workflowaction_elements = ValidateElements(
    ['required'],
    ['valid'] )

# See also: https://developer.concur.com/api-documentation/web-services/expense-report/integration-status-resource/integration-status-resourc

validate_report_by_id_1_elements = ValidateElements(
    ['required'],
    ['valid'] )

# See also: https://developer.concur.com/api-documentation/web-services/expense-report/location-resource/location-resource-get

validate_v11_by_id_elements = ValidateElements(
    ['required'],
    ['valid'] )

# See also: https://developer.concur.com/api-documentation/web-services/extract/extract-definition-resource/extract-definition-resource-get

validate__4_elements = ValidateElements(
    ['required'],
    ['valid'] )

validate_v10_by_id_1_elements = ValidateElements(
    ['required'],
    ['valid'] )

# See also: https://developer.concur.com/api-documentation/web-services/extract/extract-file-resource/extract-file-resource-get

validate_file_elements = ValidateElements(
    ['required'],
    ['valid'] )

# See also: https://developer.concur.com/api-documentation/web-services/extract/extract-job-resource/extract-job-resource-get

validate_job_elements = ValidateElements(
    ['required'],
    ['valid'] )

validate_job_by_id_elements = ValidateElements(
    ['required'],
    ['valid'] )

validate_status_elements = ValidateElements(
    ['required'],
    ['valid'] )

# See also: https://developer.concur.com/api-documentation/web-services/extract/extract-job-resource/extract-job-resource-post

validate_job_1_elements = ValidateElements(
    ['required'],
    ['valid'] )

# See also: https://developer.concur.com/api-documentation/web-services/imaging/image-resource/image-resource-post

validate_receipt_elements = ValidateElements(
    ['required'],
    ['valid'] )

validate_expenseentry_by_id_elements = ValidateElements(
    ['required'],
    ['valid'] )

validate_invoice_by_id_elements = ValidateElements(
    ['required'],
    ['valid'] )

validate_report_by_id_2_elements = ValidateElements(
    ['required'],
    ['valid'] )

# See also: https://developer.concur.com/api-documentation/web-services/imaging/image-url-resource/image-url-resource-get

validate_receipt_by_id_elements = ValidateElements(
    ['required'],
    ['valid'] )

validate_report_by_id_3_elements = ValidateElements(
    ['required'],
    ['valid'] )

validate_expenseentry_by_id_1_elements = ValidateElements(
    ['required'],
    ['valid'] )

validate_invoice_by_id_1_elements = ValidateElements(
    ['required'],
    ['valid'] )
