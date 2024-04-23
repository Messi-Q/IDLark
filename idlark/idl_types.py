# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

INTEGER_TYPES = frozenset([
    'byte',
    'octet',
    'short',
    'unsigned short',
    'long',
    'unsigned long',
    'long long',
    'unsigned long long',
])

FLOATING_TYPES = frozenset([
    'float',
    'unrestricted float',
    'double',
    'unrestricted double',
])

NUMERIC_TYPES = (INTEGER_TYPES | FLOATING_TYPES)
PRIMITIVE_TYPES = (frozenset(['boolean']) | NUMERIC_TYPES)
BASIC_TYPES = (
    PRIMITIVE_TYPES | frozenset([
        'DOMString',
        'ByteString',
        'USVString',
        'void',
        'undefined'
    ])
)
TYPE_NAMES = {
    'any': 'Any',
    'boolean': 'Boolean',
    'byte': 'Byte',
    'octet': 'Octet',
    'short': 'Short',
    'unsigned short': 'UnsignedShort',
    'long': 'Long',
    'unsigned long': 'UnsignedLong',
    'long long': 'LongLong',
    'unsigned long long': 'UnsignedLongLong',
    'float': 'Float',
    'unrestricted float': 'UnrestrictedFloat',
    'double': 'Double',
    'unrestricted double': 'UnrestrictedDouble',
    'DOMString': 'String',
    'ByteString': 'ByteString',
    'USVString': 'USVString',
    'object': 'Object',
}

STRING_TYPES = frozenset([
    'String',
    'ByteString',
    'USVString',
])

EXTENDED_ATTRIBUTES_APPLICABLE_TO_TYPES = frozenset([
    'AllowShared',
    'Clamp',
    'EnforceRange',
    'StringContext',
    'TreatNullAs',
])

class IdlTypeBase:
    """Base class for IdlType, IdlUnionType, IdlArrayTypeBase
    and IdlNullableType.
    """

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name

    def __eq__(self, other:"IdlTypeBase"):
        raise NotImplementedError('__eq__() should be defined in subclasses')

    def __ne__(self, other:"IdlTypeBase"):
        return not self.__eq__(other)

    def __hash__(self) -> int:
        raise NotImplementedError('__hash__() should be defined in subclasses')

    @property
    def name(self) -> str:
        raise NotImplementedError('name should be defined in subclasses')

class IdlType(IdlTypeBase):

    def __init__(self, base_type:str, is_unrestricted:bool=False):
        if is_unrestricted:
            self.base_type = 'unrestricted %s' % base_type
        else:
            self.base_type = base_type

    @property
    def is_basic_type(self):
        return self.base_type in BASIC_TYPES

    @property
    def is_integer_type(self):
        return self.base_type in INTEGER_TYPES

    @property
    def is_floating_type(self):
        return self.base_type in FLOATING_TYPES

    @property
    def is_void(self):
        return self.base_type == 'void'

    @property
    def is_numeric_type(self):
        return self.base_type in NUMERIC_TYPES

    @property
    def is_primitive_type(self):
        return self.base_type in PRIMITIVE_TYPES

    @property
    def is_string_type(self):
        return self.name in STRING_TYPES

    def __eq__(self, other:"IdlType"):
        if not isinstance(other, IdlType): return False
        return self.base_type == other.base_type

    def __ne__(self, other:"IdlType"):
        if not isinstance(other, IdlType): return False
        return self.base_type != other.base_type

    def __hash__(self) -> int:
        return hash(self.base_type)

    @property
    def name(self):
        base_type = self.base_type
        return TYPE_NAMES.get(base_type, base_type)

class IdlNestedType(IdlTypeBase):
    def __init__(self, nested_type:IdlTypeBase=None, member_types:list[IdlTypeBase]=None):
        assert nested_type or member_types
        self.member_types:list[IdlTypeBase] = [nested_type] if not member_types else member_types
        self.nested_type:IdlTypeBase = nested_type

    def has_type(self, type_name:str):
        for member in self.member_types:
            if isinstance(member, IdlNestedType):
                if member.has_type(type_name):
                    return True
            else:
                if member.name == type_name:
                    return True
        return False

    def get_nested_type(self) -> IdlTypeBase:
        return self.nested_type

    def get_types(self) -> list[IdlTypeBase]:
        return self.member_types

class IdlPromiseType(IdlNestedType):

    def __init__(self, nested_type: IdlTypeBase):
        IdlNestedType.__init__(self, nested_type=nested_type)

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other:"IdlPromiseType"):
        if not isinstance(other, IdlPromiseType): return False
        return self.name == other.name

    @property
    def name(self):
        all_types = ', '.join(member_type.name for member_type in self.member_types)
        return f"Promise({all_types})"

class IdlUnionType(IdlNestedType):
    def __init__(self, member_types:list[IdlTypeBase]):
        IdlNestedType.__init__(self, member_types=list(set(member_types)))
        self.member_types.sort(key=lambda t: t.name)

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other:"IdlUnionType"):
        if not isinstance(other, IdlUnionType): return False
        return other and self.name == other.name

    @property
    def number_of_nullable_member_types(self):
        count = 0
        for member in self.member_types:
            if isinstance(member, IdlNullableType):
                count += 1
                member = member.nested_type
            if isinstance(member, IdlUnionType):
                count += member.number_of_nullable_member_types
        return count

    @property
    def name(self):
        all_types = ', '.join(member_type.name for member_type in self.member_types)
        return f"Union({all_types})"

    @property
    def member_names(self):
        return [member.name for member in self.member_types]

