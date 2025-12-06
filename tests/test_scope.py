from skivvy.util import scope
from skivvy.util.file_util import set_current_file


def test_storing():
    set_current_file("/dir1/some_test.json")
    assert scope.dump("dir1") == {}
    set_current_file("/dir2/some_test.json")
    assert scope.dump("dir2") == {}

    assert scope.has("dir1") == False
    set_current_file("/dir1/test1.json")
    scope.store("var1", "123")
    assert scope.has("var1") == True
    assert scope.fetch("var1") == "123"

    assert False == scope.has("var2")
    set_current_file("/dir1/test2.json")
    scope.store("var2", "456")
    assert True == scope.has("var2")
    assert "456" == scope.fetch("var2")

    set_current_file("/dir2/test1.json")
    assert False == scope.has("var1")
    assert False == scope.has("var2")
    assert False == scope.has("var2")
    scope.store("var1", "yo")
    scope.store("var2", "dude")
    scope.store("var3", "zup")
    assert True == scope.has("var1")
    assert True == scope.has("var2")
    assert True == scope.has("var3")
    assert "yo" == scope.fetch("var1")
    assert "dude" == scope.fetch("var2")
    assert "zup" == scope.fetch("var3")

    assert scope.dump("dir1") == {"var1": "123", "var2": "456"}
    assert scope.dump("dir2") == {"var1": "yo", "var2": "dude", "var3": "zup"}
