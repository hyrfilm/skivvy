# coding=utf-8
import importlib.util
import inspect
import os.path

from . import matchers
from .util import file_util, log

def load(conf):
    custom_matchers_dir = conf.get("matchers")
    if custom_matchers_dir:
        for file in file_util.list_files(custom_matchers_dir, ".py"):
            log.info("* Loading custom matcher: %s" % file)
            custom_matcher = CustomMatcher(file)
            # NOTE: This function has the side effect of affecting the matcher module
            matchers.add_matcher(custom_matcher.matcher_name, custom_matcher.match)


class CustomMatcher(object):
    def __init__(self, source_file):
        # this is constructor loads a plugin aka a custom matcher, the contract between us
        # and the user is that we expect that:
        # * the file contains a function called "match"
        # * the function takes two parameters: expected & actual
        # * expected is a string, actual is json (what we get back from the server)
        # * the function CAN return just true if the matcher passed, false otherwise
        # * the function is RECOMMENDED to return a tuple (boolean, string)
        # * if the function returns a tuple, the string will be shown as the message when the matcher failes
        try:
            self.matcher_func_name = "match"
            self.matcher_name = os.path.basename(source_file).split(".")[0]
            spec = importlib.util.spec_from_file_location(self.matcher_name, source_file)
            self.matcher_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.matcher_module)
            self.matcher_func = self.matcher_module.__getattribute__(self.matcher_func_name)
            CustomMatcher.validate_matcher(self.matcher_func)
        except Exception as e:
            raise AssertionError("Failed to load matcher %s: %s" % (source_file, e))

    @staticmethod
    def validate_matcher(matcher_func):
        if matcher_func is None:
            raise AssertionError("Expected to find 'match' function")
        arguments = inspect.getfullargspec(matcher_func).args
        expected_signature = ["expected", "actual"]
        if not arguments == expected_signature:
            raise AssertionError(
                "Expected 'match' to take exactly 2 parameters: %s - but was %s" % (expected_signature, arguments))

    def match(self, expected, actual):
        try:
            result = self.matcher_func(expected.strip(), actual)
            if isinstance(result, (bool)):
                return result, ""
            elif isinstance(result, (tuple)):
                return result
            else:
                raise AssertionError("Unexpected result %s from %s" % (result, self.matcher_name))
        except Exception as e:
            raise Exception("Custom matcher threw unexpected execption: %s" % str(e))
