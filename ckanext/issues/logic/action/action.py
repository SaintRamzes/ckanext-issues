import logging

from datetime import datetime

import ckan.logic as logic
import ckan.plugins as p
import ckan.model as model
from ckan.logic import validate
import ckanext.issues.model as issuemodel
from ckanext.issues.logic import schema

NotFound = logic.NotFound
_get_or_bust = logic.get_or_bust

log = logging.getLogger(__name__)


def issue_show(context, data_dict=None):
    '''Return a single issue.

    :param id: the id of the issue to show
    :type id: string

    :rtype: dictionary
    '''
    id = _get_or_bust(data_dict, 'id')
    issue = issuemodel.Issue.get(id)
    context['issue'] = issue
    if issue is None:
        raise NotFound
    issue_dict = issue.as_dict()
    p.toolkit.check_access('issue_show', context, issue_dict)
    return issue_dict


def issue_create(context, data_dict):
    '''Add a new issue.

    You must provide your API key in the Authorization header.

    :param title: the title of the issue
    :type title: string
    :param description: the description of the issue item (optional)
    :type description: string
    :param dataset_id: the name or id of the dataset that the issue item
        belongs to (optional)
    :type dataset_id: string

    :returns: the newly created issue item
    :rtype: dictionary
    '''
    p.toolkit.check_access('issue_create', context, data_dict)
    # validated_data_dict, errors = p.toolkit.navl_validate(
    #     data_dict,
    #     schema.issue_create_schema(),
    #     context
    # )
    # if errors:
    #    raise p.toolkit.ValidationError(errors)

    user = context['user']
    user_obj = model.User.get(user)
    data_dict['user_id'] = user_obj.id

    # data, errors = _validate(
    #     data_dict, ckan.logic.schema.default_related_schema(), context)
    # if errors:
    #     model.Session.rollback()
    #     raise ValidationError(errors)
    dataset = model.Package.get(data_dict['dataset_id'])
    # TODO propoer validation?
    if dataset is None:
        raise p.toolkit.ValidationError({
            'dataset_id': [
                'No dataset exists with id %s' % data_dict['dataset_id']
            ]
        })
    del data_dict['dataset_id']

    issue = issuemodel.Issue(**data_dict)
    issue.dataset = dataset
    model.Session.add(issue)
    model.Session.commit()

    log.debug('Created issue %s (%s)' % (issue.title, issue.id))
    return issue.as_dict()


def issue_update(context, data_dict):
    '''Update an issue.

    You must provide your API key in the Authorization header.

    :param title: the title of the issue
    :type title: string
    :param description: the description of the issue item (optional)
    :type description: string
    :param dataset_id: the name or id of the dataset that the issue item
        belongs to (optional)
    :type dataset_id: string

    :returns: the newly updated issue item
    :rtype: dictionary
    '''
    p.toolkit.check_access('issue_update', context, data_dict)
    validated_data_dict, errors = p.toolkit.navl_validate(
        data_dict,
        schema.issue_update_schema(),
        context
    )
    if errors:
        raise p.toolkit.ValidationError(errors)

    # TODO:fix below to use validated_data_dict,
    #      and move validation into the schema

    issue = issuemodel.Issue.get(data_dict['id'])
    status_change = data_dict.get('status') and (data_dict.get('status') !=
                                                 issue.status)

    ignored_keys = ['id', 'created', 'user', 'dataset_id']
    for k, v in data_dict.items():
        if k not in ignored_keys:
            setattr(issue, k, v)

    if status_change:
        if data_dict['status'] == issuemodel.ISSUE_STATUS.closed:
            issue.resolved = datetime.now()
            user = context['user']
            user_obj = model.User.get(user)
            issue.resolver_id = user_obj.id
        elif data_dict['status'] == issuemodel.ISSUE_STATUS.open:
            issue.resolved = None
            issue.resolver = None

    model.Session.add(issue)
    model.Session.commit()
    return issue.as_dict()


def issue_comment_create(context, data_dict):
    '''Add a new issue comment.

    You must provide your API key in the Authorization header.

    :param comment: the comment text
    :type comment: string
    :param issue_id: the id of the issue the comment belongs to
    :type dataset_id: integer

    :returns: the newly created issue comment
    :rtype: dictionary
    '''
    user = context['user']
    user_obj = model.User.get(user)

    issue = issuemodel.Issue.get(data_dict['issue_id'])
    if issue is None:
        raise p.toolkit.ValidationError({
            'issue_id': ['No issue exists with id %s' % data_dict['issue_id']]
        })

    auth_dict = {'dataset_id': issue.dataset_id}
    p.toolkit.check_access('issue_comment_create', context, auth_dict)

    data_dict['user_id'] = user_obj.id

    issue = issuemodel.IssueComment(**data_dict)
    model.Session.add(issue)
    model.Session.commit()

    log.debug('Created issue comment %s' % (issue.id))

    return issue.as_dict()


@p.toolkit.side_effect_free
@validate(schema.issue_list_schema)
def issue_list(context, data_dict):
    '''List issues for a given dataset'''
    p.toolkit.check_access('issue_show', context, data_dict)

    return list(issuemodel.Issue.get_issues_for_dataset(
        session=context['session'],
        **data_dict))
