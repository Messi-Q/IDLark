
from copy import copy
from typing import Union, Iterable
from .idl_types import IdlType, IdlTypeBase, IdlUnionType

class WithExtendedAttributes:

    def __init__(self) -> None:
        self._extended_attributes = {}
        self._identifiers:set[str] = set()
        self._extattr_arguments:dict[str, list[IdlArgument]] = {}
        self._named_arguments:dict[str, tuple[str, list[IdlArgument]]] = {}
        self._identifier_pairs:dict[str, str] = {}
        self._identifier_lists:dict[str, list[str]] = {}
        self._string_literals:dict[str, str] = {}
        self._string_literal_lists:dict[str, list[str]] = {}
        self._numbers:dict[str, int] = {}

    def __process_extended_attributes(self, attrs:dict):
        for k, v in attrs.items():
            if isinstance(v, list):
                if not v: continue
                if isinstance(v[0], IdlArgument):
                    self.extattr_add_arguments(k, v)
                elif isinstance(v[0], str):
                    if v[0].startswith('"'):
                        self.extattr_add_string_literal_list(k, v)
                    else:
                        self.extattr_add_identifier_list(k ,v)
            elif isinstance(v, bool):
                self.extattr_add_identifier(k)
            elif isinstance(v, str):
                if v.startswith('"'):
                    self.extattr_add_string_literal(k, v, quotes=False)
                else:
                    self.extattr_add_identifier_pair(k, v)
            elif isinstance(v, dict):
                assert len(v.keys()) == 1
                arg_ident = list(v.keys())[0]
                self.extattr_add_named_arguments(
                    k, arg_ident, v[arg_ident]
                )
            else:
                raise TypeError(f"Wrong extended attributes type: {attrs}")

    def set_extended_attributes(self, attributes:dict):
        self._extended_attributes = attributes
        self.__process_extended_attributes(attributes)

    def extattr_add_identifier(self, identifier:str):
        self._identifiers.add(identifier)

    def extattr_has_identifier(self, identifier:str):
        return identifier in self._identifiers

    def extattr_remove_identifier(self, identifier:str):
        if self.extattr_has_identifier(identifier): self._identifiers.remove(identifier)

    def extattr_add_arguments(self, identifier:str, arguments:Iterable["IdlArgument"]):
        self._extattr_arguments[identifier] = list(arguments)

    def extattr_get_arguments(self, identifier:str):
        return self._extattr_arguments.get(identifier, [])

    def extattr_remove_arguments(self, identifier:str):
        if self.extattr_get_arguments(identifier) is not None: self._extattr_arguments.pop(identifier)

    def extattr_add_named_arguments(self, identifier:str, argument_name:str, arguments:Iterable["IdlArgument"]):
        self._named_arguments[identifier] = (argument_name, arguments)

    def extattr_get_named_arguments(self, identifier:str):
        self._named_arguments.get(identifier)

    def extattr_remove_named_arguments(self, identifier:str):
        if self.extattr_get_named_arguments(identifier) is not None: self._named_arguments.pop(identifier)

    def extattr_add_identifier_pair(self, key:str, value:str):
        self._identifier_pairs[key] = value

    def extattr_get_identifier_value(self, identifier_key:str):
        return self._identifier_pairs.get(identifier_key)

    def extattr_remove_identifier_pair(self, identifier_key:str):
        if self.extattr_get_identifier_value(identifier_key) is not None: self._identifier_pairs.pop(identifier_key)

    def extattr_add_identifier_list(self, identifier_key:str, identifier_list:Iterable[str]):
        self._identifier_lists[identifier_key] = list(identifier_list)

    def extattr_get_identifier_list(self, identifier_key:str):
        return self._identifier_lists.get(identifier_key, [])

    def extattr_remove_identifier_list(self, identifier_key:str):
        if self.extattr_get_identifier_list(identifier_key) is not None: self._identifier_lists.pop(identifier_key)

    def extattr_add_string_literal(self, identifier:str, string_literal:str, quotes:bool=True):
        self._string_literals[identifier] = f'"{string_literal}"' if quotes else string_literal

    def extattr_get_string_literal(self, identifier:str):
        self._string_literals.get(identifier)

    def extattr_remove_string_literal(self, identifier:str):
        if self.extattr_get_string_literal(identifier) is not None: self._string_literals.pop(identifier)

    def extattr_add_string_literal_list(self, identifier:str, string_literal_list:Iterable[str]):
        self._string_literal_lists[identifier] = list(string_literal_list)

    def extattr_get_string_literal_list(self, identifier:str):
        return self._string_literal_lists.get(identifier, [])

    def extattr_remove_string_literal_list(self, identifier:str):
        if self.extattr_get_string_literal_list(identifier): self._string_literal_lists.pop(identifier)

    def extattr_add_number(self, identifier:str, number:int):
        self._numbers[identifier] = number

    def extattr_get_number(self, identifier:str):
        return self._numbers.get(identifier)

    def extattr_remove_number(self, identifier:str):
        if self.extattr_get_number(identifier) is not None: self._numbers.pop(identifier)

