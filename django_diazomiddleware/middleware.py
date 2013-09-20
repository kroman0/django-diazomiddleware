from pkg_resources import resource_filename
from urlparse import urlsplit
from django.conf import settings
from repoze.xmliter.utils import getHTMLSerializer
from lxml import etree
from diazo.compiler import compile_theme
from diazo.compiler import quote_param
from django import http
from django.core import urlresolvers
from django.core.handlers import base as basehandler
from django.utils import datastructures
try:
    from threading import local
except ImportError:
    from django.utils._threading_local import local


_thread_locals = local()
DevelopmentMode = settings.DEBUG
CACHE = {}
TRUE = (u'1', u'y', u'yes', u't', u'true')


def get_request():
    return getattr(_thread_locals, 'request', None)


class NetworkResolver(etree.Resolver):

    """Resolver for network urls
    """

    def resolve(self, system_url, public_id, context):
        if '://' in system_url and system_url != 'file:///__diazo__':
            return self.resolve_filename(system_url, context)


class PythonResolver(etree.Resolver):

    """Resolver for python:// paths
    """

    def resolve(self, system_url, public_id, context):
        if not system_url.lower().startswith('python://'):
            return None
        filename = resolvePythonURL(system_url)
        return self.resolve_filename(filename, context)


def resolvePythonURL(url):
    """Resolve the python resource url to it's path

    This can resolve python://dotted.package.name/file/path URLs to paths.
    """
    assert url.lower().startswith('python://')
    spec = url[9:]
    package, resource_name = spec.split('/', 1)
    return resource_filename(package, resource_name)


def getParser(type, read_network):
    """Set up a parser for either rules, theme or compiler
    """

    if type == 'rules':
        parser = etree.XMLParser(recover=False)
    elif type == 'theme':
        parser = etree.HTMLParser()
    elif type == 'compiler':
        parser = etree.XMLParser()
    parser.resolvers.add(InternalResolver())
    parser.resolvers.add(PythonResolver())
    if read_network:
        parser.resolvers.add(NetworkResolver())
    return parser


def compileThemeTransform(rules, absolutePrefix=None, read_network=False,
                          parameterExpressions=None, runtrace=False):
    """
    Prepare the theme transform by compiling the rules with the given options
    """

    if parameterExpressions is None:
        parameterExpressions = {}

    accessControl = etree.XSLTAccessControl(
        read_file=True, write_file=False, create_dir=False,
        read_network=read_network, write_network=False
    )

    # if absolutePrefix:
        # IMPORT
        #absolutePrefix = expandAbsolutePrefix(absolutePrefix)

    params = set(parameterExpressions.keys() +
                 ['url', 'base', 'path', 'scheme', 'host'])
    xslParams = dict((k, '') for k in params)

    compiledTheme = compile_theme(rules,
                                  absolute_prefix=absolutePrefix,
                                  parser=getParser('theme', read_network),
                                  rules_parser=getParser('rules', read_network),
                                  compiler_parser=getParser(
                                      'compiler', read_network),
                                  read_network=read_network,
                                  access_control=accessControl,
                                  update=True,
                                  xsl_params=xslParams,
                                  runtrace=runtrace,
                                  )

    if not compiledTheme:
        return None

    return etree.XSLT(compiledTheme,
                      access_control=accessControl,
                      )


class InternalResolver(etree.Resolver):

    """Resolver for internal absolute and relative paths (excluding protocol).
    If the path starts with a /, it will be resolved relative to the Plone
    site navigation root.
    """

    def resolve(self, system_url, public_id, context):
        # Ignore URLs with a scheme
        if '://' in system_url:
            return None

        # Ignore the special 'diazo:' resolvers
        if system_url.startswith('diazo:'):
            return None

        # IMPORT
        #context = findContext(request)
        # portalState = queryMultiAdapter(
            #(context, request), name=u"plone_portal_state")

        # if portalState is None:
            #root = None
        # else:
            #root = portalState.navigation_root()

        if not system_url.startswith('/'):  # only for relative urls
            request = get_request()
            path = request.path
            system_url = '%s/%s' % (path, system_url)

        # IMPORT
        response = subrequest(system_url)
        # if response.status_code != 200:
            # return self.resolve_string('', context)
        result = response.content
        content_type = response['Content-Type']
        encoding = None
        if content_type is not None and ';' in content_type:
            content_type, encoding = content_type.split(';', 1)
        if encoding is None:
            encoding = response._charset
        else:
            # e.g. charset=utf-8
            encoding = encoding.split('=', 1)[1].strip()
        result = result.decode(encoding).encode('ascii', 'xmlcharrefreplace')

        if content_type in ('text/javascript', 'application/x-javascript'):
            result = ''.join([
                '<html><body><script type="text/javascript">',
                result,
                '</script></body></html>',
            ])
        elif content_type == 'text/css':
            result = ''.join([
                '<html><body><style type="text/css">',
                result,
                '</style></body></html>',
            ])

        return self.resolve_string(result, context)


