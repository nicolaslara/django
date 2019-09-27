from asgiref.sync import sync_to_async
from asyncio import iscoroutinefunction
from django.utils.decorators import async_middleware
import inspect
import warnings


class RemovedInNextVersionWarning(DeprecationWarning):
    pass


class RemovedInDjango40Warning(PendingDeprecationWarning):
    pass


class warn_about_renamed_method:
    def __init__(self, class_name, old_method_name, new_method_name, deprecation_warning):
        self.class_name = class_name
        self.old_method_name = old_method_name
        self.new_method_name = new_method_name
        self.deprecation_warning = deprecation_warning

    def __call__(self, f):
        def wrapped(*args, **kwargs):
            warnings.warn(
                "`%s.%s` is deprecated, use `%s` instead." %
                (self.class_name, self.old_method_name, self.new_method_name),
                self.deprecation_warning, 2)
            return f(*args, **kwargs)
        return wrapped


class RenameMethodsBase(type):
    """
    Handles the deprecation paths when renaming a method.

    It does the following:
        1) Define the new method if missing and complain about it.
        2) Define the old method if missing.
        3) Complain whenever an old method is called.

    See #15363 for more details.
    """

    renamed_methods = ()

    def __new__(cls, name, bases, attrs):
        new_class = super().__new__(cls, name, bases, attrs)

        for base in inspect.getmro(new_class):
            class_name = base.__name__
            for renamed_method in cls.renamed_methods:
                old_method_name = renamed_method[0]
                old_method = base.__dict__.get(old_method_name)
                new_method_name = renamed_method[1]
                new_method = base.__dict__.get(new_method_name)
                deprecation_warning = renamed_method[2]
                wrapper = warn_about_renamed_method(class_name, *renamed_method)

                # Define the new method if missing and complain about it
                if not new_method and old_method:
                    warnings.warn(
                        "`%s.%s` method should be renamed `%s`." %
                        (class_name, old_method_name, new_method_name),
                        deprecation_warning, 2)
                    setattr(base, new_method_name, old_method)
                    setattr(base, old_method_name, wrapper(old_method))

                # Define the old method as a wrapped call to the new method.
                if not old_method and new_method:
                    setattr(base, old_method_name, wrapper(new_method))

        return new_class


class DeprecationInstanceCheck(type):
    def __instancecheck__(self, instance):
        warnings.warn(
            "`%s` is deprecated, use `%s` instead." % (self.__name__, self.alternative),
            self.deprecation_warning, 2
        )
        return super().__instancecheck__(instance)


@async_middleware
class MiddlewareMixin:
    def __init__(self, get_response=None):
        print(f'FIXME: MiddlewareMixin.__init__({type(self).__name__}): get_response={get_response!r}')
        self.get_response = get_response
        if hasattr(self, 'process_request'):  # FIXME: iscoroutinefunction...
            self.process_request = sync_to_async(self.process_request)
        if hasattr(self, 'get_response') and not iscoroutinefunction(self.get_response):
            print('FIXME: wrapping get_response')
            self.get_response = sync_to_async(self.get_response)
        if hasattr(self, 'process_response'):  # FIXME: iscoroutinefunction...
            self.process_response = sync_to_async(self.process_response)
        super().__init__()

    async def __call__(self, request):
        response = None
        if hasattr(self, 'process_request'):
            response = await self.process_request(request)
        print(f'FIXME: MiddlewareMixin after process_request: response={response!r}')
        import pdb; pdb.set_trace()  # FIXME
        response = response or await self.get_response(request)
        print(f'FIXME: MiddlewareMixin after get_response: response={response!r}')
        if hasattr(self, 'process_response'):
            response = await self.process_response(request, response)
        return response