class WithOperations:

    def __init__(self):
        self._operations:list[IdlOperation] = []
        self._operations_dict:dict[str, list[IdlOperation]] = {}
        self._disabled_operations:list[IdlOperation] = []

    def add_operation(self, operation:"IdlOperation") -> Union["IdlOperation", None]:
        operation = copy(operation)
        operation.set_owner(self)
        if not self.has_operation(operation):
            if (operation.is_setter or operation.is_getter or operation.is_deleter): return
            self._operations.append(operation)
            self._operations_dict.setdefault(operation.name, []).append(operation)
            return operation

    def remove_operation(self, operation:"IdlOperation") -> bool:
        if self.has_operation(operation):
            self._operations.remove(operation)
            self._operations_dict[operation.name].remove(operation)
            operation.set_owner(None)
            return True
        return False

    @property
    def operations(self):
        return self._operations[:]

    def find_operations(
        self, name:str, argument_types:list[Union[IdlTypeBase, str, None]]=None, expect_count:int=None
    ) -> list["IdlOperation"]:
        ops = []
        if argument_types is None:
            ops = self._operations_dict.get(name, [])[:]
        else:
            for op in self._operations_dict.get(name, []):
                if len(op.arguments) != len(argument_types): continue
                matched = True
                for i in range(0, len(op.arguments)):
                    if argument_types[i] is None: continue
                    if isinstance(argument_types[i], str):
                        if argument_types[i] == op.arguments[i].idl_type.name: continue
                    elif isinstance(argument_types[i], IdlTypeBase):
                        if argument_types[i] == op.arguments[i].idl_type: continue
                    else:
                        raise TypeError(f"Invalid argument type: {type(argument_types[i])}")
                    matched = False
                    break
                if matched: ops.append(op)
        if isinstance(expect_count, int) and len(ops) != expect_count:
            raise Exception(f"The number of operations returned({len(ops)}) is not as expected({expect_count})! holder: {self}, op: {name}")
        return ops

    def operation(self, name:str, argument_types:list[Union[IdlTypeBase, str, None]]=None) -> "IdlOperation":
        return self.find_operations(name, argument_types=argument_types, expect_count=1)[0]

    def has_operation(self, operation:Union["IdlOperation", str]):
        if isinstance(operation, str):
            return operation in self._operations_dict and self._operations_dict[operation]
        elif isinstance(operation, IdlOperation):
            return operation in self._operations
        else:
            raise TypeError(f"Invalid operation type {type(operation)}")

class WithAttributes:

    def __init__(self):
        self._attributes:list[IdlAttribute] = []
        self._attributes_dict:dict[str, IdlAttribute] = {}
        self._attributes_typedict:dict[str, list[IdlAttribute]] = {}
        self.mutable_attributes:list[IdlAttribute] = []
        self.readonly_attributes:list[IdlAttribute] = []

    @property
    def attributes(self):
        return self._attributes[:]

    def add_attribute(self, attribute:"IdlAttribute") -> Union["IdlAttribute", None]:
        if attribute.name in self._attributes_dict: return
        attribute = copy(attribute)
        attribute.set_owner(self)
        self._attributes.append(attribute)
        self._attributes_dict[attribute.name] = attribute
        self._attributes_typedict.setdefault(attribute.idl_type.name, []).append(attribute)
        if attribute.is_readonly: self.readonly_attributes.append(attribute)
        elif not attribute.is_event_handler: self.mutable_attributes.append(attribute)
        return attribute

    def remove_attribute(self, attribute:Union[str, "IdlAttribute"]) -> Union["IdlAttribute", None]:
        if isinstance(attribute, str):
            attr_name = attribute
            attribute = self.attribute(attr_name)
        else:
            attr_name = attribute.name
        if attr_name not in self._attributes_dict: return
        attribute = self._attributes_dict[attr_name]
        self._attributes.remove(attribute)
        self._attributes_dict.pop(attr_name)
        self._attributes_typedict[attribute.idl_type.name].remove(attribute)
        if attribute.is_readonly: self.readonly_attributes.remove(attribute)
        elif not attribute.is_event_handler: self.mutable_attributes.remove(attribute)
        attribute.set_owner(None)
        return attribute

    def attribute(self, name:str) -> Union["IdlAttribute", None]:
        return self._attributes_dict.get(name, None)

    def find_attributes(self, type:str) -> list["IdlAttribute"]:
        return self._attributes_typedict.get(type, [])[:]

    def has_attribute(self, attribute:Union["IdlAttribute", str]) -> bool:
        if isinstance(attribute, IdlAttribute):
            return attribute in self._attributes
        elif isinstance(attribute, str):
            return attribute in self._attributes_dict
        else:
            raise TypeError(f"Invalid attribute type {type(attribute)}")

