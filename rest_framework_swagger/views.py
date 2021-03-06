import json
from django.utils import six

from django.views.generic import View
from django.utils.safestring import mark_safe
from django.utils.encoding import smart_text
from django.shortcuts import render_to_response, RequestContext
from django.core.exceptions import PermissionDenied
from .compat import import_string

from rest_framework.views import Response
from rest_framework.settings import api_settings
from rest_framework.utils import formatting

from rest_framework_swagger.urlparser import UrlParser
from rest_framework_swagger.apidocview import APIDocView
from rest_framework_swagger.docgenerator import DocumentationGenerator

import rest_framework_swagger as rfs


try:
    JSONRenderer = list(filter(
        lambda item: item.format == 'json',
        api_settings.DEFAULT_RENDERER_CLASSES,
    ))[0]
except IndexError:
    from rest_framework.renderers import JSONRenderer


def get_restructuredtext(view_cls, html=False):
    from docutils import core

    description = view_cls.__doc__ or ''
    description = formatting.dedent(smart_text(description))
    if html:
        parts = core.publish_parts(source=description, writer_name='html')
        html = parts['body_pre_docinfo'] + parts['fragment']
        return mark_safe(html)
    return description


def get_full_base_path(request):
    try:
        base_path = rfs.SWAGGER_SETTINGS['base_path']
    except KeyError:
        return request.build_absolute_uri(request.path).rstrip('/')
    else:
        protocol = 'https' if request.is_secure() else 'http'
        return '{0}://{1}'.format(protocol, base_path.rstrip('/'))


class SwaggerUIView(View):
    def get(self, request, *args, **kwargs):

        if not self.has_permission(request):
            return self.handle_permission_denied(request)

        template_name = rfs.SWAGGER_SETTINGS.get('template_path')
        data = {
            'swagger_settings': {
                'discovery_url': "%s/swagger.json" % get_full_base_path(request),
                'api_key': rfs.SWAGGER_SETTINGS.get('api_key', ''),
                'token_type': rfs.SWAGGER_SETTINGS.get('token_type'),
                'enabled_methods': mark_safe(
                    json.dumps(rfs.SWAGGER_SETTINGS.get('enabled_methods'))),
                'doc_expansion': rfs.SWAGGER_SETTINGS.get('doc_expansion', ''),
            }
        }
        response = render_to_response(
            template_name, RequestContext(request, data))

        return response

    def has_permission(self, request):
        if rfs.SWAGGER_SETTINGS.get('is_superuser') and \
                not request.user.is_superuser:
            return False

        if rfs.SWAGGER_SETTINGS.get('is_authenticated') and \
                not request.user.is_authenticated():
            return False

        return True

    def handle_permission_denied(self, request):
        permission_denied_handler = rfs.SWAGGER_SETTINGS.get(
            'permission_denied_handler')
        if isinstance(permission_denied_handler, six.string_types):
            permission_denied_handler = import_string(
                permission_denied_handler)

        if permission_denied_handler:
            return permission_denied_handler(request)
        else:
            raise PermissionDenied()


# class SwaggerResourcesView(APIDocView):
#     renderer_classes = (JSONRenderer,)

#     def get(self, request):
#         apis = []
#         resources = self.get_resources()

#         for path in resources:
#             apis.append({
#                 'path': "/%s" % path,
#             })

#         return Response({
#             'apiVersion': rfs.SWAGGER_SETTINGS.get('api_version', ''),
#             'swaggerVersion': '1.2',
#             'basePath': self.get_base_path(),
#             'apis': apis,
#             'info': rfs.SWAGGER_SETTINGS.get('info', {
#                 'contact': '',
#                 'description': '',
#                 'license': '',
#                 'licenseUrl': '',
#                 'termsOfServiceUrl': '',
#                 'title': '',
#             }),
#         })

    # def get_base_path(self):
    #     try:
    #         base_path = rfs.SWAGGER_SETTINGS['base_path']
    #     except KeyError:
    #         return self.request.build_absolute_uri(
    #             self.request.path).rstrip('/')
    #     else:
    #         protocol = 'https' if self.request.is_secure() else 'http'
    #         return '{0}://{1}/{2}'.format(protocol, base_path, 'swagger.json')




