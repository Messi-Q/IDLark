
from typing import Union
from pathlib import Path
from lark import Lark, Transformer, Tree, Token

from .idl_types import (
    IdlSequenceType, IdlTypeBase, IdlType, IdlPromiseType,
    IdlUnionType, IdlRecordType, IdlNullableType, IdlObservableArrayType
)
from .idl_definitions import (
    IdlAttribute, IdlArgument, IdlOperation,
    IdlConstant, IdlIterable, IdlMaplike, IdlSetlike,
    IdlInterface, IdlCallbackFunction, IdlNamespace,
    IdlDictionaryMember, IdlDictionary, IdlEnum,
    IdlTypedef, IdlIncludes, IdlDefinitions, WithExtendedAttributes
)

NODES_TYPE = tuple[Union[Tree, Token]]
GRAMMAR_PATH = Path(__file__).parent / "grammar.lark"

class WebIDLTransformer(Transformer):

    def definitions(self, nodes:NODES_TYPE):
        idl_definitions = IdlDefinitions()
        ext_attrs = {}
        for node in nodes:
            if isinstance(node, Token) and node.type == 'EXTENDED_ATTRIBUTE_LIST':
                ext_attrs = node.value
            else:
                definition = node.value
                if isinstance(definition, IdlCallbackFunction):
                    idl_definitions.add_callback_function(definition)
                elif isinstance(definition, IdlInterface):
                    idl_definitions.add_interface(definition)
                elif isinstance(definition, IdlDictionary):
                    idl_definitions.add_dictionary(definition)
                elif isinstance(definition, IdlNamespace):
                    idl_definitions.add_namespace(definition)
                elif isinstance(definition, IdlEnum):
                    idl_definitions.add_enum(definition)
                elif isinstance(definition, IdlIncludes):
                    idl_definitions.add_includes(definition)
                elif isinstance(definition, IdlTypedef):
                    idl_definitions.add_typedef(definition)
                else:
                    raise Exception("Invalid node of definition")
                if not ext_attrs: continue
                definition.set_extended_attributes(ext_attrs)
                ext_attrs = {}
        return idl_definitions

    def definition(self, nodes:NODES_TYPE):
        return Token('DEFINITION', nodes[0])

    def interface_declaration(self, nodes:NODES_TYPE):
        interface = IdlInterface(name=nodes[1].value, is_declaration=True)
        return interface

    def partial(self, nodes:NODES_TYPE):
        partial_def:Union[IdlInterface, IdlDictionary, IdlNamespace] = nodes[1]
        partial_def.is_partial = True
        return partial_def

    def partial_definition(self, nodes:NODES_TYPE):
        return nodes[0]

    def partial_interface(self, nodes:NODES_TYPE):
        interface_name = None
        is_stringifier = False
        attrs = []
        ops = []
        consts = []
        maplike = None
        setlike = None
        iterable = None
        for node in nodes:
            if isinstance(node, Token):
                if node.type == 'IDENTIFIER':
                    interface_name = node.value
                elif node.type == 'STRINGIFIER':
                    is_stringifier = True
            elif isinstance(node, IdlAttribute):
                attrs.append(node)
            elif isinstance(node, IdlOperation):
                assert not node.is_constructor
                ops.append(node)
            elif isinstance(node, IdlConstant):
                consts.append(node)
            elif isinstance(node, IdlMaplike):
                maplike = node
            elif isinstance(node, IdlSetlike):
                setlike = node
            elif isinstance(node, IdlIterable):
                iterable = node
        assert interface_name
        idl_interface = IdlInterface(
            interface_name, is_stringifier=is_stringifier,
            maplike=maplike, setlike=setlike, iterable=iterable
        )
        for attr in attrs: idl_interface.add_attribute(attr)
        for op in ops: idl_interface.add_operation(op)
        for const in consts: idl_interface.add_constant(const)
        return idl_interface

    def partial_interface_member(self, nodes:NODES_TYPE):
        ext_attrs = {}
        for node in nodes:
            if isinstance(node, Token):
                if node.type == 'EXTENDED_ATTRIBUTE_LIST':
                    ext_attrs = node.value
        member:WithExtendedAttributes = nodes[-1]
        if ext_attrs: member.set_extended_attributes(ext_attrs)
        return member

    def partial_dictionary(self, nodes:NODES_TYPE):
        name = ''
        members = []
        for node in nodes:
            if isinstance(node, Token):
                if node.type == 'IDENTIFIER':
                    name = node.value
            elif isinstance(node, IdlDictionaryMember):
                members.append(node)
        assert name
        idl_dictionary = IdlDictionary(name, is_partial=True)
        for member in members: idl_dictionary.add_member(member)
        return idl_dictionary

    def includes_satement(self, nodes:NODES_TYPE):
        interface = nodes[0].value
        mixin = nodes[2].value
        idl_include = IdlIncludes(interface)
        idl_include.add_mixin(mixin)
        return idl_include

    def typedef(self, nodes:NODES_TYPE):
        name = ''
        idl_type = None
        for node in nodes:
            if isinstance(node, Token) and node.type == 'IDENTIFIER':
                name = node.value
            elif isinstance(node, IdlTypeBase):
                if isinstance(node, IdlUnionType):
                    idl_type = node
                else:
                    idl_type = IdlUnionType([node])
        assert name and idl_type
        idl_typedef = IdlTypedef(name, idl_type)
        return idl_typedef

    def enum(self, nodes:NODES_TYPE):
        name = ''
        values = []
        for node in nodes:
            if isinstance(node, Token):
                if node.type == 'IDENTIFIER':
                    name = node.value
                elif node.type == 'ENUM_VALUE_LIST':
                    values.append(node.value)
        assert name
        idl_enum = IdlEnum(name)
        for v in values: idl_enum.add_value(v)
        return idl_enum

    def enum_value_list(self, nodes:NODES_TYPE):
        def _parse_enum_value(node:Token):
            if node.type == 'INTEGER':
                return int(node.value)
            elif node.type == 'STRING':
                return str(node.value)
            else:
                raise
        values = map(_parse_enum_value, nodes)
        return Token('ENUM_VALUE_LIST', set(values))

    def dictionary(self, nodes:NODES_TYPE):
        name = ''
        parent = None
        members = []
        for node in nodes:
            if isinstance(node, Token):
                if node.type == 'IDENTIFIER':
                    name = node.value
                elif node.type == 'INHERITANCE':
                    parent = node.value
            elif isinstance(node, IdlDictionaryMember):
                members.append(node)
        assert name
        idl_dictionary = IdlDictionary(name, parent=parent)
        for member in members: idl_dictionary.add_member(member)
        return idl_dictionary

    def dictionary_member(self, nodes:NODES_TYPE):
        name = ''
        idl_type = None
        default_value = None
        is_required = False
        extended_attributes = {}
        for node in nodes:
            if isinstance(node, Token):
                if node.type == 'REQUIRED':
                    is_required = True
                elif node.type == 'IDENTIFIER':
                    name = node.value
                elif node.type == 'DEFAULT':
                    default_value = node.value
                elif node.type == 'EXTENDED_ATTRIBUTE_LIST':
                    extended_attributes = node.value
            elif isinstance(node, IdlTypeBase):
                idl_type = node
        assert name and idl_type
        member = IdlDictionaryMember(
            name, idl_type, is_required=is_required, default_value=default_value)
        member.set_extended_attributes(extended_attributes)
        return member

    def namespace(self, nodes:NODES_TYPE):
        name = ''
        ops = []
        attrs = []
        consts = []
        for node in nodes:
            if isinstance(node, Token):
                if node.type == 'IDENTIFIER':
                    name = node.value
            elif isinstance(node, IdlOperation):
                ops.append(node)
            elif isinstance(node, IdlAttribute):
                attrs.append(node)
            elif isinstance(node, IdlConstant):
                consts.append(node)
        assert name
        idl_namespace = IdlNamespace(name)
        for op in ops: idl_namespace.add_operation(op)
        for attr in attrs: idl_namespace.add_attribute(attr)
        for const in consts: idl_namespace.add_constant(const)
        return idl_namespace

    def namespace_member(self, nodes:NODES_TYPE):
        is_readonly = False
        ext_attrs = {}
        member = None
        for node in nodes:
            if isinstance(node, IdlOperation):
                member = node
            elif isinstance(node, IdlAttribute):
                member = node
            elif isinstance(node, IdlConstant):
                member = node
            elif isinstance(node, Token):
                if node.type == 'EXTENDED_ATTRIBUTE_LIST':
                    ext_attrs = node.value
                if node.type == 'READONLY':
                    is_readonly = True
        if ext_attrs: member.set_extended_attributes(ext_attrs)
        if isinstance(member, IdlAttribute):
            member.set_readonly(is_readonly)
        return member

    def namespace_member_constant(self, nodes:NODES_TYPE):
        return self.interface_member_constant(nodes)

    def callback(self, nodes:NODES_TYPE):
        name = ''
        args = []
        idl_type = None
        is_constructor = False
        for node in nodes:
            if isinstance(node, Token):
                if node.type == 'IDENTIFIER':
                    name = node.value
                elif node.type == 'ARGUMENT_LIST':
                    args = node.value
                elif node.type == 'CONSTRUCTOR':
                    is_constructor = True
            elif isinstance(node, IdlTypeBase):
                idl_type = node
        assert name and idl_type
        idl_callback = IdlCallbackFunction(
            name, idl_type=idl_type, arguments=args, is_constructor=is_constructor
        )
        return idl_callback

    def callback_interface(self, nodes:NODES_TYPE):
        idl_interface:IdlInterface = nodes[1]
        idl_interface.is_callback = True
        return idl_interface

    def mixin_interface(self, nodes:NODES_TYPE):
        interface_name = ''
        is_stringifier = False
        attrs = []
        ops = []
        consts = []
        for node in nodes:
            if isinstance(node, Token):
                if node.type == 'IDENTIFIER':
                    interface_name = node.value
                elif node.type == 'STRINGIFIER':
                    is_stringifier = True
            elif isinstance(node, IdlAttribute):
                attrs.append(node)
            elif isinstance(node, IdlOperation):
                ops.append(node)
            elif isinstance(node, IdlConstant):
                consts.append(node)
        assert interface_name
        idl_interface = IdlInterface(
            interface_name, is_stringifier=is_stringifier,
            is_mixin=True
        )
        for attr in attrs: idl_interface.add_attribute(attr)
        for op in ops: idl_interface.add_operation(op)
        for const in consts: idl_interface.add_constant(const)

        return idl_interface

    def mixin_interface_member(self, nodes:NODES_TYPE):
        ext_attrs = {}
        for node in nodes:
            if isinstance(node, Token):
                if node.type == 'EXTENDED_ATTRIBUTE_LIST':
                    ext_attrs = node.value
        member:WithExtendedAttributes = nodes[-1]
        if ext_attrs: member.set_extended_attributes(ext_attrs)
        return member

    def interface(self, nodes:NODES_TYPE):

        interface_name = None
        is_stringifier = False
        attrs = []
        ops = []
        consts = []
        maplike = None
        setlike = None
        iterable = None
        parent = None
        for node in nodes:
            if isinstance(node, Token):
                if node.type == 'IDENTIFIER':
                    interface_name = node.value
                elif node.type == 'INHERITANCE':
                    parent = node.value
                elif node.type == 'STRINGIFIER':
                    is_stringifier = True
            elif isinstance(node, IdlAttribute):
                attrs.append(node)
            elif isinstance(node, IdlOperation):
                ops.append(node)
            elif isinstance(node, IdlConstant):
                consts.append(node)
            elif isinstance(node, IdlMaplike):
                maplike = node
            elif isinstance(node, IdlSetlike):
                setlike = node
            elif isinstance(node, IdlIterable):
                iterable = node
        assert interface_name
        idl_interface = IdlInterface(
            interface_name, is_stringifier=is_stringifier, 
            maplike=maplike, setlike=setlike, iterable=iterable,
            parent=parent
        )
        for attr in attrs: idl_interface.add_attribute(attr)
        for op in ops: idl_interface.add_operation(op)
        for const in consts: idl_interface.add_constant(const)
        return idl_interface

    def inheritance(self, nodes:NODES_TYPE):
        return Token('INHERITANCE', nodes[0].value)

    def interface_member(self, nodes:NODES_TYPE):
        ext_attrs = {}
        for node in nodes:
            if isinstance(node, Token):
                if node.type == 'EXTENDED_ATTRIBUTE_LIST':
                    ext_attrs = node.value
        member = nodes[-1]
        if ext_attrs: 
            if isinstance(member, (
                IdlAttribute, IdlOperation, IdlConstant, 
                IdlMaplike, IdlSetlike, IdlIterable
            )):
                member.set_extended_attributes(ext_attrs)
        return member

    def stringifier(self, nodes:NODES_TYPE):
        return nodes[0]

    def async_iterable(self, nodes:NODES_TYPE):
        return nodes

    def iterable(self, nodes:NODES_TYPE):
        iterable = IdlIterable()
        for node in nodes:
            if isinstance(node, Token):
                if node.type == 'VALUE_TYPE':
                    iterable.value_type = node.value
                elif node.type == 'KEY_TYPE':
                    iterable.key_type = node.value
        assert iterable.value_type
        return iterable

    def interface_member_setlike(self, nodes:NODES_TYPE):
        setlike = IdlSetlike()
        for node in nodes:
            if isinstance(node, Token):
                if node.type == 'VALUE_TYPE':
                    setlike.value_type = node.value
        assert setlike.value_type
        return setlike

    def interface_member_maplike(self, nodes:NODES_TYPE):
        maplike = IdlMaplike()
        is_readonly = False
        key_type = None
        value_type = None
        for node in nodes:
            if isinstance(node, Token):
                if node.type == 'KEY_TYPE':
                    key_type = node.value
                elif node.type == 'VALUE_TYPE':
                    value_type = node.value
                elif node.type == 'READONLY':
                    is_readonly = True
        assert key_type and value_type
        maplike.is_read_only = is_readonly
        maplike.key_type = key_type
        maplike.value_type = value_type
        return maplike

    def key_type(self, nodes:NODES_TYPE):
        return Token('KEY_TYPE', nodes[0])

    def optional_key_type(self, nodes:NODES_TYPE):
        return Token('KEY_TYPE', nodes[0])

    def value_type(self, nodes:NODES_TYPE):
        return Token('VALUE_TYPE', nodes[0])

    def constructor(self, nodes:NODES_TYPE):
        arguments = []
        for node in nodes:
            if isinstance(node, Token) and node.type == 'ARGUMENT_LIST':
                arguments = node.value
        return IdlOperation('constructor', None, arguments, is_ctor=True)

    def interface_member_constant(self, nodes:NODES_TYPE):
        const_type = None
        const_value = None
        const_name = None
        for node in nodes:
            if isinstance(node, Token):
                if node.type == 'IDENTIFIER':
                    const_name = node.value
                elif node.type == 'CONST_VALUE':
                    const_value = node.value
            elif isinstance(node, IdlTypeBase):
                const_type = node
        assert const_type and const_name and const_value
        return IdlConstant(const_name, const_type, const_value)

    def interface_member_operation(self, nodes:NODES_TYPE):
        is_static = False
        is_stringifier = False
        op_member = None
        for node in nodes:
            if isinstance(node, Token):
                if node.type == 'STATIC':
                    is_static = True
                elif node.type == 'STRINGIFIER':
                    is_stringifier = True
            elif isinstance(node, IdlOperation):
                op_member = node
        assert op_member
        op_member.is_static = is_static
        op_member.is_stringifier = is_stringifier
        return op_member

    def regular_operation(self, nodes:NODES_TYPE):
        ret_type = None
        op_name = ''
        argument_list = []
        for node in nodes:
            if isinstance(node, IdlTypeBase):
                ret_type = node
            elif isinstance(node, Token):
                if node.type == 'OPERATION_NAME':
                    op_name = node.value
                elif node.type == 'ARGUMENT_LIST':
                    argument_list = node.value
        assert ret_type
        return IdlOperation(op_name, ret_type, argument_list)

    def special_operation(self, nodes:NODES_TYPE):
        op:IdlOperation = nodes[1]
        special = nodes[0].type
        if special == 'SETTER':
            op.is_setter = True
        elif special == 'GETTER':
            op.is_getter = True
        elif special == 'DELETER':
            op.is_deleter = True
        elif special == 'LEGACYCALLER':
            op.is_legacycaller = True
        return op

    def operation_name(self, nodes:NODES_TYPE):
        node = nodes[0]
        return Token("OPERATION_NAME", node.value)

    def argument_list(self, nodes:NODES_TYPE):
        return Token("ARGUMENT_LIST", nodes)

    def argument(self, nodes:NODES_TYPE):
        arg_type = None
        arg_name = None
        is_optional = False
        is_variadic = False
        default_value = None
        for node in nodes:
            if isinstance(node, IdlTypeBase):
                arg_type = node
            elif isinstance(node, Token):
                if node.type == 'ARGUMENT_NAME':
                    arg_name = node.value
                elif node.type == 'OPTIONAL':
                    is_optional = True
                elif node.type == 'ELLIPSIS':
                    is_variadic = True
                elif node.type == 'DEFAULT':
                    default_value = node.value
        idl_arg = IdlArgument(arg_name, arg_type)
        idl_arg.set_optional(is_optional)
        idl_arg.set_variadic(is_variadic)
        idl_arg.set_default(default_value)
        return idl_arg

    def default(self, nodes:NODES_TYPE):
        return Token("DEFAULT", nodes[0].value)

    def default_value(self, nodes:NODES_TYPE):
        return Token("DEFAULT_VALUE", nodes[0].value)

    def const_type(self, nodes:NODES_TYPE):
        c_type = None
        nullable = False
        for node in nodes:
            if isinstance(node, IdlTypeBase):
                c_type = node
            elif isinstance(node, Token):
                if node.type == 'NULLABLE' and node.value:
                    nullable = True
                elif node.type == 'IDENTIFIER':
                    c_type = IdlType(node.value)
        assert c_type
        return c_type if not nullable else IdlNullableType(c_type)

    def const_value(self, nodes:NODES_TYPE):
        return Token("CONST_VALUE", nodes[0].value)

    def argument_name(self, nodes:NODES_TYPE):
        node = nodes[0]
        return Token("ARGUMENT_NAME", node.value)

    def argument_name_keyword(self, nodes:NODES_TYPE):
        node = nodes[0]
        return Token("ARGUMENT_NAME_KEYWORD", node.value)

    def interface_member_attribute(self, nodes:NODES_TYPE):
        attr_member = None
        is_static = False
        is_readonly = False
        is_inherit = False
        is_stringifier = False
        for node in nodes:
            if isinstance(node, IdlAttribute):
                attr_member = node
            elif isinstance(node, Token):
                if node.type == 'STATIC':
                    is_static = True
                elif node.type == 'INHERIT':
                    is_inherit = True
                elif node.type == 'STRINGIFIER':
                    is_stringifier = True
                elif node.type == 'READONLY':
                    is_readonly = True
        assert attr_member
        attr_member.set_readonly(is_readonly)
        attr_member.set_static(is_static)
        attr_member.set_stringifier(is_stringifier)
        attr_member.set_inherit(is_inherit)
        return attr_member

    def attribute_rest(self, nodes:NODES_TYPE):
        attr_type = None
        attr_name = None
        for node in nodes:
            if isinstance(node, IdlTypeBase):
                attr_type = node
            elif isinstance(node, Token) and node.type == 'ATTRIBUTE_NAME':
                attr_name = node.value
        assert attr_type and attr_name
        attr = IdlAttribute(attr_name, attr_type)
        return attr

    def attribute_name(self, nodes:NODES_TYPE):
        node = nodes[0]
        return Token('ATTRIBUTE_NAME', node.value)

    def extended_attribute_list(self, nodes:NODES_TYPE):
        attrs = {}
        for node in nodes:
            attr = node.value
            for k, v in attr.items():
                attrs[k] = v
        return Token("EXTENDED_ATTRIBUTE_LIST", attrs)

    def extended_attribute(self, nodes:NODES_TYPE):
        return Token('EXTENDED_ATTRIBUTE', nodes[0].value)

    def extended_attribute_named_arg_list(self, nodes:NODES_TYPE):
        return Token('EXTENDED_ATTRIBUTE_NAMED_ARG_LIST', {nodes[0].value:{nodes[1].value:nodes[2].value}})

    def extended_attribute_string_literal(self, nodes:NODES_TYPE):
        return Token('EXTENDED_ATTRIBUTE_STRING_LITERAL', {nodes[0].value:nodes[1].value})

    def extended_attribute_string_literal_list(self, nodes:NODES_TYPE):
        return Token('EXTENDED_ATTRIBUTE_STRING_LITERAL_LIST', {nodes[0].value:nodes[1].value})

    def extended_attribute_conjunction(self, nodes:NODES_TYPE):
        return Token('EXTENDED_ATTRIBUTE_CONJUNCTION', {nodes[0].value: [ n.value for n in nodes[1:]]})

    def extended_attribute_arg_list(self, nodes:NODES_TYPE):
        key = None
        value = None
        for node in nodes:
            if node.type == 'IDENTIFIER':
                key = node.value
            if node.type == 'ARGUMENT_LIST':
                value = node.value
        return Token('EXTENDED_ATTRIBUTE_ARG_LIST', {key:value})

    def extended_attribute_ident(self, nodes:NODES_TYPE):
        attr = {
            nodes[0].value: nodes[1].value
        }
        return Token('EXTENDED_ATTRIBUTE_IDENT', attr)

    def extended_attribute_no_args(self, nodes:NODES_TYPE):
        return Token('EXTENDED_ATTRIBUTE_NO_ARGS', {nodes[0].value:True})

    def extended_attribute_ident_list(self, nodes:NODES_TYPE):
        key = None
        value = None
        for node in nodes:
            if node.type == 'IDENTIFIER':
                key = node.value
            elif node.type == 'IDENTIFIER_LIST':
                value = node.value
        return Token('EXTENDED_ATTRIBUTE_IDENT_LIST', {key:value})

    def identifier_list(self, nodes:NODES_TYPE):
        return Token('IDENTIFIER_LIST', [n.value for n in nodes])

    def string_literal_list(self, nodes:NODES_TYPE):
        return Token('STRING_LITERAL_LIST', [n.value for n in nodes])

    def type_with_extended_attributes(self, nodes:NODES_TYPE):
        assert len(nodes) == 1 or len(nodes) == 2
        attr_type = nodes[-1]
        return attr_type

    def unrestricted_float_type(self, nodes:NODES_TYPE):
        assert len(nodes) == 2 or len(nodes) == 1
        return Token('UNRESTRICTED_FLOAT_TYPE', ' '.join([n.value for n in nodes]))

    def float_type(self, nodes:NODES_TYPE):
        assert len(nodes) == 1
        node = nodes[0]
        return Token('FLOAT_TYPE', node.value)

    def unsigned_integer_type(self, nodes:NODES_TYPE):
        assert len(nodes) == 1 or len(nodes) == 2
        ret = []
        for node in nodes:
            if isinstance(node, Token):
                ret.append(node.value)
            else: 
                raise TypeError(f"Invalid node type {type(node)}")
        return Token("UNSIGNED_INTEGER_TYPE", ' '.join(ret))

    def integer_type(self, nodes:NODES_TYPE):
        assert len(nodes) == 1 or len(nodes) == 2
        return Token('INTEGER_TYPE', ' '.join([n.value for n in nodes]))

    def void_type(self, nodes:NODES_TYPE):
        assert len(nodes) == 1
        t = nodes[0]
        return IdlType(t.value)

    def any_type(self, nodes:NODES_TYPE):
        assert len(nodes) == 1
        t = nodes[0]
        return IdlType(t.value)

    def type(self, nodes:NODES_TYPE):
        ret = None
        nullable = False
        for node in nodes:
            if isinstance(node, IdlTypeBase):
                ret = node
            elif isinstance(node, Token) and node.type == 'NULLABLE':
                nullable = node.value
        assert ret
        if nullable: 
            ret = IdlNullableType(ret)
        return ret

    def single_type(self, nodes:NODES_TYPE):
        assert len(nodes) == 1
        ret_type = None
        for node in nodes:
            if isinstance(node, IdlTypeBase):
                ret_type = node
        assert ret_type
        return ret_type

    def union_type(self, nodes:NODES_TYPE):
        member_types = []
        for node in nodes:
            if isinstance(node, IdlTypeBase):
                member_types.append(node)
        assert member_types
        return IdlUnionType(member_types)

    def union_member_type(self, nodes:NODES_TYPE):
        ret_type = None
        for node in nodes:
            if isinstance(node, IdlTypeBase):
                ret_type = node
        assert ret_type
        return ret_type

    def promise_type(self, nodes:NODES_TYPE):
        assert len(nodes) == 2
        return IdlPromiseType(nodes[1])

    def primitive_type(self, nodes:NODES_TYPE):
        assert len(nodes) == 1
        node = nodes[0]
        if isinstance(node, Token):
            return IdlType(node.value)
        else:
            raise TypeError(f"Invalid node type {type(node)}")

    def identifier_type(self, nodes:NODES_TYPE):
        assert len(nodes) == 1
        t = nodes[0]
        return IdlType(t.value)

    def sequence_type(self, nodes:NODES_TYPE):
        element_type = None
        length = None
        for node in nodes:
            if isinstance(node, IdlTypeBase):
                element_type = node
            elif isinstance(node, Token) and node.type == 'INTEGER':
                length = node.value
        assert element_type
        return IdlSequenceType(element_type, length)

    def forzen_array_type(self, nodes:NODES_TYPE):
        for node in nodes:
            if isinstance(node, IdlTypeBase):
                return IdlSequenceType(node)
        return nodes

    def observable_array_type(self, nodes:NODES_TYPE):
        for node in nodes:
            if isinstance(node, IdlTypeBase):
                return IdlObservableArrayType(node)
        return nodes

    def record_type(self, nodes:NODES_TYPE):
        key_type = nodes[1]
        value_type = nodes[2]
        assert key_type and value_type
        return IdlRecordType(key_type, value_type)

    def distinguishable_type(self, nodes:NODES_TYPE):
        assert len(nodes) == 1 or len(nodes) == 2
        ret_type = None
        nullable = False
        for node in nodes:
            if isinstance(node, IdlTypeBase):
                ret_type = node
            elif isinstance(node, Token) and node.type == 'NULLABLE':
                nullable = node.value
        assert ret_type
        ret_type = ret_type if not nullable else IdlNullableType(ret_type)
        return ret_type

    def nullable(self, nodes:NODES_TYPE):
        for node in nodes:
            if isinstance(node, Token) and node.type == 'QSTN':
                return Token('NULLABLE', True)
        return Token('NULLABLE', False)

class IDLark:

    GRAMMAR_FILE = 'grammar.lark'

    def __init__(self):
        self.lark = Lark(
            GRAMMAR_PATH.read_text(encoding='utf-8'), start="definitions", parser="lalr"
        )

    def parse(self, text:str) -> IdlDefinitions:
        return WebIDLTransformer().transform(self.lark.parse(text))