class WithConstants:

    def __init__(self):
        self.constants:list[IdlConstant] = []
        self._constants_dict:dict[str, IdlConstant] = {}

    def add_constant(self, constant:"IdlConstant"):
        if constant.name in self._constants_dict: return
        self.constants.append(constant)
        self._constants_dict[constant.name] = constant
        constant.set_owner(self)

    def remove_constant(self, constant:Union[str, "IdlConstant"]):
        if isinstance(constant, str):
            constant = self._constants_dict.get(constant)
        if not constant: return
        self.constants.remove(constant)
        self._constants_dict.pop(constant.name)
        constant.set_owner(None)

    def constant(self, name:str):
        return self._constants_dict.get(name)

class WithIdlType:

    def __init__(self, idl_type:IdlTypeBase):
        self.set_type(idl_type)

    def set_type(self, idl_type:IdlTypeBase):
        self.idl_type = idl_type

OwnerClass = Union["IdlInterface", "IdlNamespace", "IdlDictionary"]

class WithOwner:

    def __init__(self, owner:OwnerClass=None):
        self.owner:OwnerClass = None
        self.set_owner(owner)

    def set_owner(self, owner:OwnerClass):
        if not owner or owner.is_partial:
            return
        self.owner = owner

class IdlDefinition(WithExtendedAttributes):

    def __init__(self):
        WithExtendedAttributes.__init__(self)
        self.name:str = ''

    def set_name(self, name:str):
        self.name = name

class IdlAttribute(WithExtendedAttributes, WithIdlType,WithOwner):

    def __init__(
        self, name:str, idl_type:IdlTypeBase, is_readonly:bool=False,
        is_static:bool=False, is_stringifier:bool=False, is_inherit:bool=False
    ):
        WithExtendedAttributes.__init__(self)
        WithIdlType.__init__(self, idl_type)
        WithOwner.__init__(self)
        self.name:str = name
        self.is_readonly = is_readonly
        self.is_static = is_static
        self.is_stringifier = is_stringifier
        self.is_inherit = is_inherit
        self.is_event_handler = self.idl_type.name == 'EventHandler'

    def __copy__(self):
        attribute = IdlAttribute(
            self.name, self.idl_type, is_readonly=self.is_readonly,
            is_static=self.is_static, is_stringifier=self.is_stringifier,
            is_inherit=self.is_inherit
        )
        attribute.set_extended_attributes(self._extended_attributes)
        return attribute

    def __str__(self):
        if self.owner:
            prefix = f"{self.owner.name}."
        else:
            prefix = ''
        return f"({self.idl_type.name}){prefix}{self.name}"

    def __eq__(self, other:"IdlAttribute"):
        if not self.same_as(other):
            return False
        if self.owner != other.owner:
            return False
        return True

    def set_stringifier(self, is_stringifier:bool):
        self.is_stringifier = is_stringifier

    def set_inherit(self, is_inherit:bool):
        self.is_inherit = is_inherit

    def set_static(self, is_static:bool):
        self.is_static = is_static

    def set_readonly(self, readonly:bool):
        if readonly == self.is_readonly: return
        if self.owner:
            owner = self.owner
            owner.remove_attribute(self)
            self.is_readonly = readonly
            owner.add_attribute(self)
        else:
            self.is_readonly = readonly

    def same_as(self, other:"IdlAttribute"):
        if self.idl_type.name != other.idl_type.name:
            return False
        if self.name != other.name:
            return False
        return True