class SwaggerView(APIDocView):
    renderer_classes = (JSONRenderer,)

    def get(self, request, *args, **kwargs):
        apis = []
        resources = self.get_resources()

        for path in resources:
            apis.append(
                self.get_api_for_resource(path)
            )

        generator = DocumentationGenerator()

        #parameters = generator.get_models(apis)

        tags = {}
        paths = {}
        # TODO: reformat the contents that come from generator, don't
        # post-process it here.
        for path in generator.generate(apis):
            mypath = {}

            try:
                tag = path['path'].split('/')[2]
            except IndexError:
                tag = None

            for operation in path.get('operations', []):

                # {
                #     'parameters': [
                #         {'name': 'cigar', 'paramType': 'form', 'required': True, 'type': 'string', 'description': ''},
                #         {'name': 'jambalaya', 'paramType': 'form', 'required': True, 'type': 'string', 'description': ''}
                #     ],
                #     'nickname': u'Drop_Cigar_In_Jambalaya_POST',
                #     'notes': u'<p>Make a cigar jambalaya</p>',
                #     'summary': u'Make a cigar jambalaya',
                #     'type': 'CigarJambalayaSerializer',
                #     'method': 'POST'
                # }",
                responses = {}

                response_messages = operation.get('responseMessages', [])
                if len(response_messages) == 0:
                    responses['default'] = {'description': 'Unknown'}

                for response in response_messages:
                    responses[response['code']] = {
                        'description': response['message']
                    }

                    # TODO : this is almost certainly wrong
                    if response['responseModel']:
                        response[response['code']]['schema'] = {
                            "$ref": response['responseModel']
                        }


                method = operation['method'].lower()
                mypath[method] = {
                    #'debug': operation,
                    'description': operation['notes'],
                    'summary': operation['summary'],
                    'operationId': operation['nickname'],
                    'produces': [
                        'application/json'
                    ],
                    'parameters': operation.get('parameters', []),
                    'responses': responses
                }

                if tag:
                    mypath[method]["tags"] = [tag]

            if tag and tag not in tags:
                tags[tag] = {
                    'name': tag,
                    'description': tag
                }

            paths[path['path']] = mypath

        tag_list = []
        for tag in tags:
            tag_list.append(tag)

        definitions = {}
        securityDefinitions = {}
        security = []
        externalDocs = {}

        full_uri = self.api_full_uri.rstrip('/').split('/')
        scheme = full_uri[0].rstrip(':')
        host = '/'.join(full_uri[2:3])
        basePath = "/" + '/'.join(full_uri[3:])

        return Response({
            'swagger': '2.0',
            'info': rfs.SWAGGER_SETTINGS['info'],
            'host': host,
            'basePath': basePath,
            'schemes': [scheme],
            'consumes': ['application/json'],
            'produces': ['application/json'],

            'paths': paths,
            'definitions': definitions,
            #'parameters': parameters,
            'responses': {},
            'securityDefinitions': securityDefinitions,
            'security': security
        })

    def get_api_for_resource(self, filter_path):
        urlparser = UrlParser()
        urlconf = getattr(self.request, "urlconf", None)
        return urlparser.get_apis(urlconf=urlconf, filter_path=filter_path)

    def get_resources(self):
        urlparser = UrlParser()
        urlconf = getattr(self.request, "urlconf", None)
        apis = urlparser.get_apis(
            urlconf=urlconf,
            exclude_namespaces=rfs.SWAGGER_SETTINGS.get('exclude_namespaces'))
        resources = urlparser.get_top_level_apis(apis)
        return resources

# class SwaggerApiView(APIDocView):
#     renderer_classes = (JSONRenderer,)

#     def get(self, request, path):
#         apis = self.get_api_for_resource(path)
#         generator = DocumentationGenerator()

#         return Response({
#             'apiVersion': rfs.SWAGGER_SETTINGS.get('api_version', ''),
#             'swaggerVersion': '1.2',
#             'basePath': self.api_full_uri.rstrip('/'),
#             'resourcePath': '/' + path,
#             'apis': generator.generate(apis),
#             'models': generator.get_models(apis),
#         })

#     def get_api_for_resource(self, filter_path):
#         urlparser = UrlParser()
#         urlconf = getattr(self.request, "urlconf", None)
#         return urlparser.get_apis(urlconf=urlconf, filter_path=filter_path)
