from collections import OrderedDict

from .base import BaseOptions, BaseType
from .field import Field
from .inputfield import InputField
from .objecttype import ObjectType
from .scalars import Scalar
from .structures import List, NonNull
from .unmountedtype import UnmountedType
from .utils import yank_fields_from_attrs

# For static type checking with Mypy
MYPY = False
if MYPY:
    from typing import Dict, Callable  # NOQA


class InputObjectTypeOptions(BaseOptions):
    fields = None  # type: Dict[str, InputField]
    create_container = None  # type: Callable


class InputObjectTypeContainer(dict, BaseType):
    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        for key in self._meta.fields.keys():
            field = getattr(self, key, None)
            if field is None or self.get(key, None) is None:
                value = None
            else:
                value = InputObjectTypeContainer._get_typed_field_value(field, self[key])
            setattr(self, key, value)

    def __init_subclass__(cls, *args, **kwargs):
        pass

    @staticmethod
    def _get_typed_field_value(field_or_type, value):
        if isinstance(field_or_type, NonNull):
            return InputObjectTypeContainer._get_typed_field_value(field_or_type.of_type, value)
        elif isinstance(field_or_type, List):
            return [
                InputObjectTypeContainer._get_typed_field_value(field_or_type.of_type, v)
                for v in value
            ]
        elif hasattr(field_or_type, '_meta') and hasattr(field_or_type._meta, 'container'):
            return field_or_type._meta.container(value)
        else:
            return value

class InputObjectType(UnmountedType, BaseType):
    '''
    Input Object Type Definition

    An input object defines a structured collection of fields which may be
    supplied to a field argument.

    Using `NonNull` will ensure that a value must be provided by the query
    '''

    @classmethod
    def __init_subclass_with_meta__(cls, container=None, **options):
        _meta = InputObjectTypeOptions(cls)

        fields = OrderedDict()
        for base in reversed(cls.__mro__):
            fields.update(
                yank_fields_from_attrs(base.__dict__, _as=InputField)
            )

        _meta.fields = fields
        if container is None:
            container = type(cls.__name__, (InputObjectTypeContainer, cls), {})
        _meta.container = container
        super(InputObjectType, cls).__init_subclass_with_meta__(_meta=_meta, **options)

    @classmethod
    def get_type(cls):
        '''
        This function is called when the unmounted type (InputObjectType instance)
        is mounted (as a Field, InputField or Argument)
        '''
        return cls