class IdlArgument(WithExtendedAttributes, WithIdlType):

    def __init__(
        self, name:str, idl_type:IdlTypeBase, is_optional:bool=False,
        is_variadic:bool=False, default_value=None
    ):
        WithExtendedAttributes.__init__(self)
        WithIdlType.__init__(self, idl_type)
        self.name = name
        self.is_optional = is_optional
        self.is_variadic = is_variadic
        self.default_value = default_value

    def __copy__(self):
        argument = IdlArgument(
            self.name, self.idl_type, is_optional=self.is_optional,
            is_variadic=self.is_variadic, default_value=self.default_value
        )
        argument.set_extended_attributes(self._extended_attributes)
        return argument

    def __str__(self):
        return f"{self.idl_type.name} {self.name}"

    def __eq__(self, other:"IdlArgument"):
        return (
            self.idl_type.name == other.idl_type.name
            and self.name == other.name
        )

    def set_variadic(self, variadic:bool):
        self.is_variadic = variadic

    def set_optional(self, optional:bool):
        self.is_optional = optional

    def set_default(self, default_value):
        self.default_value = default_value

class IdlOperation(WithExtendedAttributes, WithIdlType, WithOwner):

    def __init__(
        self, name:str, idl_type:IdlTypeBase, arguments:list[IdlArgument]=None, 
        is_ctor:bool=False, is_static:bool=False, is_getter:bool=False,
        is_setter:bool=False, is_deleter:bool=False, is_stringifier:bool=False, 
        is_legacycaller:bool=False, is_async:bool=False
    ):
        WithExtendedAttributes.__init__(self)
        WithIdlType.__init__(self, idl_type)
        WithOwner.__init__(self)
        self.__name = name
        self.is_constructor = is_ctor
        self.is_static = is_static
        self.is_getter = is_getter
        self.is_setter = is_setter
        self.is_deleter = is_deleter
        self.is_stringifier = is_stringifier
        self.is_legacycaller = is_legacycaller
        self.is_async = is_async

        self.__init_arguments(arguments)

    def __init_arguments(self, args:list[IdlArgument]):
        self.arguments:list[IdlArgument] = args if args else []
        self.arguments_dict:dict[str, IdlArgument] = {arg.name:arg for arg in self.arguments}

    def argument(self, index:Union[str, int], expect_type:str=None):
        argument = None
        if isinstance(index, int):
            argument = self.arguments[index]
        elif isinstance(index, str):
            argument = self.arguments_dict.get(index)
        if isinstance(expect_type, str) and argument and argument.idl_type.name != expect_type:
            raise Exception(f"The type of argument returned({argument.idl_type.name}) is not expected({expect_type})")
        return argument

    def add_argument(self, arg:IdlArgument):
        assert arg not in self.arguments
        self.arguments.append(arg)
        self.arguments_dict[arg.name] = arg

    @property
    def name(self):
        if self.__name:
            return self.__name
        elif self.is_getter:
            return '(getter)'
        elif self.is_setter:
            return '(setter)'
        elif self.is_deleter:
            return '(deleter)'
        elif self.is_stringifier:
            return '(stringifier)'
        elif self.is_legacycaller:
            return '(legacycaller)'
        else:
            raise Exception(f"Invalid operation")

    def __copy__(self):
        arguments = [ copy(arg) for arg in self.arguments]
        operation = IdlOperation(
            self.name, self.idl_type, arguments, self.is_constructor,
            is_static=self.is_static, is_getter=self.is_getter,
            is_setter=self.is_setter, is_deleter=self.is_deleter,
            is_stringifier=self.is_stringifier,
            is_legacycaller=self.is_legacycaller,
            is_async=self.is_async, 
        )
        operation.set_extended_attributes(self._extended_attributes)
        return operation

    def __str__(self):
        owner_prefix = ''
        if self.owner: owner_prefix = f"{self.owner.name}."
        type_prefix = ''
        if not self.is_constructor: type_prefix = f"{self.idl_type.name} "
        return f"{type_prefix}{owner_prefix}{self.name}({', '.join(arg.idl_type.name for arg in self.arguments)})"

    def __hash__(self):
        return hash(str([
            self.idl_type, self.owner.name if self.owner else '', self.name, self.arguments
        ]))

    def __eq__(self, other:"IdlOperation"):
        if self.name != other.name:
            return False

        if self.owner != other.owner:
            return False

        if self.idl_type != other.idl_type:
            return False

        if not self.has_same_arguments(other):
            return False

        return True

    def has_same_arguments(self, other:"IdlOperation"):
        other_arguments = other.arguments
        if len(self.arguments) != len(other_arguments):
            return False

        for i in range(0, len(self.arguments)):
            if self.arguments[i] != other_arguments[i]:
                return False

        return True

