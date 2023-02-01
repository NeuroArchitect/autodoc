import unittest

from libcst.codemod import CodemodTest

from autodoc.codemod.commands import AutodocCommand


class BackendTest:
    def generate_function_doc_string(self, func_signature, func_body):
        return '"has no code line"'


class WrapTestAutodocCommand(AutodocCommand):
    def __init__(self, context):
        super().__init__(context, BackendTest())


class TestConvertConstantCommand(CodemodTest):
    # The codemod that will be instantiated for us in assertCodemod.
    TRANSFORM = WrapTestAutodocCommand

    def test_sub_function(self) -> None:
        before = """
            def no_code_line():
                pass
        """
        after = """
            def no_code_line():
                "has no code line"
                pass
        """

        # Verify that if we do have a valid string match, we make a substitution
        # as well as import the constant.
        self.assertCodemod(before, after)

    def test_sub_method(self) -> None:
        before = """
        class Foo:
            def no_code_line():
                pass
        """
        after = """
        class Foo:
            def no_code_line():
                "has no code line"
                pass
        """

        # Verify that if we do have a valid string match, we make a substitution
        # as well as import the constant.
        self.assertCodemod(before, after)

    @unittest.skip("not implemented yet")
    def test_module_doc(self) -> None:
        before = """
        class Foo:
            def no_code_line():
                pass
        """
        after = """
        '''has no code line'''

        class Foo:
            def no_code_line():
                "has no code line"
                pass
        """

        # Verify that if we do have a valid string match, we make a substitution
        # as well as import the constant.
        self.assertCodemod(before, after)

    def test_async_def(self) -> None:
        before = """
        class Foo:
            async def no_code_line():
                pass
        """
        after = """
        class Foo:
            async def no_code_line():
                "has no code line"
                pass
        """

        # Verify that if we do have a valid string match, we make a substitution
        # as well as import the constant.
        self.assertCodemod(before, after)