def isThemeEnabled(request, response, settings=None):
    """Determine if a theme is enabled for the given request
    """

    # Disable theming if the response sets a header
    if response.get('X-Theme-Disabled', None):
        return False

    # Disable theming subrequest
    if getattr(request, 'diazo_subrequest', False):
        return False

    # Check for diazo.off request parameter
    if (DevelopmentMode and request.GET.get(u'diazo.off', u'').lower() in TRUE):
        return False

    if not settings.get('enabled') or not settings.get('rules'):
        return False

    return True


def prepareThemeParameters(request, parameterExpressions):
    """Prepare and return a dict of parameter expression values.
    """

    # Find real or virtual path - PATH_INFO has VHM elements in it
    url = request.build_absolute_uri()

    # Find the host name
    path = request.path
    base = url[:-len(path)]
    parts = urlsplit(url)

    params = dict(
        url=quote_param(url),
        base=quote_param(base),
        path=quote_param(path),
        scheme=quote_param(parts.scheme),
        host=quote_param(parts.netloc),
    )

    # Add expression-based parameters
    if parameterExpressions:

        for name, expression in parameterExpressions.items():
            if callable(expression):
                params[name] = quote_param(expression(request))
            else:
                params[name] = quote_param(expression)

    return params


def get_response(url, request, get_query):
    subrequest = http.HttpRequest()
    for attname, attvalue in vars(request).items():
        setattr(subrequest, attname, attvalue)
    subrequest.method = 'GET'
    subrequest.GET = get_query
    subrequest.REQUEST = get_query
    subrequest.diazo_subrequest = True

    # if this view_func has an URL, set the path info
    # to reflect what the url should be
    try:
        subrequest.path = subrequest.path_info = url
    except urlresolvers.NoReverseMatch:
        subrequest.path = subrequest.path_info = '/'

    # since we've cloned the request, we need to apply
    # the middleware to the cloned request
    handler = basehandler.BaseHandler()
    handler.load_middleware()
    response = handler.get_response(subrequest)
    return response


def subrequest(url):
    request = get_request()
    get_query = datastructures.MultiValueDict()
    response = get_response(url, request, get_query)
    return response


def parseTree(response):
    contentType = response.get('Content-Type', None)
    if contentType is None or not contentType.startswith('text/html'):
        return None

    contentEncoding = response.get('Content-Encoding', None)
    if contentEncoding and contentEncoding in ('zip', 'deflate', 'compress',):
        return None

    try:
        return getHTMLSerializer(response.content, pretty_print=False)
    except (TypeError, etree.ParseError):
        return None


def getSettings():
    return getattr(settings, 'DIAZO_SETTINGS')


def setupTransform(request, response, runtrace=False):

    # Obtain settings. Do nothing if not found
    settings = getSettings()

    # Apply theme
    transform = None

    if not DevelopmentMode:
        transform = CACHE.get(0)

    if transform is None:
        rules = settings.get('rules')
        absolutePrefix = settings.get('prefix') or None
        read_network = settings.get('read_network')
        parameterExpressions = settings.get('parameter_expressions')

        transform = compileThemeTransform(
            rules, absolutePrefix, read_network, parameterExpressions, runtrace=runtrace)
        if transform is None:
            return None

        if not DevelopmentMode:
            CACHE[0] = transform

    return transform


class DiazoMiddleware(object):

    """
    This middleware compresses content if the browser allows gzip compression.
    It sets the Vary header accordingly, so that caches will base their storage
    on the Accept-Encoding header.
    """

    def process_request(self, request):
        _thread_locals.request = request

    def process_response(self, request, response):
        settings = getSettings()

        if settings is None or not isThemeEnabled(request, response, settings):
            return response

        result = parseTree(response)
        if result is None:
            return response

        runtrace = (DevelopmentMode and request.GET.get(u'diazo.debug', u'').lower() in TRUE)

        try:
            etree.clear_error_log()

            if settings.get('doctype'):
                result.doctype = settings.get('doctype')
                if not result.doctype.endswith('\n'):
                    result.doctype += '\n'

            transform = setupTransform(request, response, runtrace)
            if transform is None:
                return response

            parameterExpressions = settings.get('parameter_expressions') or {}
            params = prepareThemeParameters(request, parameterExpressions)

            transformed = transform(result.tree, **params)
            error_log = transform.error_log
            if transformed is not None:
                # Transformed worked, swap content with result
                result.tree = transformed
        except etree.LxmlError as e:
            if not(DevelopmentMode):
                raise
            error_log = e.error_log
            runtrace = True

        if runtrace:
            from diazo.runtrace import generate_debug_html
            # Add debug information to end of body
            base_url = request.build_absolute_uri()[:-len(request.path)]
            body = result.tree.xpath('/html/body')
            if body:
                body = body[0]
            else:
                html = result.tree.xpath('/html')[0]
                body = etree.Element('body')
                html.append(body)
            body.insert(-1, generate_debug_html(
                base_url + '/diazo-debug',
                rules=settings.get('rules'),
                rules_parser=getParser('rules', settings.get('read_network')),
                error_log=error_log,
            ))

        response.content = str(result)
        if settings.get('update_content_length'):
            response['Content-Length'] = str(len(response.content))
        return response