class IdlConstant(WithExtendedAttributes, WithIdlType, WithOwner):

    def __init__(
        self, const_name:str, const_type:IdlTypeBase, const_value
    ):
        WithExtendedAttributes.__init__(self)
        WithIdlType.__init__(self, const_type)
        WithOwner.__init__(self)
        self.name = const_name
        self.value = const_value

    def __eq__(self, other:"IdlConstant"):
        return (
            self.name == other.name
            and self.idl_type == other.idl_type
            and self.value == other.value
        )

class IdlIterable(WithExtendedAttributes):

    def __init__(self):
        WithExtendedAttributes.__init__(self)
        self.key_type:IdlTypeBase = None
        self.value_type:IdlTypeBase = None

    def __eq__(self, other:"IdlIterable"):
        return (
            self.key_type == other.key_type
            and self.value_type == other.value_type
        )

class IdlMaplike(WithExtendedAttributes):

    def __init__(self):
        WithExtendedAttributes.__init__(self)
        self.is_read_only = False
        self.key_type:IdlTypeBase = None
        self.value_type:IdlTypeBase = None

    def __eq__(self, other:"IdlMaplike"):
        return (
            self.key_type == other.key_type
            and self.value_type == other.value_type
            and self.is_read_only == other.is_read_only
        )

class IdlSetlike(WithExtendedAttributes):

    def __init__(self):
        WithExtendedAttributes.__init__(self)
        self.is_read_only = False
        self.value_type:IdlTypeBase = None

    def __eq__(self, other:"IdlSetlike"):
        return (
            self.value_type == other.value_type
            and self.is_read_only == other.is_read_only
        )

class IdlInterface(
    IdlDefinition, WithOperations, WithAttributes, WithIdlType, WithConstants
):

    def __init__(
        self, name:str, is_stringifier:bool=False, is_mixin:bool=False,
        maplike:Union[IdlMaplike, None]=None, setlike:Union[IdlSetlike, None]=None, 
        iterable:Union[IdlIterable, None]=None, parent:Union[str, "IdlInterface", None]=None, 
        is_declaration:bool=False
    ):
        IdlDefinition.__init__(self)
        WithOperations.__init__(self)
        WithAttributes.__init__(self)
        WithConstants.__init__(self)
        WithIdlType.__init__(self, IdlType(name))
        self.set_name(name)
        self.constructors:list[IdlOperation] = []
        self.maplike = maplike
        self.setlike = setlike
        self.iterable = iterable
        self.is_stringifier = is_stringifier
        self.is_callback = False
        self.is_partial = False
        self.is_declaration = is_declaration
        self.is_mixin = is_mixin
        self.is_event = False
        self.parent:Union[str, IdlInterface] = parent
        self.event_handlers:list[IdlAttribute] = []

    def __str__(self):
        return f"IdlInterface({self.name})"

    @property
    def parent_name(self):
        if isinstance(self.parent, str):
            return self.parent
        elif isinstance(self.parent, IdlInterface):
            return self.parent.name
        else:
            raise TypeError(f"Invalid parent type {type(self.parent)}")

    def set_name(self, name:str):
        if not name or not isinstance(name, str): return
        self.name = name
        self.set_type(IdlType(name))

    def set_parent(self, parent:Union[str, "IdlInterface", None]):
        self.parent = parent

    def add_operation(self, operation:IdlOperation) -> bool:
        operation = WithOperations.add_operation(self, operation)
        if not operation: return False
        if operation.is_constructor:
            assert (operation.idl_type is None or operation.idl_type == self.idl_type)
            self.constructors.append(operation)
            operation.set_type(IdlType(self.name))
        assert operation.idl_type
        return True

    def remove_operation(
        self, operation:Union[IdlOperation, str], argument_types:list[Union[str, None]]=None
    ) -> bool:
        if isinstance(operation, IdlOperation):
            if not WithOperations.remove_operation(self, operation): return False
            if operation.is_constructor: self.constructors.remove(operation)
            return True
        else:
            operation_name = operation
            result = True
            for operation in self.find_operations(operation_name, argument_types):
                result = self.remove_operation(operation) and result
            return result

    def is_subclass_of(self, other:Union[str, "IdlInterface"]) -> bool:
        i = self.parent
        while i:
            assert isinstance(i, IdlInterface)
            if isinstance(other, str):
                parent_info = i.name
            else:
                parent_info = i
            if other == parent_info:
                return True
            i = i.parent
        return False

