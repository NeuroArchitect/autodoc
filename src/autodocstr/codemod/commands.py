import os

import libcst as cst
import libcst.matchers as m
from libcst._nodes.internal import CodegenState
from libcst.codemod import CodemodContext, VisitorBasedCodemodCommand

from autodoc.backends import Backend, CodexBackend


def func_has_doc(node: cst.FunctionDef) -> bool:
    """
    Check if a function has a docstring.
    Args:
        node: The function to check.
    Returns:
        True if the function has a docstring, False otherwise.
    """
    maybe_more = m.AtLeastN(m.DoNotCare(), n=0)  # anything or nothing
    doc_block = [m.Expr(m.SimpleString()), maybe_more]
    single_line_body = m.SimpleStatementSuite(body=doc_block)
    multi_line_body = m.IndentedBlock(body=[m.SimpleStatementLine(body=doc_block), maybe_more])
    if m.matches(node.body, multi_line_body | single_line_body):
        return True
    return False


def split_function_definition_and_body(node: cst.FunctionDef) -> str:
    """
    Split a function definition and body into two strings.
    Args:
        node: A function definition.
    Returns:
        A tuple of two strings. The first string is the function definition. The second string is the function body.
    """
    func_def = cst.FunctionDef(
        name=node.name,
        params=node.params,
        decorators=node.decorators,
        returns=node.returns,
        asynchronous=node.asynchronous,
        whitespace_after_def=node.whitespace_after_def,
        lines_after_decorators=node.lines_after_decorators,
        body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])]),
    )
    default_indent: str = " " * 4
    default_newline: str = "\n"
    state = CodegenState(default_indent=default_indent, default_newline=default_newline)
    func_def._codegen(state)
    func_def_str = "".join(state.tokens[: state.tokens.index("pass")])

    # extract body
    state = CodegenState(default_indent=default_indent, default_newline=default_newline)
    node.body._codegen(state)
    func_body_str = "".join(state.tokens)

    return func_def_str, func_body_str


class AutodocCommand(VisitorBasedCodemodCommand):
    # Add a description so that future codemodders can see what this does.
    DESCRIPTION: str = "adds AI generated docstring to a function"

    def __init__(self, context: CodemodContext, backend: Backend) -> None:
        """Initialize the base class with context, and save our args."""
        # Initialize the base class with context, and save our args.
        super().__init__(context)
        self._backend = backend

    def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef):
        """
        This function is used to add a docstring to a function.
        Args:
            original_node: The original function node.
            updated_node: The updated function node.
        Returns:
            The updated function node.
        """
        if func_has_doc(original_node):
            print("Function already has a docstring:", original_node.name.value)
            return updated_node

        # # Assuming the function will have at least one code line inside it,
        # # and it is ought to be indented
        # #: The indentation of the file, expressed as a series of tabs and/or spaces.
        # # This: value is inferred from the contents of the parsed source code by default.
        # default_indent: str = " " * 4

        # #: The newline of the file, expressed as ``\n``, ``\r\n``, or ``\r``.
        # # This value is: inferred from the contents of the parsed source code by default.
        # default_newline: str = "\n"
        # state = CodegenState(
        #     default_indent=default_indent, default_newline=default_newline
        # )
        # original_node._codegen(state)
        # code = "".join(state.tokens)

        func_signature, func_body = split_function_definition_and_body(original_node)

        doc = self._backend.generate_function_doc_string(func_signature, func_body)

        func_def = cst.parse_statement(func_signature + doc + func_body)
        return func_def


class AutodocWithCodexCommand(AutodocCommand):
    def __init__(self, context: CodemodContext) -> None:
        """
        Args:
            context: The CodemodContext.
        """
        super().__init__(
            context,
            CodexBackend(
                os.getenv("OPENAI_API_KEY"),
            ),
        )