class IdlArrayTypeBase(IdlNestedType):
    """Base class for array-like types."""

    def __init__(self, element_type:IdlTypeBase):
        IdlNestedType.__init__(self, nested_type=element_type)
        self.element_type = element_type

class IdlSequenceType(IdlArrayTypeBase):
    def __init__(self, element_type:IdlTypeBase):
        IdlArrayTypeBase.__init__(self, element_type)

    def __eq__(self, other:"IdlSequenceType"):
        if not isinstance(other, IdlSequenceType): return False
        return other and self.name == other.name

    def __hash__(self):
        return hash(self.element_type)

    @property
    def name(self):
        return f"Sequence({self.element_type.name})"

class IdlFrozenArrayType(IdlArrayTypeBase):
    def __init__(self, element_type:IdlTypeBase):
        IdlArrayTypeBase.__init__(self, element_type)

    def __eq__(self, other:"IdlFrozenArrayType"):
        if not isinstance(other, IdlFrozenArrayType): return False
        return other and self.name == other.name

    def __hash__(self):
        return hash(self.element_type)

    @property
    def name(self):
        return f"FrozenArray({self.element_type.name})"

class IdlObservableArrayType(IdlArrayTypeBase):

    def __init__(self, element_type:IdlTypeBase):
        IdlArrayTypeBase.__init__(self, element_type)

    def __eq__(self, other:"IdlObservableArrayType"):
        if not isinstance(other, IdlObservableArrayType): return False
        return other.name == self.name

    def __hash__(self):
        return hash(self.name)

    def __repr__(self) -> str:
        return self.name

    __str__ : __repr__

    @property
    def name(self):
        return f"ObservableArray({self.element_type.name})"

class IdlRecordType(IdlTypeBase):
    def __init__(self, key_type:IdlTypeBase, value_type:IdlTypeBase):
        IdlTypeBase.__init__(self)
        self.key_type = key_type
        self.value_type = value_type
        assert not isinstance(key_type, IdlNestedType)

    def __eq__(self, other:"IdlRecordType"):
        if not isinstance(other, IdlRecordType): return False
        return self.key_type == other.key_type and self.value_type == other.value_type

    def __ne__(self, other:"IdlRecordType"):
        return not (self.key_type == other.key_type and self.value_type == other.value_type)

    def __hash__(self) -> int:
        return hash((self.key_type.name, self.value_type.name))

    @property
    def name(self):
        return f"Record({self.key_type.name}, {self.value_type.name})"

class IdlNullableType(IdlNestedType):
    def __init__(self, nested_type:IdlTypeBase):
        IdlNestedType.__init__(self, nested_type=nested_type)
        if nested_type.name == 'Any':
            raise ValueError('Inner type of nullable type must not be any.')
        if isinstance(nested_type, IdlPromiseType):
            raise ValueError(
                'Inner type of nullable type must not be a promise.')
        if isinstance(nested_type, IdlNullableType):
            raise ValueError(
                'Inner type of nullable type must not be a nullable type.')
        if isinstance(nested_type, IdlUnionType):
            if nested_type.number_of_nullable_member_types > 0:
                raise ValueError(
                    'Inner type of nullable type must not be a union type that '
                    'itself includes a nullable type.')

    def __eq__(self, other:"IdlNullableType"):
        if not isinstance(other, IdlNullableType): return False
        return other and self.nested_type == other.nested_type

    def __ne__(self, other:"IdlNullableType"):
        if not isinstance(other, IdlNullableType): return False
        return other and not (self.nested_type == other.nested_type)

    def __hash__(self):
        return hash(self.nested_type)

    @property
    def name(self):
        return self.nested_type.name

class IdlAnnotatedType(IdlNestedType):
    def __init__(self, nested_type:IdlTypeBase, extended_attributes):
        IdlNestedType.__init__(self, nested_type=nested_type)
        self.extended_attributes = extended_attributes

        if any(key not in EXTENDED_ATTRIBUTES_APPLICABLE_TO_TYPES
               for key in extended_attributes):
            raise ValueError(
                'Extended attributes not applicable to types: %s' % self)

        if ('StringContext' in extended_attributes
                and nested_type.name not in ['DOMString', 'USVString']):
            raise ValueError(
                'StringContext is only applicable to string types.')

    def __eq__(self, other:"IdlAnnotatedType"):
        if not isinstance(other, IdlAnnotatedType): return False
        return other and self.nested_type == other.nested_type and self.extended_attributes == other.extended_attributes

    def __ne__(self, other:"IdlAnnotatedType"):
        return not (self == other)

    def __hash__(self):
        return hash(self.name)

    @property
    def has_string_context(self):
        return 'StringContext' in self.extended_attributes

    @property
    def name(self):
        return self.nested_type.name