class IdlCallbackFunction(IdlDefinition, WithIdlType):

    def __init__(
        self, name:str, idl_type:IdlTypeBase, arguments:list[IdlArgument]=None,
        is_constructor:bool=False
    ):
        IdlDefinition.__init__(self)
        WithIdlType.__init__(self, idl_type)
        self.name = name
        self.arguments:list[IdlArgument] = arguments if arguments else []
        self.is_constructor = is_constructor

    def __eq__(self, other:"IdlCallbackFunction"):
        if not other: return False
        assert isinstance(other, IdlCallbackFunction)
        return (
            self.name == other.name
            and self.idl_type == other.idl_type
            and set(self.arguments) == set(other.arguments)
            and self.is_constructor == other.is_constructor
        )

class IdlNamespace(IdlDefinition, WithOperations, WithAttributes, WithConstants):

    def __init__(self, name:str) -> None:
        IdlDefinition.__init__(self)
        WithOperations.__init__(self)
        WithAttributes.__init__(self)
        WithConstants.__init__(self)
        self.name = name
        self.is_partial = False

    def __str__(self):
        return f"IdlNamespace({self.name})"

    def remove_operation(
        self, operation:Union[IdlOperation, str], argument_types:list[Union[str, None]]=None
    ) -> bool:
        if isinstance(operation, IdlOperation):
            if not WithOperations.remove_operation(self, operation): return False
            return True
        else:
            op_name = operation
            result = True
            for operation in self.find_operations(op_name, argument_types):
                result = self.remove_operation(operation) and result
            return result

class IdlDictionaryMember(WithExtendedAttributes, WithIdlType, WithOwner):

    def __init__(
        self, name:str, idl_type:IdlTypeBase, is_required:bool=False,
        default_value=None
    ):
        WithExtendedAttributes.__init__(self)
        WithIdlType.__init__(self, idl_type)
        WithOwner.__init__(self)
        self.name = name
        self.is_required = is_required
        self.default_value = default_value

    def __copy__(self):
        new_member = IdlDictionaryMember(
            self.name, self.idl_type, is_required=self.is_required, 
            default_value=self.default_value
        )
        new_member.set_extended_attributes(self._extended_attributes)
        return new_member

    def __eq__(self, other:"IdlDictionaryMember"):
        if not other: return False
        assert isinstance(other, IdlDictionaryMember)
        return (
            self.name == other.name
            and self.idl_type.name == other.idl_type.name
        )

    def __str__(self):
        return f"{self.idl_type.name} {self.owner.name}.{self.name}"

    def __hash__(self):
        return hash(str(self))

    def set_required(self, required:bool):
        self.is_required = required

class IdlDictionary(IdlDefinition, WithIdlType):

    def __init__(
        self, name:str, parent:Union[str, "IdlDictionary"]=None, 
        is_partial:bool=False
    ):
        IdlDefinition.__init__(self)
        WithIdlType.__init__(self, IdlType(name))
        self.name = name
        self.members:list[IdlDictionaryMember] = []
        self.members_dict:dict[str, IdlDictionaryMember] = {}
        self.members_typedict:dict[str, list[IdlDictionaryMember]] = {}
        self.parent:Union[str, IdlDictionary] = parent
        self.is_partial = is_partial
        self.set_name(name)

    @property
    def parent_name(self):
        if isinstance(self.parent, str):
            return self.parent
        elif isinstance(self.parent, IdlDictionary):
            return self.parent.name
        else:
            raise TypeError(f"Invalid parent type {type(self.parent)}")

    def __eq__(self, other:"IdlDictionary"):
        if not other: return False
        assert isinstance(other, IdlDictionary)
        return self.name == other.name

    def __hash__(self) -> int:
        return hash(self.name)

    def set_name(self, name:str):
        self.name = name
        self.set_type(IdlType(name))

    def set_parent(self, parent:Union[str, "IdlDictionary"]):
        self.parent = parent

    def add_member(self, member:IdlDictionaryMember):
        if member.name in self.members_dict: return
        new_member = copy(member)
        self.members.append(new_member)
        self.members_dict[new_member.name] = new_member
        self.members_typedict.setdefault(
            new_member.idl_type.name, []
        ).append(new_member)
        new_member.set_owner(self)

    def has_member(self, member:Union[str, IdlDictionaryMember]):
        if isinstance(member, str):
            return member in self.members_dict
        else:
            return member.name in self.members_dict

    def remove_member(self, member_name:str):
        member = self.members_dict.get(member_name, None)
        if not member: return
        self.members.remove(member)
        self.members_dict.pop(member_name)
        self.members_typedict[member.idl_type.name].remove(member)

    def member(self, name:str):
        return self.members_dict[name]

    def find_members(self, member_type:str):
        return self.members_typedict.get(member_type, [])[:]

class IdlEnum(IdlDefinition, WithIdlType):

    def __init__(self, name:str, values:set[Union[str, int]]=None):
        IdlDefinition.__init__(self)
        WithIdlType.__init__(self, IdlType(name))
        self.name = name
        self.__values = set() if not values else set(values)

    @property
    def values(self):
        return list(self.__values)

    def __eq__(self, other: "IdlEnum") -> bool:
        if not other: return False
        assert isinstance(other, IdlEnum)
        return (
            self.name == other.name
            and self.idl_type == other.idl_type
            and self.__values == other.__values
        )

    def set_name(self, name:str):
        self.name = name
        self.set_type(IdlType(name))

    def set_values(self, values:Iterable[Union[str, int]]):
        self.__values = set(values)

    def add_value(self, value:Union[str, set[str], int, set[int]]):
        if isinstance(value, str):
            self.__values.add(value.strip('"'))
        elif isinstance(value, int):
            self.__values.add(value)
        elif isinstance(value, set):
            [self.add_value(i) for i in value]
        else:
            raise TypeError(f"Invalid value type {type(value)}")

    def remove_value(self, value:str):
        self.__values.remove(value)

class IdlTypedef(IdlDefinition, WithIdlType):

    def __init__(self, name:str, idl_type:IdlUnionType) -> None:
        IdlDefinition.__init__(self)
        WithIdlType.__init__(self, idl_type)
        self.name = name

    def __eq__(self, other: "IdlTypedef") -> bool:
        if not other: return False
        assert isinstance(other, IdlTypedef)
        return (
            self.name == other.name
            and self.idl_type == other.idl_type
        )

class IdlIncludes(IdlDefinition):

    def __init__(self, interface:str):
        IdlDefinition.__init__(self)
        self.interface:str = interface
        self.__mixin:set[str] = set()

    @property
    def mixin(self):
        return list(self.__mixin)

    def __eq__(self, other: "IdlIncludes") -> bool:
        if not other: return False
        assert isinstance(other, IdlIncludes)
        return (
            self.interface == other.interface
            and self.mixin == other.mixin
        )

    def add_mixin(self, mixin:str):
        self.__mixin.add(mixin)

    def remove_mixin(self, mixin:str):
        self.__mixin.remove(mixin)

class IdlDefinitions:

    def __init__(self):
        self.callback_functions:dict[str, IdlCallbackFunction] = {}
        self.dictionaries:dict[str, IdlDictionary] = {}
        self.enumerations:dict[str, IdlEnum] = {}
        self.includes:list[IdlIncludes] = []
        self.interfaces:list[IdlInterface] = []
        self.typedefs:dict[str, IdlTypedef] = {}
        self.namespaces:list[IdlNamespace] = []

    def add_interface(self, interface:IdlInterface):
        self.interfaces.append(interface)

    def add_includes(self, includes:IdlIncludes):
        self.includes.append(includes)

    def add_dictionary(self, dictionary:IdlDictionary):
        self.dictionaries[dictionary.name] = dictionary

    def add_callback_function(self, callback:IdlCallbackFunction):
        self.callback_functions[callback.name] = callback

    def add_namespace(self, namespace:IdlNamespace):
        self.namespaces.append(namespace)

    def add_enum(self, enum:IdlEnum):
        self.enumerations[enum.name] = enum

    def add_typedef(self, typedef:IdlTypedef):
        self.typedefs[typedef.name] = typedef
